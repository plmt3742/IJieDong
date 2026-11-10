"""AI chat session and message models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, bigint_pk_type


class ChatSession(TimestampMixin, Base):
    """Conversation container owned by a user (``NULL`` for guest sessions)."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        bigint_pk_type(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChatMessage(Base):
    """One user/assistant/tool turn with rendering and provenance payloads."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'tool')",
            name="ck_chat_messages_role",
        ),
        Index(
            "ix_chat_messages_session_created_at",
            "session_id",
            "created_at",
        ),
        Index("uq_chat_messages_answer_id", "answer_id", unique=True),
    )

    id: Mapped[int] = mapped_column(bigint_pk_type(), primary_key=True)
    session_id: Mapped[int] = mapped_column(
        bigint_pk_type(),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    answer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tool_calls: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    chart_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    blocks: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    data_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    citations: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
