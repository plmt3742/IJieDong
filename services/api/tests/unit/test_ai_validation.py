"""Unit tests for answer parsing, ChartSpec, and numeric provenance."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.ai.validation import AiValidationError, assert_no_null_to_zero, parse_answer_draft
from app.schemas.ai import ChartSpec
from app.services.ai_service import compute_data_hash

CITATION = {
    "id": "c1",
    "indicator": "常住人口",
    "indicator_code": "population_resident",
    "region": "曲溪街道",
    "region_code": "JD-T-01",
    "region_name": "曲溪街道",
    "region_level": "town",
    "period": "2025",
    "source": "data_values",
    "data_as_of": "2026-11-10",
}


def _chart_block(values: list[float | None], categories: list[str] | None = None) -> dict:
    categories = categories or ["曲溪街道"]
    return {
        "id": "b1",
        "type": "chart",
        "component": "bar_chart",
        "props": {},
        "data_ref": {"indicator_codes": ["population_resident"]},
        "citations": [CITATION],
        "chart": {
            "version": "1.0",
            "type": "bar",
            "title": "常住人口",
            "unit": "人",
            "categories": categories,
            "series": [{"name": "常住人口", "values": values}],
        },
    }


def _draft(block: dict) -> dict:
    return {
        "answer_markdown": "2025 年常住人口数据见图表。",
        "intent": "lookup",
        "blocks": [block],
        "citations": [CITATION],
        "actions": [],
        "follow_up_questions": [],
        "status": "done",
    }


def test_chart_spec_accepts_valid_bar() -> None:
    spec = ChartSpec(
        version="1.0",
        type="bar",
        title="常住人口",
        categories=["A"],
        series=[{"name": "常住人口", "values": [1]}],
    )
    assert spec.type == "bar"


def test_chart_spec_rejects_missing_series() -> None:
    with pytest.raises(ValidationError):
        ChartSpec(version="1.0", type="bar", title="常住人口", categories=["A"])


def test_chart_spec_rejects_echarts_option() -> None:
    with pytest.raises(ValidationError):
        ChartSpec(
            version="1.0",
            type="bar",
            title="常住人口",
            categories=["A"],
            series=[{"name": "常住人口", "values": [1]}],
            option={"xAxis": {}},
        )


def test_chart_spec_table_requires_rows() -> None:
    with pytest.raises(ValidationError):
        ChartSpec(version="1.0", type="table", title="表", columns=["A"])


def test_text_indicator_cannot_be_charted() -> None:
    payload = _draft(_chart_block([1]))
    payload["blocks"][0]["data_ref"] = {"indicator_codes": ["region_intro"]}
    with pytest.raises(AiValidationError):
        parse_answer_draft(payload, text_codes={"region_intro"})


def test_props_only_blocks_are_hydrated_from_canonical_shape() -> None:
    payload = {
        "answer_markdown": "2025 年云路镇常住人口为 31038 人。",
        "intent": "lookup",
        "blocks": [
            {
                "id": "b1",
                "type": "summary",
                "component": "SummaryCard",
                "props": {"text": "2025 年云路镇常住人口为 31038 人。", "citation_ids": ["c1"]},
            },
            {
                "id": "b2",
                "type": "metric_grid",
                "component": "MetricGrid",
                "props": {
                    "metrics": [
                        {
                            "label": "常住人口",
                            "value": 31038,
                            "unit": "人",
                            "period": "2025",
                            "region": "云路镇",
                            "citation_ids": ["c1"],
                        }
                    ]
                },
            },
            {
                "id": "b3",
                "type": "source",
                "component": "SourceNote",
                "props": {"text": "数据来源：已发布观测值", "citations": ["c1"]},
            },
        ],
        "citations": [CITATION],
        "actions": [],
        "follow_up_questions": [],
        "status": "done",
    }

    draft = parse_answer_draft(payload)

    assert draft.blocks[0].text == "2025 年云路镇常住人口为 31038 人。"
    assert draft.blocks[1].metrics is not None
    assert draft.blocks[1].metrics[0].year == "2025"
    assert draft.blocks[1].metrics[0].citation_id == "c1"
    assert draft.blocks[2].props["citations"] == ["c1"]


def test_null_observation_cannot_be_rendered_as_zero() -> None:
    payload = _draft(_chart_block([0]))
    with pytest.raises(AiValidationError):
        parse_answer_draft(
            payload,
            expected={("population_resident", "曲溪街道"): None},
        )


def test_zero_is_allowed_when_the_tool_returns_zero() -> None:
    payload = _draft(_chart_block([0]))
    draft = parse_answer_draft(
        payload,
        expected={("population_resident", "曲溪街道"): 0},
    )
    assert draft.blocks[0].chart is not None


def test_mismatched_number_is_rejected() -> None:
    payload = _draft(_chart_block([999]))
    with pytest.raises(AiValidationError):
        parse_answer_draft(
            payload,
            expected={("population_resident", "曲溪街道"): 31038},
        )


def test_unknown_citation_is_rejected() -> None:
    block = _chart_block([1])
    block["citations"] = [dict(CITATION, id="c9", citation_id="c9")]
    payload = _draft(block)
    payload["blocks"][0]["metrics"] = [
        {
            "label": "常住人口",
            "value": 1,
            "unit": "人",
            "citation_id": "c9",
        }
    ]
    payload["blocks"][0]["type"] = "metric_grid"
    payload["blocks"][0].pop("chart")
    with pytest.raises(AiValidationError):
        parse_answer_draft(payload)


def test_assert_no_null_to_zero_helper() -> None:
    assert_no_null_to_zero(
        ["A"],
        [1.0],
        {("population_resident", "A"): 1.0},
        "population_resident",
    )
    with pytest.raises(AiValidationError):
        assert_no_null_to_zero(
            ["A"],
            [0.0],
            {("population_resident", "A"): None},
            "population_resident",
        )


def test_data_hash_is_order_independent_and_preserves_nulls() -> None:
    rows = [
        {"indicator_code": "population_resident", "region_code": "B", "period": 2025, "value": None},
        {"indicator_code": "population_resident", "region_code": "A", "period": 2025, "value": 1.5},
    ]
    first = compute_data_hash(rows, "dv_test")
    second = compute_data_hash(list(reversed(rows)), "dv_test")
    assert first == second
    assert first.startswith("sha256:")
    changed = compute_data_hash([{**rows[0], "value": 0}, rows[1]], "dv_test")
    assert changed != first
