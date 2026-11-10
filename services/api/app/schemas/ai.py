"""Pydantic contracts for AI answers and chat sessions.

The wire shape follows ``docs/agent/24-ai-and-component-spec.md`` and stays
compatible with ``apps/mp/miniprogram/types/api.ts``: each block carries the
canonical ``props`` payload plus flattened display fields the mini program reads.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChartType = Literal["bar", "hbar", "line", "pie", "table"]
BlockType = Literal[
    "summary",
    "metric_grid",
    "chart",
    "table",
    "ranking",
    "comparison",
    "insight",
    "source",
    "notice",
    "actions",
]
Intent = Literal[
    "lookup",
    "rank",
    "compare",
    "trend",
    "composition",
    "profile",
    "relationship",
    "export",
    "clarify",
    "refuse",
]
AnswerStatus = Literal["done", "refused", "no_data"]
NoticeLevel = Literal["info", "warning", "error", "success"]
ActionType = Literal["navigate", "export", "apply", "retry"]

MAX_ANSWER_MARKDOWN = 2000
MAX_BLOCKS = 8
MAX_CITATIONS_PER_BLOCK = 30
MAX_PROPS_BYTES = 16 * 1024
NUMERIC_BLOCK_TYPES = {"metric_grid", "chart", "table", "ranking", "comparison"}


class ChartSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=80)
    values: list[float | None] = Field(..., min_length=1, max_length=50)


class ChartOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    show_values: bool | None = None
    sort: Literal["none", "asc", "desc"] | None = None
    max_items: int | None = Field(None, ge=1, le=50)


class ChartSpec(BaseModel):
    """Platform-neutral chart contract; never an ECharts option or JavaScript."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field("1.0", min_length=1, max_length=8)
    type: ChartType
    title: str = Field(..., min_length=1, max_length=120)
    subtitle: str | None = Field(None, max_length=200)
    unit: str | None = Field(None, max_length=32)
    categories: list[str] | None = Field(None, max_length=15)
    series: list[ChartSeries] | None = Field(None, max_length=3)
    columns: list[str] | None = Field(None, max_length=12)
    rows: list[list[str | int | float | None]] | None = Field(None, max_length=100)
    options: ChartOptions | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> ChartSpec:
        if self.type == "table":
            if not self.columns or self.rows is None:
                raise ValueError("table charts require columns and rows")
            for row in self.rows:
                if len(row) != len(self.columns):
                    raise ValueError("table row width must match columns")
            return self
        if not self.categories or not self.series:
            raise ValueError(f"{self.type} charts require categories and series")
        for series in self.series:
            if len(series.values) != len(self.categories):
                raise ValueError("series length must match categories")
        return self


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=32)
    citation_id: str | None = Field(None, max_length=32)
    indicator: str = Field(..., min_length=1, max_length=120)
    indicator_name: str | None = Field(None, max_length=120)
    indicator_id: int | None = None
    indicator_code: str = Field(..., min_length=1, max_length=64)
    region: str | None = Field(None, max_length=120)
    region_id: int | None = None
    region_code: str | None = Field(None, max_length=64)
    region_name: str | None = Field(None, max_length=120)
    region_level: str = Field(..., min_length=1, max_length=16)
    period: str = Field(..., min_length=1, max_length=16)
    source: str = Field(..., min_length=1, max_length=32)
    data_as_of: str | None = Field(None, max_length=32)

    @model_validator(mode="after")
    def _fill_citation_id(self) -> Citation:
        if not self.citation_id:
            object.__setattr__(self, "citation_id", self.id)
        return self


class AnswerAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, max_length=32)
    label: str = Field(..., min_length=1, max_length=20)
    type: ActionType
    url: str | None = Field(None, max_length=200)
    target: str | None = Field(None, max_length=200)
    permission: str | None = Field(None, max_length=32)
    indicator_id: int | None = None
    indicator_code: str | None = Field(None, max_length=64)
    region_id: int | None = None
    period: str | None = Field(None, max_length=16)


class MetricGridItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1, max_length=80)
    value: float | str | None = None
    unit: str | None = Field(None, max_length=32)
    year: int | str | None = None
    quality_status: str | None = Field(None, max_length=16)
    display: str | None = Field(None, max_length=80)
    citation_id: str | None = Field(None, max_length=32)


class RankingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=120)
    value: float | None = None
    unit: str | None = Field(None, max_length=32)
    region_code: str | None = Field(None, max_length=64)
    citation_id: str | None = Field(None, max_length=32)


class AnswerBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=8)
    type: BlockType
    component: str = Field(..., min_length=1, max_length=64)
    props: dict[str, Any] = Field(default_factory=dict)
    data_ref: dict[str, Any] | None = None
    fallback: dict[str, Any] | None = None

    key: str | None = Field(None, max_length=32)
    title: str | None = Field(None, max_length=120)
    text: str | None = Field(None, max_length=2000)
    chart: ChartSpec | None = None
    metrics: list[MetricGridItem] | None = Field(None, max_length=6)
    columns: list[str] | None = Field(None, max_length=12)
    rows: list[list[str | int | float | None]] | None = Field(None, max_length=100)
    ranking: list[RankingEntry] | None = Field(None, max_length=15)
    citations: list[Citation] | None = Field(None, max_length=MAX_CITATIONS_PER_BLOCK)
    actions: list[AnswerAction] | None = Field(None, max_length=3)
    source: str | None = Field(None, max_length=200)
    level: NoticeLevel | None = None

    @model_validator(mode="before")
    @classmethod
    def _hydrate_from_props(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        block = dict(data)
        props = block.get("props")
        if not isinstance(props, dict):
            return block

        def set_missing(field: str, value: Any) -> None:
            if value is not None and block.get(field) is None:
                block[field] = value

        block_type = block.get("type")
        if block_type == "source":
            source_ids = block.get("citations")
            if (
                isinstance(source_ids, list)
                and source_ids
                and all(isinstance(value, str) for value in source_ids)
            ):
                props = dict(props)
                props.setdefault("citations", source_ids)
                block["props"] = props
                block["citations"] = None
        set_missing("title", props.get("title"))
        if block_type == "summary":
            set_missing("text", props.get("text"))
        elif block_type in {"metric_grid", "comparison"}:
            items = props.get("metrics") or props.get("items")
            if isinstance(items, list):
                normalized: list[dict[str, Any]] = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    entry = dict(item)
                    if entry.get("year") is None and entry.get("period") is not None:
                        entry["year"] = entry.pop("period")
                    if not entry.get("citation_id"):
                        citations = entry.get("citation_ids")
                        if isinstance(citations, list) and citations:
                            entry["citation_id"] = citations[0]
                    entry.pop("citation_ids", None)
                    entry.pop("region", None)
                    normalized.append(entry)
                set_missing("metrics", normalized)
        elif block_type == "chart":
            set_missing("chart", props.get("chart"))
        elif block_type == "table":
            set_missing("columns", props.get("columns"))
            set_missing("rows", props.get("rows"))
        elif block_type == "ranking":
            items = props.get("ranking") or props.get("items")
            if isinstance(items, list):
                normalized = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    entry = dict(item)
                    if not entry.get("name"):
                        entry["name"] = (
                            entry.pop("region_name", None)
                            or entry.pop("region", None)
                            or entry.get("label")
                        )
                    entry.pop("label", None)
                    entry.pop("region_name", None)
                    entry.pop("region", None)
                    normalized.append(entry)
                set_missing("ranking", normalized)
        elif block_type == "notice":
            set_missing("text", props.get("text"))
            set_missing("level", props.get("level") or "info")
        elif block_type == "actions":
            set_missing("actions", props.get("actions"))
        elif block_type == "source":
            set_missing("text", props.get("text"))
        return block

    @model_validator(mode="after")
    def _check_block_shape(self) -> AnswerBlock:
        if self.type == "chart" and self.chart is None:
            raise ValueError("chart blocks require a ChartSpec")
        if self.type == "metric_grid" and not self.metrics:
            raise ValueError("metric_grid blocks require metrics")
        if self.type == "table":
            if not self.columns or self.rows is None:
                raise ValueError("table blocks require columns and rows")
            for row in self.rows:
                if len(row) != len(self.columns):
                    raise ValueError("table row width must match columns")
        if self.type == "ranking" and not self.ranking:
            raise ValueError("ranking blocks require ranking items")
        if self.type == "comparison" and not self.metrics:
            raise ValueError("comparison blocks require items")
        if self.type == "summary" and not self.text:
            raise ValueError("summary blocks require text")
        if self.type == "source":
            props_citations = self.props.get("citations") or self.props.get("citation_ids")
            if not self.citations and not (
                isinstance(props_citations, list) and props_citations
            ):
                raise ValueError("source blocks require citations")
        if self.type == "notice" and (not self.text or not self.level):
            raise ValueError("notice blocks require text and level")
        if self.type == "actions" and not self.actions:
            raise ValueError("actions blocks require actions")
        encoded = json.dumps(self.props, ensure_ascii=False, default=str).encode("utf-8")
        if len(encoded) > MAX_PROPS_BYTES:
            raise ValueError("block props exceed 16 KB")
        return self


class AnswerMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1, max_length=128)
    model: str = Field(..., min_length=1, max_length=64)
    latency_ms: int = Field(..., ge=0)
    tool_calls: int = Field(..., ge=0)
    data_version: str = Field(..., min_length=1, max_length=32)
    data_hash: str = Field(..., min_length=8, max_length=80)
    registry_version: str = Field(..., min_length=1, max_length=16)
    generated_at: datetime
    degraded: bool
    locale: str = Field("zh-CN", max_length=16)


class AnswerEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_id: str = Field(..., min_length=1, max_length=32)
    answer_markdown: str = Field(..., min_length=1, max_length=MAX_ANSWER_MARKDOWN)
    intent: Intent
    blocks: list[AnswerBlock] = Field(..., min_length=1, max_length=MAX_BLOCKS)
    citations: list[Citation] = Field(default_factory=list, max_length=30)
    actions: list[AnswerAction] = Field(default_factory=list, max_length=3)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)
    meta: AnswerMeta

    @model_validator(mode="after")
    def _check_envelope(self) -> AnswerEnvelope:
        known = {citation.id for citation in self.citations}
        numeric_blocks = [block for block in self.blocks if block.type in NUMERIC_BLOCK_TYPES]
        if numeric_blocks and not self.citations:
            raise ValueError("numeric blocks require at least one citation")
        for block in numeric_blocks:
            referenced = {citation.id for citation in (block.citations or [])}
            for item in block.metrics or []:
                if item.citation_id:
                    referenced.add(item.citation_id)
            for item in block.ranking or []:
                if item.citation_id:
                    referenced.add(item.citation_id)
            if not referenced:
                raise ValueError(f"{block.type} block requires a citation reference")
            unknown = referenced - known
            if unknown:
                raise ValueError(f"unknown citation ids: {sorted(unknown)}")
        for question in self.follow_up_questions:
            if len(question) > 30:
                raise ValueError("follow-up questions must be at most 30 characters")
        return self


class AIContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str | None = Field(None, max_length=16)
    region_id: int | None = None
    indicator_id: int | None = None


class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=500)
    session_id: int | None = None
    context: AIContext | None = None


class AIChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: int | None
    message_id: int | None
    answer_id: str
    answer_markdown: str
    blocks: list[AnswerBlock]
    chart_spec: ChartSpec | None
    citations: list[Citation]
    follow_up_questions: list[str]
    status: AnswerStatus
    demo: bool
    intent: Intent
    meta: AnswerMeta


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    title: str | None
    message_count: int = Field(..., ge=0)
    created_at: datetime | None
    updated_at: datetime | None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    session_id: int
    role: str
    content: str
    answer_id: str | None
    blocks: list[dict[str, Any]] | None
    citations: list[dict[str, Any]] | None
    chart_spec: dict[str, Any] | None
    model: str | None
    latency_ms: int | None
    created_at: datetime | None
