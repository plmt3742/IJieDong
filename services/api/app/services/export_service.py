"""Synchronous Demo v0 export service: snapshots, renderers, storage, audit."""
from __future__ import annotations

import asyncio
import csv
import hashlib
import html as html_lib
import io
import logging
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Request
from openpyxl import Workbook
from openpyxl.styles import Font
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models import ChatMessage, ChatSession, DataSource, DataValue, ExportJob, Indicator, Region, User
from app.services import query_service
from app.services.ai_service import compute_data_hash
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)

FORMATS: dict[str, dict[str, Any]] = {
    "png": {"ext": "png", "mime": "image/png", "max_bytes": 3 * 1024 * 1024},
    "pdf": {"ext": "pdf", "mime": "application/pdf", "max_bytes": 10 * 1024 * 1024},
    "xlsx": {
        "ext": "xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "max_bytes": 10 * 1024 * 1024,
    },
    "csv": {"ext": "csv", "mime": "text/csv; charset=utf-8", "max_bytes": 5 * 1024 * 1024},
}
ALLOWED_ROLES = {"viewer", "editor", "approver", "admin"}
PRIVILEGED_ROLES = {"admin", "approver"}
ILLEGAL_TITLE = re.compile(r'[\\/:*?"<>|\r\n]+')
DEFAULT_PERIOD = query_service.DEFAULT_PERIOD_YEAR
LOCAL_TZ = timezone(timedelta(hours=8))


class ExportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orientation: Literal["portrait", "landscape"] = "portrait"
    include_citations: bool = True
    watermark: bool = True
    max_rows: int = Field(100, ge=1, le=100)


class ExportSourceDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: int | None = None
    region_name: str | None = Field(None, max_length=128)
    indicator_id: int | None = None
    indicator_code: str | None = Field(None, max_length=64)
    indicator_name: str | None = Field(None, max_length=128)
    period_year: int | None = None
    unit: str | None = Field(None, max_length=32)


class ExportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: Literal["answer", "report"]
    source_id: str | None = Field(None, max_length=32)
    format: str | None = None
    title: str | None = Field(None, max_length=60)
    options: ExportOptions | None = None
    source: ExportSourceDescriptor | None = None


class ExportErrorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ExportJobOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_id: str
    status: str
    progress: int
    format: str
    title: str
    file_size: int | None
    sha256: str | None
    download_url: str | None
    expires_at: datetime | None
    created_at: datetime | None
    error: ExportErrorOut | None = None


@dataclass
class Snapshot:
    source_id: str
    title: str
    answer_markdown: str
    blocks: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    meta: dict[str, Any]
    demo: bool
    period_label: str
    source_summary: dict[str, Any] = field(default_factory=dict)


class ExportRenderError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def _as_local(value: datetime | None) -> datetime | None:
    converted = _as_utc(value)
    return converted.astimezone(LOCAL_TZ) if converted is not None else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _new_export_id() -> str:
    return f"exp_{_utcnow():%Y%m%d}_{secrets.token_hex(4)}"


def _sanitize_title(value: str | None) -> str:
    if not value:
        return ""
    cleaned = ILLEGAL_TITLE.sub(" ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:60]


def _filename(title: str, period: str, export_id: str, extension: str) -> str:
    base = _sanitize_title(title) or "导出"
    period_part = re.sub(r"[^\w\u4e00-\u9fff-]+", "", period or "")[:16]
    parts = [base]
    if period_part:
        parts.append(period_part)
    parts.append(export_id)
    return "_".join(parts) + f".{extension}"


def _citation(
    citation_id: str,
    *,
    indicator: Indicator | None,
    indicator_code: str,
    indicator_name: str,
    region: Region | None,
    region_code: str | None,
    region_name: str | None,
    region_level: str,
    period: int | str,
    data_as_of: str | None,
) -> dict[str, Any]:
    return {
        "id": citation_id,
        "citation_id": citation_id,
        "indicator": indicator_name,
        "indicator_name": indicator_name,
        "indicator_id": indicator.id if indicator is not None else None,
        "indicator_code": indicator_code,
        "region": region_name,
        "region_id": region.id if region is not None else None,
        "region_code": region_code,
        "region_name": region_name,
        "region_level": region_level,
        "period": str(period),
        "source": "data_values",
        "data_as_of": data_as_of,
    }


def _is_privileged(user: User) -> bool:
    return user.role in PRIVILEGED_ROLES


def _forbidden() -> AppError:
    return AppError(
        "EXPORT_FORBIDDEN",
        "Current role cannot export",
        status_code=403,
    )


def _not_found() -> AppError:
    return AppError("EXPORT_NOT_FOUND", "Export not found", status_code=404)


def _source_not_found(message: str = "Export source not found") -> AppError:
    return AppError("EXPORT_SOURCE_NOT_FOUND", message, status_code=404)


async def _answer_snapshot(
    session: AsyncSession,
    *,
    user: User,
    source_id: str,
) -> Snapshot:
    message = (
        await session.execute(
            select(ChatMessage).where(
                ChatMessage.answer_id == source_id,
                ChatMessage.role == "assistant",
            )
        )
    ).scalars().first()
    if message is None:
        raise _source_not_found()
    chat_session = await session.get(ChatSession, message.session_id)
    owner_id = chat_session.user_id if chat_session is not None else None
    if owner_id != user.id and not _is_privileged(user):
        raise _source_not_found()

    blocks = list(message.blocks or [])
    citations = list(message.citations or [])
    if not blocks:
        blocks = _blocks_from_legacy(message)
    snapshot_meta = dict(message.data_snapshot or {})
    demo = bool(snapshot_meta.get("demo", True))
    demo = demo or any("演示" in str(block.get("text") or "") for block in blocks)
    if not citations:
        citations = _citations_from_blocks(blocks)
    title = _first_title(blocks) or "AI 问答答案"
    data_as_of = next(
        (item.get("data_as_of") for item in citations if item.get("data_as_of")),
        None,
    )
    period_label = next(
        (str(item.get("period")) for item in citations if item.get("period")),
        "",
    )
    first_citation = citations[0] if citations else {}
    return Snapshot(
        source_id=source_id,
        title=title,
        answer_markdown=message.content,
        blocks=blocks,
        citations=citations,
        meta={
            "generated_at": snapshot_meta.get("generated_at"),
            "data_version": snapshot_meta.get("data_version") or "dv_demo_2025",
            "data_hash": snapshot_meta.get("data_hash") or "",
            "registry_version": snapshot_meta.get("registry_version") or "1.0.0",
        },
        demo=demo,
        period_label=period_label,
        source_summary={
            "as_of": data_as_of,
            "period": period_label,
            "region": first_citation.get("region_name") or first_citation.get("region"),
            "indicator": first_citation.get("indicator")
            or first_citation.get("indicator_name"),
        },
    )


def _first_title(blocks: list[dict[str, Any]]) -> str:
    for block in blocks:
        title = block.get("title")
        if title:
            return str(title)
    return ""


def _citations_from_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for block in blocks:
        for citation in block.get("citations") or []:
            identifier = citation.get("id") or citation.get("citation_id")
            if identifier and identifier not in seen:
                seen[identifier] = citation
    return list(seen.values())


def _blocks_from_legacy(message: ChatMessage) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        {
            "id": "b1",
            "type": "summary",
            "component": "text",
            "props": {"paragraphs": [message.content]},
            "text": message.content,
        }
    ]
    if message.chart_spec:
        blocks.append(
            {
                "id": f"b{len(blocks) + 1}",
                "type": "chart",
                "component": "bar_chart",
                "props": {"chart": message.chart_spec},
                "chart": message.chart_spec,
                "title": message.chart_spec.get("title") if isinstance(message.chart_spec, dict) else None,
            }
        )
    if message.citations:
        blocks.append(
            {
                "id": f"b{len(blocks) + 1}",
                "type": "source",
                "component": "source_card",
                "props": {"citation_ids": [item.get("id") for item in message.citations]},
                "citations": message.citations,
            }
        )
    return blocks


async def _report_snapshot(
    session: AsyncSession,
    *,
    user: User,
    request_payload: ExportCreateRequest,
) -> Snapshot:
    descriptor = request_payload.source
    if descriptor is None:
        raise _source_not_found("report source descriptor is required")
    region = await _resolve_region(session, descriptor)
    if region is None:
        raise _source_not_found("Region not found")
    indicator = await _resolve_indicator(session, descriptor)
    if indicator is None and any(
        value is not None
        for value in (
            descriptor.indicator_id,
            descriptor.indicator_code,
            descriptor.indicator_name,
        )
    ):
        raise _source_not_found("Indicator not found")
    period = int(descriptor.period_year or DEFAULT_PERIOD)
    data_as_of = await _latest_as_of(session, region.id, indicator)
    demo = True
    source_type = "demo"
    value: Any = None

    if indicator is None:
        profile = await query_service.get_region_profile(session, region.id)
        metrics: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        for index, metric in enumerate(profile.metrics[:6], start=1):
            value = metric.value_number
            citation = _citation(
                f"c{index}",
                indicator=await session.get(Indicator, metric.indicator_id),
                indicator_code=metric.code,
                indicator_name=metric.name,
                region=region,
                region_code=region.code,
                region_name=region.name,
                region_level=region.level,
                period=metric.period_year,
                data_as_of=data_as_of,
            )
            if value is not None:
                citations.append(citation)
            metrics.append(
                {
                    "label": metric.name,
                    "value": value,
                    "unit": metric.unit,
                    "year": metric.period_year,
                    "quality_status": metric.quality_status,
                    "display": _display(value, metric.unit),
                    "citation_id": citation["id"] if value is not None else None,
                }
            )
        blocks = [
            {
                "id": "b1",
                "type": "summary",
                "component": "text",
                "props": {"paragraphs": [profile.intro or profile.feature or f"{region.name}区域汇报"]},
                "title": f"{region.name}区域汇报",
                "text": profile.intro or profile.feature or f"{region.name}区域汇报",
            },
            {
                "id": "b2",
                "type": "metric_grid",
                "component": "metric_grid",
                "props": {"title": f"{region.name}关键指标", "items": metrics},
                "title": f"{region.name}关键指标",
                "metrics": metrics,
                "citations": citations,
            },
        ]
        answer_markdown = f"{region.name}区域汇报（{period} 年）。"
        title = f"{period} 年{region.name}区域汇报"
        source_summary = {"region": region.name, "period": period, "as_of": data_as_of}
    else:
        row = (
            await session.execute(
                select(DataValue, DataSource)
                .outerjoin(DataSource, DataValue.source_id == DataSource.id)
                .where(
                    DataValue.region_id == region.id,
                    DataValue.indicator_id == indicator.id,
                    DataValue.period_year == period,
                    DataValue.status == "published",
                )
                .order_by(DataValue.id)
            )
        ).first()
        value_row = row[0] if row is not None else None
        source_row = row[1] if row is not None else None
        if source_row is not None:
            source_type = source_row.source_type
        demo = source_type == "demo"
        value = None if value_row is None else value_row.value_number
        quality = value_row.quality_status if value_row is not None else "missing"
        updated_at = _as_utc(value_row.updated_at) if value_row is not None else None
        if updated_at is not None:
            data_as_of = updated_at.date().isoformat()
        citation = _citation(
            "c1",
            indicator=indicator,
            indicator_code=indicator.code,
            indicator_name=indicator.name,
            region=region,
            region_code=region.code,
            region_name=region.name,
            region_level=region.level,
            period=period,
            data_as_of=data_as_of,
        )
        citations = [citation] if value is not None else []
        metric_value = None if value is None else float(value)
        metrics = [
            {
                "label": indicator.name,
                "value": metric_value,
                "unit": indicator.unit,
                "year": period,
                "quality_status": quality,
                "display": _display(metric_value, indicator.unit),
                "citation_id": citation["id"] if value is not None else None,
            }
        ]
        table_rows = [[region.name, metric_value, indicator.unit, period]]
        blocks = [
            {
                "id": "b1",
                "type": "summary",
                "component": "text",
                "props": {
                    "paragraphs": [
                        f"{period} 年{region.name}{indicator.name}为 {_display(metric_value, indicator.unit)}。"
                    ]
                },
                "title": f"{period} 年{region.name}{indicator.name}",
                "text": f"{period} 年{region.name}{indicator.name}为 {_display(metric_value, indicator.unit)}。",
            },
            {
                "id": "b2",
                "type": "metric_grid",
                "component": "metric_grid",
                "props": {"title": indicator.name, "items": metrics},
                "title": indicator.name,
                "metrics": metrics,
                "citations": citations,
            },
            {
                "id": "b3",
                "type": "table",
                "component": "data_table",
                "props": {
                    "title": f"{indicator.name}数据表",
                    "columns": ["区域", f"{indicator.name}（{indicator.unit}）", "期"],
                    "rows": table_rows,
                },
                "title": f"{indicator.name}数据表",
                "columns": ["区域", f"{indicator.name}（{indicator.unit}）", "期"],
                "rows": table_rows,
                "citations": citations,
            },
        ]
        if value is None:
            blocks.append(
                {
                    "id": "b4",
                    "type": "notice",
                    "component": "text",
                    "props": {"level": "warning", "code": "NO_DATA", "text": "该区域、指标、期暂无数据。"},
                    "level": "warning",
                    "text": "该区域、指标、期暂无数据。",
                }
            )
        answer_markdown = (
            f"{period} 年{region.name}{indicator.name}为 {_display(metric_value, indicator.unit)}。"
        )
        title = f"{period} 年{region.name}{indicator.name}"
        source_summary = {
            "region": region.name,
            "indicator": indicator.name,
            "period": period,
            "unit": indicator.unit,
            "as_of": data_as_of,
        }

    blocks.append(
        {
            "id": f"b{len(blocks) + 1}",
            "type": "notice",
            "component": "text",
            "props": {
                "level": "info",
                "code": "DEMO_DATA" if demo else "DATA",
                "text": "演示数据（合成），仅用于展示流程。",
            },
            "level": "info",
            "text": "演示数据（合成），仅用于展示流程。" if demo else "",
            "title": "演示数据" if demo else None,
        }
    )
    blocks.append(
        {
            "id": f"b{len(blocks) + 1}",
            "type": "source",
            "component": "source_card",
            "props": {"citation_ids": [item["id"] for item in citations], "data_as_of": data_as_of},
            "title": "引用与来源",
            "citations": citations,
        }
    )
    source_id = f"report_{region.id}_{indicator.id if indicator else 'all'}_{period}"[:32]
    return Snapshot(
        source_id=source_id,
        title=title,
        answer_markdown=answer_markdown,
        blocks=blocks,
        citations=citations,
        meta={
            "generated_at": _now_local().isoformat(),
            "data_version": "dv_demo_2025",
            "data_hash": compute_data_hash(
                [
                    {
                        "indicator_code": indicator.code if indicator else None,
                        "region_code": region.code,
                        "period": period,
                        "value": None if indicator is None else float(value) if value is not None else None,
                    }
                ],
                "dv_demo_2025",
            ),
            "registry_version": "1.0.0",
        },
        demo=demo,
        period_label=str(period),
        source_summary={"region": region.name, "period": period, "as_of": data_as_of},
    )


async def _resolve_region(
    session: AsyncSession,
    descriptor: ExportSourceDescriptor,
) -> Region | None:
    if descriptor.region_id is not None:
        return await session.get(Region, descriptor.region_id)
    if descriptor.region_name:
        return (
            await session.execute(
                select(Region).where(Region.name == descriptor.region_name)
            )
        ).scalars().first()
    return None


async def _resolve_indicator(
    session: AsyncSession,
    descriptor: ExportSourceDescriptor,
) -> Indicator | None:
    if descriptor.indicator_id:
        return await session.get(Indicator, descriptor.indicator_id)
    if descriptor.indicator_code:
        return (
            await session.execute(
                select(Indicator).where(Indicator.code == descriptor.indicator_code)
            )
        ).scalars().first()
    if descriptor.indicator_name:
        return (
            await session.execute(
                select(Indicator).where(Indicator.name == descriptor.indicator_name)
            )
        ).scalars().first()
    return None


async def _latest_as_of(
    session: AsyncSession,
    region_id: int,
    indicator: Indicator | None,
) -> str | None:
    statement = select(DataValue.updated_at).where(DataValue.region_id == region_id)
    if indicator is not None:
        statement = statement.where(DataValue.indicator_id == indicator.id)
    value = (await session.execute(statement.order_by(DataValue.updated_at.desc()).limit(1))).scalar()
    if value is None:
        return None
    converted = _as_utc(value)
    return converted.date().isoformat() if converted is not None else None


def _display(value: float | None, unit: str) -> str:
    if value is None:
        return "无数据"
    if unit in {"人", "个"}:
        return f"{int(round(value))} {unit}"
    return f"{value:.2f} {unit}".strip()


def _primary_table(blocks: list[dict[str, Any]]) -> tuple[list[str], list[list[Any]]] | None:
    for block in blocks:
        if block.get("type") == "table" and block.get("columns") is not None:
            return list(block["columns"]), [list(row) for row in block.get("rows") or []]
        if block.get("type") == "ranking" and block.get("ranking"):
            items = block["ranking"]
            columns = ["排名", "区域", "数值"]
            rows = [[item.get("rank"), item.get("name"), item.get("value")] for item in items]
            return columns, rows
        if block.get("type") == "metric_grid" and block.get("metrics"):
            columns = ["指标", "数值", "单位", "期"]
            rows = [
                [
                    item.get("label"),
                    item.get("value"),
                    item.get("unit"),
                    item.get("year"),
                ]
                for item in block["metrics"]
            ]
            return columns, rows
    return None


def _supports_format(snapshot: Snapshot, fmt: str) -> bool:
    if fmt == "csv":
        return _primary_table(snapshot.blocks) is not None
    return True


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _write_csv(snapshot: Snapshot, *, title: str, export_id: str, path: Path) -> None:
    primary = _primary_table(snapshot.blocks)
    if primary is None:
        raise AppError(
            "EXPORT_FORMAT_UNSUPPORTED",
            "CSV requires a single table",
            status_code=422,
        )
    columns, rows = primary
    meta = snapshot.source_summary
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([title])
        writer.writerow(
            [
                "导出编号",
                export_id,
                "数据时效",
                _now_local().date().isoformat(),
                "区域",
                meta.get("region") or "",
                "指标",
                meta.get("indicator") or "",
                "期",
                meta.get("period") or snapshot.period_label,
                "来源",
                "data_values",
            ]
        )
        writer.writerow([])
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_cell(cell) for cell in row])
    if path.stat().st_size > FORMATS["csv"]["max_bytes"]:
        raise AppError("EXPORT_TOO_LARGE", "CSV exceeds 5 MB", status_code=413)


def _write_xlsx(
    snapshot: Snapshot,
    *,
    title: str,
    export_id: str,
    generated_at: datetime,
    path: Path,
    is_answer: bool,
) -> None:
    workbook = Workbook()
    summary = workbook.active
    if summary is None:
        summary = workbook.create_sheet("摘要")
    summary.title = "答案摘要" if is_answer else "摘要"
    summary_rows = [
        ("标题", title),
        ("导出编号", export_id),
        ("生成时间", generated_at.isoformat()),
        ("数据时效", snapshot.source_summary.get("as_of") or ""),
        ("数据版本", snapshot.meta.get("data_version") or ""),
        ("数据哈希", snapshot.meta.get("data_hash") or ""),
        ("区域", snapshot.source_summary.get("region") or ""),
        ("指标", snapshot.source_summary.get("indicator") or ""),
        ("期", snapshot.source_summary.get("period") or snapshot.period_label),
        ("演示数据", "是" if snapshot.demo else "否"),
    ]
    for row_index, (key, value) in enumerate(summary_rows, start=1):
        summary.cell(row=row_index, column=1, value=key).font = Font(bold=True)
        summary.cell(row=row_index, column=2, value=value)
    summary.column_dimensions["A"].width = 16
    summary.column_dimensions["B"].width = 48

    data_sheet = workbook.create_sheet("数据")
    data_sheet.freeze_panes = "A2"
    current_row = 1
    for block in snapshot.blocks:
        block_type = block.get("type")
        table: tuple[list[str], list[list[Any]]] | None = None
        if block_type == "table" and block.get("columns") is not None:
            table = (list(block["columns"]), [list(row) for row in block.get("rows") or []])
        elif block_type == "ranking" and block.get("ranking"):
            table = (
                ["排名", "区域", "数值"],
                [
                    [item.get("rank"), item.get("name"), item.get("value")]
                    for item in block["ranking"]
                ],
            )
        elif block_type == "metric_grid" and block.get("metrics"):
            table = (
                ["指标", "数值", "单位", "期"],
                [
                    [item.get("label"), item.get("value"), item.get("unit"), item.get("year")]
                    for item in block["metrics"]
                ],
            )
        if table is None:
            continue
        columns, rows = table
        if block.get("title"):
            data_sheet.cell(row=current_row, column=1, value=str(block["title"])).font = Font(bold=True)
            current_row += 1
        for column_index, header in enumerate(columns, start=1):
            cell = data_sheet.cell(row=current_row, column=column_index, value=header)
            cell.font = Font(bold=True)
        current_row += 1
        for row in rows[:100]:
            for column_index, value in enumerate(row, start=1):
                data_sheet.cell(row=current_row, column=column_index, value=_xlsx_value(value))
            current_row += 1
        current_row += 1
    for column in range(1, 13):
        data_sheet.column_dimensions[data_sheet.cell(row=1, column=column).column_letter].width = 18

    if is_answer:
        citation_sheet = workbook.create_sheet("引用")
        headers = ["引用编号", "指标", "指标编码", "区域", "区域编码", "层级", "期", "来源", "数据时效"]
        for column_index, header in enumerate(headers, start=1):
            citation_sheet.cell(row=1, column=column_index, value=header).font = Font(bold=True)
        for row_index, citation in enumerate(snapshot.citations, start=2):
            values = [
                citation.get("id") or citation.get("citation_id"),
                citation.get("indicator") or citation.get("indicator_name"),
                citation.get("indicator_code"),
                citation.get("region") or citation.get("region_name"),
                citation.get("region_code"),
                citation.get("region_level"),
                citation.get("period"),
                citation.get("source"),
                citation.get("data_as_of"),
            ]
            for column_index, value in enumerate(values, start=1):
                citation_sheet.cell(row=row_index, column=column_index, value=value)
        for column in range(1, len(headers) + 1):
            citation_sheet.column_dimensions[citation_sheet.cell(row=1, column=column).column_letter].width = 20

    workbook.save(path)
    if path.stat().st_size > FORMATS["xlsx"]["max_bytes"]:
        raise AppError("EXPORT_TOO_LARGE", "XLSX exceeds 10 MB", status_code=413)


def _xlsx_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float)):
        return value
    text = str(value)
    if text.startswith("="):
        return "'" + text
    return text


def _watermark_text(user: User, generated_at: datetime, demo: bool) -> str:
    suffix = " 演示数据" if demo else ""
    return f"{user.display_name} {generated_at:%Y-%m-%d %H:%M} 内部资料{suffix}"


def _render_html(
    snapshot: Snapshot,
    *,
    title: str,
    export_id: str,
    generated_at: datetime,
    watermark: str,
) -> str:
    escape = html_lib.escape
    meta = snapshot.source_summary
    as_of = meta.get("as_of") or snapshot.meta.get("generated_at") or generated_at.isoformat()
    parts: list[str] = [
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
        "<style>",
        "@page { size: A4; margin: 12mm; }",
        "body { font-family: 'Microsoft YaHei','Noto Sans CJK SC',sans-serif; color:#1f2937;",
        "  margin:0; padding:24px 28px; background:#ffffff; font-size:14px; line-height:1.6; }",
        "h1 { font-size:22px; margin:0 0 6px; } h2 { font-size:16px; margin:18px 0 8px; }",
        ".meta { color:#6b7280; font-size:12px; margin-bottom:14px; }",
        ".grid { display:flex; flex-wrap:wrap; gap:10px; }",
        ".card { border:1px solid #e5e7eb; border-radius:8px; padding:10px 14px; min-width:150px; }",
        ".card .label { color:#6b7280; font-size:12px; } .card .value { font-size:20px; font-weight:600; }",
        "table { width:100%; border-collapse:collapse; margin:8px 0; font-size:13px; }",
        "th,td { border:1px solid #e5e7eb; padding:6px 8px; text-align:left; }",
        "th { background:#f3f4f6; }",
        ".bar-row { display:flex; align-items:center; gap:8px; margin:4px 0; }",
        ".bar-label { width:110px; font-size:12px; } .bar-track { flex:1; background:#f3f4f6; height:14px; }",
        ".bar-fill { background:#1d4ed8; height:14px; } .bar-value { width:90px; text-align:right; font-size:12px; }",
        ".notice { border-left:4px solid #f59e0b; background:#fffbeb; padding:8px 12px; margin:10px 0; }",
        ".source { color:#4b5563; font-size:12px; } .source li { margin:2px 0; }",
        ".footer { margin-top:18px; border-top:1px solid #e5e7eb; padding-top:8px; color:#6b7280; font-size:11px; }",
        ".watermark { position:fixed; inset:0; pointer-events:none; opacity:0.07; z-index:0;",
        "  display:flex; flex-wrap:wrap; gap:60px; align-content:center; justify-content:center;",
        "  transform:rotate(-24deg); font-size:26px; font-weight:600; color:#111827; }",
        ".watermark span { white-space:nowrap; }",
        ".content { position:relative; z-index:1; }",
        "</style></head><body>",
        "<div class=\"watermark\">",
    ]
    for _ in range(24):
        parts.append(f"<span>{escape(watermark)}</span>")
    parts.append("</div><div class=\"content\">")
    parts.append(f"<h1>{escape(title)}</h1>")
    meta_bits = [
        f"区域：{escape(str(meta.get('region') or '-'))}",
        f"指标：{escape(str(meta.get('indicator') or '-'))}",
        f"期：{escape(str(meta.get('period') or snapshot.period_label or '-'))}",
        f"数据时效：{escape(str(as_of))}",
        f"生成时间：{generated_at.isoformat()}",
        f"导出编号：{escape(export_id)}",
    ]
    parts.append(f"<div class=\"meta\">{' ｜ '.join(meta_bits)}</div>")

    for block in snapshot.blocks:
        block_type = block.get("type")
        title_text = block.get("title")
        if block_type == "summary":
            if title_text:
                parts.append(f"<h2>{escape(str(title_text))}</h2>")
            parts.append(f"<p>{escape(str(block.get('text') or ''))}</p>")
        elif block_type == "metric_grid":
            if title_text:
                parts.append(f"<h2>{escape(str(title_text))}</h2>")
            parts.append("<div class=\"grid\">")
            for item in block.get("metrics") or []:
                value = item.get("display") or _display(item.get("value"), str(item.get("unit") or ""))
                parts.append(
                    "<div class=\"card\">"
                    f"<div class=\"label\">{escape(str(item.get('label') or ''))}</div>"
                    f"<div class=\"value\">{escape(str(value))}</div>"
                    f"<div class=\"label\">{escape(str(item.get('year') or ''))}</div>"
                    "</div>"
                )
            parts.append("</div>")
        elif block_type == "chart":
            chart = block.get("chart") or {}
            if title_text:
                parts.append(f"<h2>{escape(str(title_text))}</h2>")
            if chart.get("type") == "table" or chart.get("columns"):
                _html_table(parts, chart.get("columns") or [], chart.get("rows") or [])
            else:
                _html_bars(parts, chart)
        elif block_type == "table":
            if title_text:
                parts.append(f"<h2>{escape(str(title_text))}</h2>")
            _html_table(parts, block.get("columns") or [], block.get("rows") or [])
        elif block_type == "ranking":
            if title_text:
                parts.append(f"<h2>{escape(str(title_text))}</h2>")
            _html_table(
                parts,
                ["排名", "区域", "数值"],
                [[item.get("rank"), item.get("name"), item.get("value")] for item in block.get("ranking") or []],
            )
        elif block_type == "notice":
            parts.append(f"<div class=\"notice\">{escape(str(block.get('text') or ''))}</div>")
        elif block_type == "source":
            parts.append("<h2>引用与来源</h2><ul class=\"source\">")
            for citation in block.get("citations") or []:
                parts.append(
                    "<li>"
                    + escape(
                        f"{citation.get('indicator') or citation.get('indicator_name')} · "
                        f"{citation.get('region_name') or citation.get('region') or '全部'} · "
                        f"{citation.get('period')} · {citation.get('source')} · "
                        f"数据时效 {citation.get('data_as_of') or '-'}"
                    )
                    + "</li>"
                )
            parts.append("</ul>")

    parts.append(
        "<div class=\"footer\">"
        f"导出编号 {escape(export_id)} ｜ 生成时间 {generated_at.isoformat()} ｜ "
        f"数据时效 {escape(str(as_of))} ｜ 内部资料"
        "</div></div></body></html>"
    )
    return "".join(parts)


def _html_table(parts: list[str], columns: list[Any], rows: list[list[Any]]) -> None:
    escape = html_lib.escape
    parts.append("<table><thead><tr>")
    for column in columns:
        parts.append(f"<th>{escape(str(column))}</th>")
    parts.append("</tr></thead><tbody>")
    for row in rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{escape('无数据' if cell is None else str(cell))}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")


def _html_bars(parts: list[str], chart: dict[str, Any]) -> None:
    escape = html_lib.escape
    categories = chart.get("categories") or []
    series = chart.get("series") or []
    values = series[0].get("values") if series else []
    numbers = [value for value in values if isinstance(value, (int, float))]
    maximum = max(numbers) if numbers else 0
    for category, value in zip(categories, values):
        width = 0 if not maximum or value is None else max(2, int(float(value) / maximum * 100))
        label = "无数据" if value is None else f"{value:g}"
        parts.append(
            "<div class=\"bar-row\">"
            f"<div class=\"bar-label\">{escape(str(category))}</div>"
            f"<div class=\"bar-track\"><div class=\"bar-fill\" style=\"width:{width}%\"></div></div>"
            f"<div class=\"bar-value\">{escape(label)}</div>"
            "</div>"
        )


def _render_browser(kind: str, html: str, path: Path, orientation: str) -> None:
    from playwright.sync_api import sync_playwright

    args = ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True, args=args)
        except Exception:
            try:
                browser = playwright.chromium.launch(headless=True, channel="msedge", args=args)
            except Exception as exc:
                raise ExportRenderError("No Chromium or Edge browser available") from exc
        try:
            if kind == "pdf":
                page = browser.new_page()
                page.set_content(html, wait_until="load")
                page.pdf(
                    path=str(path),
                    format="A4",
                    landscape=orientation == "landscape",
                    print_background=True,
                    margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
                )
                page.close()
            else:
                context = browser.new_context(
                    viewport={"width": 750, "height": 1000},
                    device_scale_factor=2,
                )
                page = context.new_page()
                page.set_content(html, wait_until="load")
                height = page.evaluate(
                    "Math.min(Math.max(document.body.scrollHeight, 400), 8000)"
                )
                page.set_viewport_size({"width": 750, "height": int(height)})
                page.screenshot(path=str(path), full_page=False)
                context.close()
        finally:
            browser.close()


async def _render_file(
    *,
    kind: str,
    snapshot: Snapshot,
    title: str,
    export_id: str,
    generated_at: datetime,
    user: User,
    options: ExportOptions,
    path: Path,
    is_answer: bool,
) -> None:
    if kind == "csv":
        _write_csv(snapshot, title=title, export_id=export_id, path=path)
        return
    if kind == "xlsx":
        _write_xlsx(
            snapshot,
            title=title,
            export_id=export_id,
            generated_at=generated_at,
            path=path,
            is_answer=is_answer,
        )
        return
    watermark = _watermark_text(user, generated_at, snapshot.demo)
    markup = _render_html(
        snapshot,
        title=title,
        export_id=export_id,
        generated_at=generated_at,
        watermark=watermark,
    )
    await asyncio.to_thread(_render_browser, kind, markup, path, options.orientation)
    limit = FORMATS[kind]["max_bytes"]
    if path.stat().st_size > limit:
        raise AppError(
            "EXPORT_TOO_LARGE",
            f"{kind.upper()} exceeds its size limit",
            status_code=413,
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _job_out(job: ExportJob) -> ExportJobOut:
    expired = False
    expires = _as_utc(job.expires_at)
    if expires is not None and expires < _utcnow():
        expired = True
    status = "expired" if expired and job.status == "ready" else job.status
    progress = 100 if job.status == "ready" else (30 if job.status == "running" else 0)
    error = None
    if job.error_code or job.error_message:
        error = ExportErrorOut(
            code=job.error_code or "EXPORT_FAILED",
            message=job.error_message or "Export failed",
        )
    download_url = (
        f"/api/v1/exports/{job.export_id}/download"
        if status == "ready" and not expired
        else None
    )
    return ExportJobOut(
        export_id=job.export_id or "",
        status=status,
        progress=progress,
        format=job.format,
        title=job.title or "",
        file_size=job.file_size,
        sha256=job.sha256,
        download_url=download_url,
        expires_at=_as_local(job.expires_at),
        created_at=_as_local(job.created_at),
        error=error,
    )


def _component_versions(blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    versions: dict[str, str] = {}
    for block in blocks:
        component = block.get("component")
        if component:
            versions[str(component)] = "1.0.0"
    return [{"key": key, "version": version} for key, version in sorted(versions.items())]


async def create_export(
    session: AsyncSession,
    *,
    request: Request,
    settings: Settings,
    user: User,
    payload: ExportCreateRequest,
) -> ExportJobOut:
    if user.role not in ALLOWED_ROLES:
        raise _forbidden()
    if payload.format is None or not payload.format.strip():
        raise AppError(
            "EXPORT_FORMAT_REQUIRED",
            "A format must be selected explicitly",
            status_code=422,
        )
    fmt = payload.format.strip().lower()
    if fmt not in FORMATS:
        raise AppError(
            "EXPORT_FORMAT_UNSUPPORTED",
            "Unsupported export format",
            status_code=422,
            details={"format": payload.format},
        )

    if payload.source_type == "answer":
        if not payload.source_id:
            raise _source_not_found("answer source_id is required")
        snapshot = await _answer_snapshot(session, user=user, source_id=payload.source_id)
    else:
        snapshot = await _report_snapshot(session, user=user, request_payload=payload)

    if not _supports_format(snapshot, fmt):
        raise AppError(
            "EXPORT_FORMAT_UNSUPPORTED",
            "The answer has no single table; choose XLSX, PDF, or PNG",
            status_code=422,
        )

    options = payload.options or ExportOptions(
        orientation="portrait",
        include_citations=True,
        watermark=True,
        max_rows=settings.export_max_rows,
    )
    title = _sanitize_title(payload.title) or _sanitize_title(snapshot.title) or "导出"
    export_id = _new_export_id()
    created_at = _utcnow()
    expires_at = created_at + timedelta(days=settings.export_retention_days)
    view_spec = {
        "orientation": options.orientation,
        "include_citations": options.include_citations,
        "watermark": True,
        "max_rows": min(options.max_rows, settings.export_max_rows),
        "theme": "gov-baseline",
    }
    blocks_snapshot = {
        "answer_id": snapshot.source_id,
        "answer_markdown": snapshot.answer_markdown,
        "blocks": snapshot.blocks,
        "citations": snapshot.citations,
        "meta": snapshot.meta,
    }
    job = ExportJob(
        export_id=export_id,
        user_id=user.id,
        source_type=payload.source_type,
        source_id=snapshot.source_id[:32],
        format=fmt,
        status="running",
        title=title,
        target="mp" if payload.source_type == "report" else "answer",
        params=payload.source.model_dump(mode="json") if payload.source is not None else None,
        view_spec=view_spec,
        answer_blocks=blocks_snapshot,
        component_versions=_component_versions(snapshot.blocks),
        registry_version=settings.export_registry_version,
        data_version=snapshot.meta.get("data_version"),
        data_hash=snapshot.meta.get("data_hash"),
        renderer_version=settings.export_renderer_version,
        started_at=created_at,
        expires_at=expires_at,
    )
    session.add(job)
    await session.flush()
    await write_audit(
        session,
        action="export.requested",
        resource_type="export",
        resource_id=export_id,
        detail={
            "format": fmt,
            "source_type": payload.source_type,
            "source_id": snapshot.source_id,
            "demo": snapshot.demo,
        },
        request=request,
        user_id=user.id,
    )

    directory = Path(settings.export_dir) / f"{created_at:%Y}" / f"{created_at:%m}"
    directory.mkdir(parents=True, exist_ok=True)
    filename = _filename(title, snapshot.period_label, export_id, FORMATS[fmt]["ext"])
    path = directory / filename
    relative = f"{created_at:%Y}/{created_at:%m}/{filename}"
    try:
        await _render_file(
            kind=fmt,
            snapshot=snapshot,
            title=title,
            export_id=export_id,
            generated_at=_as_local(created_at) or created_at,
            user=user,
            options=options,
            path=path,
            is_answer=payload.source_type == "answer",
        )
        job.status = "ready"
        job.file_path = relative
        job.file_size = path.stat().st_size
        job.sha256 = _sha256_file(path)
        job.finished_at = _utcnow()
        await write_audit(
            session,
            action="export.ready",
            resource_type="export",
            resource_id=export_id,
            detail={"format": fmt, "file_size": job.file_size},
            request=request,
            user_id=user.id,
        )
    except AppError as exc:
        job.status = "failed"
        job.error_code = exc.code
        job.error_message = exc.message
        job.finished_at = _utcnow()
        await write_audit(
            session,
            action="export.failed",
            resource_type="export",
            resource_id=export_id,
            detail={"format": fmt, "code": exc.code},
            request=request,
            user_id=user.id,
        )
    except Exception as exc:  # noqa: BLE001 - failure is reported on the job
        logger.exception("Export rendering failed")
        job.status = "failed"
        job.error_code = "EXPORT_FAILED"
        job.error_message = "Export rendering failed"
        job.finished_at = _utcnow()
        await write_audit(
            session,
            action="export.failed",
            resource_type="export",
            resource_id=export_id,
            detail={"format": fmt, "reason": type(exc).__name__},
            request=request,
            user_id=user.id,
        )
    await session.commit()
    return _job_out(job)


async def _load_export(
    session: AsyncSession,
    *,
    export_id: str,
    user: User,
) -> ExportJob:
    job = (
        await session.execute(
            select(ExportJob).where(ExportJob.export_id == export_id)
        )
    ).scalars().first()
    if job is None:
        raise _not_found()
    if job.user_id != user.id and not _is_privileged(user):
        raise AppError(
            "EXPORT_FORBIDDEN",
            "Export belongs to another user",
            status_code=403,
        )
    return job


async def get_export(
    session: AsyncSession,
    *,
    export_id: str,
    user: User,
) -> ExportJobOut:
    job = await _load_export(session, export_id=export_id, user=user)
    expires = _as_utc(job.expires_at)
    if expires is not None and expires < _utcnow() and job.status == "ready":
        job.status = "expired"
        await session.commit()
    return _job_out(job)


async def download_export(
    session: AsyncSession,
    *,
    request: Request,
    export_id: str,
    user: User,
    settings: Settings,
) -> tuple[Path, str, str]:
    job = await _load_export(session, export_id=export_id, user=user)
    expires = _as_utc(job.expires_at)
    if expires is not None and expires < _utcnow():
        if job.status != "expired":
            job.status = "expired"
            await session.commit()
        raise AppError(
            "EXPORT_EXPIRED",
            "Export file has expired",
            status_code=410,
        )
    if job.status != "ready" or not job.file_path:
        raise _not_found()
    path = Path(settings.export_dir) / job.file_path
    if not path.is_file():
        raise _not_found()
    job.download_count = (job.download_count or 0) + 1
    await write_audit(
        session,
        action="export.downloaded",
        resource_type="export",
        resource_id=export_id,
        detail={"format": job.format, "download_count": job.download_count},
        request=request,
        user_id=user.id,
    )
    await session.commit()
    filename = _filename(
        job.title or "导出",
        "",
        job.export_id or export_id,
        FORMATS[job.format]["ext"],
    )
    return path, filename, FORMATS[job.format]["mime"]
