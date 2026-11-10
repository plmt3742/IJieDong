"""Answer draft parsing and the five-layer validation helpers from spec 24.

``AnswerDraft`` is the model-agnostic part of an answer. The service adds
``answer_id`` and ``meta`` only after validation so a bad model response can never
reach persistence or the client.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.models import Indicator
from app.schemas.ai import (
    AnswerAction,
    AnswerBlock,
    AnswerStatus,
    Citation,
    Intent,
    NUMERIC_BLOCK_TYPES,
    MAX_ANSWER_MARKDOWN,
    MAX_BLOCKS,
)

FORBIDDEN_KEYS = {
    "option",
    "echarts",
    "echarts_option",
    "sql",
    "javascript",
    "script",
    "html",
}


class AiValidationError(ValueError):
    """Raised when a model answer violates a structural or policy rule."""


class AnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_markdown: str = Field(..., min_length=1, max_length=MAX_ANSWER_MARKDOWN)
    intent: Intent
    blocks: list[AnswerBlock] = Field(..., min_length=1, max_length=MAX_BLOCKS)
    citations: list[Citation] = Field(default_factory=list, max_length=30)
    actions: list[AnswerAction] = Field(default_factory=list, max_length=3)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)
    status: AnswerStatus = "done"

    @model_validator(mode="after")
    def _check_citations(self) -> AnswerDraft:
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


@dataclass
class AgentAnswer:
    """Validated draft plus non-wire provenance collected while producing it."""

    draft: AnswerDraft
    tool_calls: int
    rows: list[dict[str, Any]] = field(default_factory=list)
    demo: bool = True
    token_usage: dict[str, int] | None = None


def text_indicator_codes(indicators: list[Indicator]) -> set[str]:
    return {indicator.code for indicator in indicators if indicator.value_type == "long_text"}


def _scan_forbidden_keys(value: Any, path: str = "props") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise AiValidationError(f"forbidden key {path}.{key}")
            _scan_forbidden_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_forbidden_keys(item, f"{path}[{index}]")


def _check_no_text_chart(block: AnswerBlock, text_codes: set[str]) -> None:
    if block.type not in {"chart", "ranking", "comparison"}:
        return
    ref = block.data_ref or {}
    codes = set(ref.get("indicator_codes") or [])
    if not codes and ref.get("indicator_code"):
        codes.add(str(ref["indicator_code"]))
    bad = codes & text_codes
    if bad:
        raise AiValidationError(f"text indicators cannot be charted: {sorted(bad)}")


def _close(left: float, right: float) -> bool:
    scale = max(abs(left), abs(right), 1.0)
    return abs(left - right) <= max(0.51, scale * 0.005)


def assert_no_null_to_zero(
    categories: list[str],
    values: list[float | None],
    expected: dict[tuple[str, str], float | None],
    indicator_code: str,
) -> None:
    """Reject a chart that renders a null observation as zero or changes a value."""
    for category, value in zip(categories, values):
        key = (indicator_code, category)
        if key not in expected:
            continue
        reference = expected[key]
        if reference is None:
            if value is not None:
                raise AiValidationError(
                    f"null observation rendered as a number for {category}"
                )
            continue
        if value is None:
            continue
        if not _close(float(value), float(reference)):
            raise AiValidationError(
                f"value for {category} does not match the tool result"
            )


def _check_provenance(
    block: AnswerBlock,
    expected: dict[tuple[str, str], float | None],
) -> None:
    ref = block.data_ref or {}
    codes = list(ref.get("indicator_codes") or [])
    if not codes and ref.get("indicator_code"):
        codes.append(str(ref["indicator_code"]))
    if not codes:
        return
    code = str(codes[0])
    if block.type == "chart" and block.chart is not None:
        if block.chart.categories and block.chart.series:
            assert_no_null_to_zero(
                block.chart.categories,
                block.chart.series[0].values,
                expected,
                code,
            )
    if block.type == "ranking" and block.ranking:
        categories = [item.name for item in block.ranking]
        values = [item.value for item in block.ranking]
        assert_no_null_to_zero(categories, values, expected, code)


def parse_answer_draft(
    raw: str | dict[str, Any],
    *,
    text_codes: set[str] | None = None,
    expected: dict[tuple[str, str], float | None] | None = None,
) -> AnswerDraft:
    """Parse JSON, then apply Pydantic, component, policy, and provenance checks."""
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.rstrip().endswith("```"):
                text = text.rsplit("```", 1)[0]
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AiValidationError("answer is not valid JSON") from exc
    else:
        payload = raw
    if not isinstance(payload, dict):
        raise AiValidationError("answer must be a JSON object")
    try:
        draft = AnswerDraft.model_validate(payload)
    except ValidationError as exc:
        raise AiValidationError(f"answer failed schema validation: {exc.errors()}") from exc

    text_codes = text_codes or set()
    expected = expected or {}
    for block in draft.blocks:
        _scan_forbidden_keys(block.props)
        _check_no_text_chart(block, text_codes)
        if block.chart is not None:
            _scan_forbidden_keys(block.chart.model_dump(), path=f"block[{block.id}].chart")
        _check_provenance(block, expected)
    cited = {citation.id for citation in draft.citations}
    for block in draft.blocks:
        if block.type == "source":
            source_ids = {citation.id for citation in block.citations or []}
            props_citations = block.props.get("citations") or block.props.get("citation_ids")
            if isinstance(props_citations, list):
                source_ids |= {str(value) for value in props_citations}
            missing = source_ids - cited
            if missing:
                raise AiValidationError(f"source block cites unknown ids: {sorted(missing)}")
    return draft
