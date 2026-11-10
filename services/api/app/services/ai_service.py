"""AI orchestration: model/fallback selection, validation, persistence, audit."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.deterministic import deterministic_answer
from app.ai.llm import run_llm_agent
from app.ai.validation import AgentAnswer
from app.core.config import Settings
from app.core.errors import AppError
from app.core.request_id import get_request_id
from app.models import ChatMessage, ChatSession, User
from app.schemas.ai import (
    AIChatResponse,
    ChatMessageOut,
    ChatSessionOut,
    AnswerEnvelope,
    AnswerMeta,
)
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)

DATA_VERSION = "dv_demo_2025"
TZ = timezone.utc
LOCAL_TZ = timezone(timedelta(hours=8))


def _now() -> datetime:
    return datetime.now(LOCAL_TZ)


def _utcnow() -> datetime:
    return datetime.now(TZ)


def new_answer_id() -> str:
    return f"ans_{_now():%Y%m%d}_{secrets.token_hex(6)}"


def compute_data_hash(rows: list[dict[str, Any]], data_version: str) -> str:
    normalized = []
    for row in rows:
        value = row.get("value")
        normalized.append(
            {
                "indicator_code": row.get("indicator_code"),
                "region_code": row.get("region_code"),
                "period": str(row.get("period")) if row.get("period") is not None else None,
                "value": None if value is None else round(float(value), 4),
            }
        )
    normalized.sort(
        key=lambda item: (
            str(item["indicator_code"]),
            str(item["region_code"]),
            str(item["period"]),
        )
    )
    payload = json.dumps(
        {"data_version": data_version, "rows": normalized},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _chart_spec(envelope_blocks: list) -> Any:
    for block in envelope_blocks:
        if block.type == "chart" and block.chart is not None:
            return block.chart
    return None


async def _resolve_session(
    session: AsyncSession,
    *,
    user: User,
    session_id: int | None,
    question: str,
) -> ChatSession:
    if session_id is not None:
        chat_session = await session.get(ChatSession, session_id)
        if chat_session is None or chat_session.user_id != user.id:
            raise AppError("NOT_FOUND", "Chat session not found", status_code=404)
        return chat_session
    chat_session = ChatSession(user_id=user.id, title=question[:60])
    session.add(chat_session)
    await session.flush()
    return chat_session


async def _persist(
    session: AsyncSession,
    *,
    user: User | None,
    session_id: int | None,
    question: str,
    envelope: AnswerEnvelope,
    agent: AgentAnswer,
    model_name: str,
) -> tuple[int | None, int | None]:
    if user is None:
        return None, None
    chat_session = await _resolve_session(
        session,
        user=user,
        session_id=session_id,
        question=question,
    )
    user_message = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=question,
    )
    assistant_message = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=envelope.answer_markdown,
        answer_id=envelope.answer_id,
        tool_calls=[{"count": agent.tool_calls}] if agent.tool_calls else None,
        chart_spec=(
            _chart_spec(envelope.blocks).model_dump(mode="json")
            if _chart_spec(envelope.blocks) is not None
            else None
        ),
        blocks=[block.model_dump(mode="json") for block in envelope.blocks],
        citations=[citation.model_dump(mode="json") for citation in envelope.citations],
        data_snapshot={
            "answer_id": envelope.answer_id,
            "intent": envelope.intent,
            "status": agent.draft.status,
            "demo": agent.demo,
            "data_version": envelope.meta.data_version,
            "data_hash": envelope.meta.data_hash,
            "registry_version": envelope.meta.registry_version,
            "generated_at": envelope.meta.generated_at.isoformat(),
        },
        model=model_name,
        latency_ms=envelope.meta.latency_ms,
        token_usage=agent.token_usage,
    )
    session.add_all([user_message, assistant_message])
    chat_session.updated_at = _utcnow()
    await session.flush()
    return chat_session.id, assistant_message.id


async def chat(
    session: AsyncSession,
    *,
    request: Request,
    settings: Settings,
    user: User | None,
    question: str,
    session_id: int | None,
    context: dict[str, Any] | None,
) -> AIChatResponse:
    request_id = get_request_id(request)
    started = time.monotonic()
    key = ""
    if settings.llm_api_key is not None:
        key = settings.llm_api_key.get_secret_value().strip()
    llm_ready = bool(key and settings.llm_base_url and settings.llm_model)

    agent: AgentAnswer | None = None
    model_name = "deterministic-v0"
    degraded = True
    if llm_ready:
        try:
            async with asyncio.timeout(settings.ai_timeout_seconds):
                agent = await run_llm_agent(
                    session,
                    question=question,
                    context=context,
                    settings=settings,
                )
            model_name = settings.llm_model or "llm"
            degraded = False
        except Exception as exc:  # noqa: BLE001 - fallback is the contract
            logger.warning("LLM path failed, using deterministic fallback: %s", exc)
            agent = None

    if agent is None:
        context_period = None
        context_region_id = None
        context_indicator_id = None
        if context:
            context_period = context.get("period")
            context_region_id = context.get("region_id")
            context_indicator_id = context.get("indicator_id")
        agent = await deterministic_answer(
            session,
            question=question,
            context_period=context_period,
            context_region_id=context_region_id,
            context_indicator_id=context_indicator_id,
        )

    draft = agent.draft
    latency_ms = int((time.monotonic() - started) * 1000)
    answer_id = new_answer_id()
    meta = AnswerMeta(
        request_id=request_id,
        model=model_name,
        latency_ms=latency_ms,
        tool_calls=agent.tool_calls,
        data_version=DATA_VERSION,
        data_hash=compute_data_hash(agent.rows, DATA_VERSION),
        registry_version=settings.export_registry_version,
        generated_at=_now(),
        degraded=degraded,
        locale="zh-CN",
    )
    envelope = AnswerEnvelope(
        answer_id=answer_id,
        answer_markdown=draft.answer_markdown,
        intent=draft.intent,
        blocks=draft.blocks,
        citations=draft.citations,
        actions=draft.actions,
        follow_up_questions=draft.follow_up_questions,
        meta=meta,
    )

    persisted_session_id, message_id = await _persist(
        session,
        user=user,
        session_id=session_id,
        question=question,
        envelope=envelope,
        agent=agent,
        model_name=model_name,
    )

    await write_audit(
        session,
        action="ai.chat",
        resource_type="chat",
        resource_id=answer_id,
        detail={
            "intent": envelope.intent,
            "status": draft.status,
            "demo": agent.demo,
            "model": model_name,
            "degraded": degraded,
            "question": question if user is not None else None,
            "question_length": len(question),
            "tool_calls": agent.tool_calls,
        },
        request=request,
        user_id=user.id if user is not None else None,
    )
    await session.commit()

    return AIChatResponse(
        session_id=persisted_session_id,
        message_id=message_id,
        answer_id=answer_id,
        answer_markdown=envelope.answer_markdown,
        blocks=envelope.blocks,
        chart_spec=_chart_spec(envelope.blocks),
        citations=envelope.citations,
        follow_up_questions=envelope.follow_up_questions,
        status=draft.status,
        demo=agent.demo,
        intent=envelope.intent,
        meta=meta,
    )


async def list_sessions(
    session: AsyncSession,
    *,
    user: User,
    limit: int = 50,
) -> list[ChatSessionOut]:
    count_column = func.count(ChatMessage.id)
    rows = (
        await session.execute(
            select(ChatSession, count_column)
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user.id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
            .limit(limit)
        )
    ).all()
    return [
        ChatSessionOut(
            id=chat_session.id,
            title=chat_session.title,
            message_count=int(message_count),
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
        )
        for chat_session, message_count in rows
    ]


async def get_session_messages(
    session: AsyncSession,
    *,
    user: User,
    session_id: int,
) -> list[ChatMessageOut]:
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None or chat_session.user_id != user.id:
        raise AppError("NOT_FOUND", "Chat session not found", status_code=404)
    messages = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
        )
    ).scalars().all()
    return [
        ChatMessageOut(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            answer_id=message.answer_id,
            blocks=message.blocks,
            citations=message.citations,
            chart_spec=message.chart_spec,
            model=message.model,
            latency_ms=message.latency_ms,
            created_at=message.created_at,
        )
        for message in messages
    ]


__all__ = [
    "chat",
    "compute_data_hash",
    "get_session_messages",
    "list_sessions",
    "new_answer_id",
]
