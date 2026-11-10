"""Deterministic rule-based agent used when no LLM key is configured.

It resolves entities against the seeded database, calls the same read-only tools
as the LLM path, and renders only values returned by those tools. Every answer
carries citations and a demo notice so the synthetic seed is never mistaken for
real statistics.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools import (
    ToolContext,
    ToolError,
    execute_tool,
    today_iso,
)
from app.ai.validation import AgentAnswer, AnswerDraft
from app.models import Indicator, Region, RegionAlias
from app.schemas.ai import (
    AnswerAction,
    AnswerBlock,
    AnswerStatus,
    BlockType,
    ChartOptions,
    ChartSeries,
    ChartSpec,
    Citation,
    Intent,
    MetricGridItem,
    RankingEntry,
)
from app.services import query_service

DEFAULT_PERIOD = query_service.DEFAULT_PERIOD_YEAR

REFUSE_KEYWORDS = (
    "预测",
    "明年",
    "预估",
    "因果",
    "相关性",
    "有关系吗",
    "手机号",
    "身份证",
    "密码",
    "openid",
    "密钥",
    "系统提示",
    "忽略以上",
    "忽略上面",
    "执行命令",
    "脚本",
    "关系",
)
PROFILE_KEYWORDS = ("介绍", "画像", "概况", "基本情况", "简介")
RANK_KEYWORDS = ("排名", "排行", "前", "top", "最大", "最多", "最高", "最低")
COMPARE_KEYWORDS = ("比较", "对比", "差异", "相差")

INDICATOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "population_resident": ("常住人口", "常住"),
    "population_household": ("户籍人口", "户籍"),
    "area": ("区域面积", "面积"),
    "gdp": ("地区生产总值", "生产总值", "GDP", "gdp"),
    "budget_revenue": ("一般公共预算收入", "预算收入"),
    "budget_expenditure": ("一般公共预算支出", "预算支出"),
    "import_export_total": ("进出口总额", "进出口"),
    "fixed_asset_investment": ("固定资产投资",),
    "industrial_investment": ("工业投资额", "工业投资"),
    "retail_total": ("社会消费品零售总额", "零售总额", "零售"),
    "farmland_area": ("耕地面积", "耕地"),
    "forest_area": ("林地面积", "林地"),
    "admin_village_count": ("行政村数量", "行政村"),
}

FOLLOW_UPS = {
    "lookup": ["要看户籍人口吗？", "要不要看各镇街排名？"],
    "rank": ["要看前 10 名吗？", "要不要对比其中两个镇街？"],
    "compare": ["要看差值百分比吗？", "要不要再比较一个镇街？"],
    "profile": ["要常住人口排名吗？", "要不要看耕地面积？"],
    "clarify": ["请补充镇街名称或指标名称。", "可以问“2025 年各镇街常住人口排名”。"],
}


def _fmt(value: float | None, unit: str, precision: int = 0) -> str:
    if value is None:
        return "无数据"
    if unit in {"人", "个"}:
        return f"{int(round(value))} {unit}"
    return f"{value:.{precision}f} {unit}".strip()


def _block(
    block_id: str,
    block_type: BlockType,
    component: str,
    props: dict[str, Any],
    **flat: Any,
) -> AnswerBlock:
    return AnswerBlock(
        id=block_id,
        type=block_type,
        component=component,
        props=props,
        **flat,
    )


def _citations(payload: dict[str, Any]) -> list[Citation]:
    return [Citation.model_validate(item) for item in payload.get("citations", [])]


def _attach_data_ref(
    blocks: list[AnswerBlock],
    *,
    indicator_codes: list[str],
    region_codes: list[str],
    periods: list[str],
    level: str,
) -> None:
    reference = {
        "indicator_codes": indicator_codes,
        "region_codes": region_codes,
        "periods": periods,
        "level": level,
        "tool_call_id": "tc_1",
    }
    for block in blocks:
        if block.type in {"metric_grid", "chart", "table", "ranking", "comparison"}:
            if block.data_ref is None:
                block.data_ref = dict(reference)


def _demo_notice(block_id: str) -> AnswerBlock:
    text = "当前使用演示数据（合成），仅用于展示流程，不作为决策依据。"
    return _block(
        block_id,
        "notice",
        "text",
        {"level": "info", "code": "DEMO_DATA", "text": text},
        level="info",
        text=text,
        title="演示数据",
    )


def _source_block(block_id: str, citations: list[Citation], data_as_of: str | None) -> AnswerBlock:
    ids = [citation.id for citation in citations]
    text = "数据来源：data_values；指标与区域见引用。"
    return _block(
        block_id,
        "source",
        "source_card",
        {"citation_ids": ids, "data_as_of": data_as_of, "generated_at": today_iso()},
        citations=citations,
        title="引用与来源",
        text=text,
    )


def _actions_block(block_id: str, region: Region | None, indicator: Indicator | None) -> AnswerBlock:
    actions = [
        AnswerAction(
            key="export",
            label="导出本页",
            type="export",
            url=None,
            indicator_id=None,
            indicator_code=None,
            region_id=None,
            period=None,
        ),
        AnswerAction(
            key="navigate",
            label="查看区域",
            type="navigate",
            url=f"/pages/region-detail/region-detail?region_id={region.id}" if region else "/pages/regions/regions",
            region_id=region.id if region else None,
            indicator_id=indicator.id if indicator else None,
            indicator_code=indicator.code if indicator else None,
            period=str(DEFAULT_PERIOD),
        ),
    ]
    return _block(
        block_id,
        "actions",
        "action_row",
        {"actions": [action.model_dump(mode="json") for action in actions]},
        actions=actions,
        title="下一步",
    )


def _actions_in(blocks: list[AnswerBlock]) -> list[AnswerAction]:
    for block in blocks:
        if block.type == "actions" and block.actions:
            return list(block.actions)
    return []


def _notice_only(
    *,
    intent: Intent,
    status: AnswerStatus,
    text: str,
    code: str,
    tool_calls: int = 0,
    rows: list[dict[str, Any]] | None = None,
) -> AgentAnswer:
    level = "error" if status == "refused" else "warning"
    block = _block(
        "b1",
        "notice",
        "text",
        {"level": level, "code": code, "text": text, "suggestions": FOLLOW_UPS["clarify"]},
        level=level,
        text=text,
        title="无法回答" if status == "refused" else "暂无数据",
    )
    draft = AnswerDraft(
        answer_markdown=text,
        intent=intent,
        blocks=[block],
        citations=[],
        actions=[],
        follow_up_questions=FOLLOW_UPS["clarify"],
        status=status,
    )
    return AgentAnswer(draft=draft, tool_calls=tool_calls, rows=rows or [], demo=True)


def _find_regions(
    question: str,
    regions: list[Region],
    aliases: dict[str, Region],
) -> list[Region]:
    matches: list[tuple[int, int, Region]] = []
    for region in regions:
        index = question.find(region.name)
        if index >= 0:
            matches.append((index, -len(region.name), region))
    for alias, region in aliases.items():
        index = question.find(alias)
        if index >= 0 and all(item[2].id != region.id for item in matches):
            matches.append((index, -len(alias), region))
    matches.sort(key=lambda item: (item[0], item[1]))
    deduped: list[Region] = []
    for _, _, region in matches:
        if all(item.id != region.id for item in deduped):
            deduped.append(region)
    return deduped


def _find_indicator(question: str, indicators: dict[str, Indicator]) -> Indicator | None:
    candidates: list[tuple[int, str]] = []
    for code, keywords in INDICATOR_KEYWORDS.items():
        indicator = indicators.get(code)
        if indicator is None:
            continue
        for keyword in keywords:
            if keyword in question:
                candidates.append((len(keyword), code))
                break
    if candidates:
        candidates.sort(reverse=True)
        return indicators.get(candidates[0][1])
    for code, indicator in indicators.items():
        if indicator.name in question:
            return indicator
    return None


def _detect_period(question: str, context_period: str | None) -> int:
    match = re.search(r"(20\d{2})", question)
    if match:
        return int(match.group(1))
    if context_period:
        found = re.search(r"(20\d{2})", context_period)
        if found:
            return int(found.group(1))
    return DEFAULT_PERIOD


def _detect_limit(question: str) -> int:
    match = re.search(r"(?:前|top|Top|TOP)\s*(\d+)", question)
    if not match:
        match = re.search(r"(\d+)\s*名", question)
    if not match:
        return 5
    return max(3, min(int(match.group(1)), 15))


def _detect_level(question: str) -> str:
    if "村" in question:
        return "village"
    if "区" in question and "镇" not in question:
        return "district"
    return "town"


def _detect_intent(
    question: str,
    regions: list[Region],
    indicator: Indicator | None,
) -> str:
    if any(keyword in question for keyword in REFUSE_KEYWORDS):
        return "refuse"
    if any(keyword in question for keyword in PROFILE_KEYWORDS):
        return "profile"
    if any(keyword in question for keyword in COMPARE_KEYWORDS) and len(regions) >= 2:
        return "compare"
    if any(keyword in question for keyword in RANK_KEYWORDS):
        return "rank"
    if len(regions) >= 2 and indicator is not None and ("和" in question or "与" in question):
        return "compare"
    if regions and indicator is not None:
        return "lookup"
    if regions:
        return "profile"
    return "clarify"


async def _lookup(
    ctx: ToolContext,
    *,
    region: Region,
    indicator: Indicator,
    period: int,
) -> AgentAnswer:
    payload = await execute_tool(
        ctx,
        "query_observations",
        {
            "indicator_codes": [indicator.code],
            "region_codes": [region.code],
            "periods": [period],
        },
    )
    row = payload["rows"][0]
    citations = _citations(payload)
    value = row["value"]
    if value is None:
        return _notice_only(
            intent="lookup",
            status="no_data",
            code="NO_DATA",
            text=f"{period} 年{region.name}的{indicator.name}暂无数据（质量状态：{row['quality_status']}）。",
            tool_calls=ctx.calls,
            rows=ctx.rows,
        )
    citation = citations[0]
    display = _fmt(value, indicator.unit, indicator.precision)
    text = f"{period} 年{region.name}{indicator.name}为 {display}。"
    metric = MetricGridItem(
        label=indicator.name,
        value=value,
        unit=indicator.unit,
        year=period,
        quality_status=row["quality_status"],
        display=display,
        citation_id=citation.id,
    )
    blocks = [
        _block(
            "b1",
            "summary",
            "text",
            {"title": "结论", "paragraphs": [text]},
            text=text,
            title="结论",
        ),
        _block(
            "b2",
            "metric_grid",
            "metric_grid",
            {
                "title": f"{region.name}{indicator.name}",
                "columns": 1,
                "items": [metric.model_dump(mode="json")],
            },
            metrics=[metric],
            citations=[citation],
            title=f"{region.name}{indicator.name}",
        ),
        _demo_notice("b3"),
        _source_block("b4", citations, citation.data_as_of),
        _actions_block("b5", region, indicator),
    ]
    _attach_data_ref(
        blocks,
        indicator_codes=[indicator.code],
        region_codes=[region.code],
        periods=[str(period)],
        level=region.level,
    )
    draft = AnswerDraft(
        answer_markdown=text + "（演示数据，仅用于展示流程。）",
        intent="lookup",
        blocks=blocks,
        citations=citations,
        actions=_actions_in(blocks),
        follow_up_questions=FOLLOW_UPS["lookup"],
        status="done",
    )
    return AgentAnswer(draft=draft, tool_calls=ctx.calls, rows=ctx.rows, demo=True)


async def _rank(
    ctx: ToolContext,
    *,
    indicator: Indicator,
    period: int,
    level: str,
    limit: int,
) -> AgentAnswer:
    payload = await execute_tool(
        ctx,
        "rank_regions",
        {
            "indicator_code": indicator.code,
            "period": period,
            "level": level,
            "order": "desc",
            "limit": limit,
            "include_development_zones": False,
        },
    )
    rows = payload["rows"]
    citations = _citations(payload)
    citation = citations[0]
    ranking = [
        RankingEntry(
            rank=row["rank"],
            name=row["region_name"],
            value=row["value"],
            unit=row["unit"],
            region_code=row["region_code"],
            citation_id=row["citation_id"],
        )
        for row in rows
    ]
    columns = ["排名", "区域", f"{indicator.name}（{indicator.unit}）"]
    table_rows = [
        [row["rank"], row["region_name"], row["value"]]
        for row in rows
    ]
    categories = [row["region_name"] for row in rows]
    values = [row["value"] for row in rows]
    chart = ChartSpec(
        version="1.0",
        type="hbar",
        title=f"{period} 年{indicator.name}排名（前 {len(rows)}）",
        subtitle=None,
        unit=indicator.unit,
        categories=categories,
        series=[ChartSeries(name=indicator.name, values=values)],
        columns=None,
        rows=None,
        options=ChartOptions(show_values=True, sort="desc", max_items=len(rows)),
    )
    lead = "、".join(
        f"{row['rank']}. {row['region_name']} {_fmt(row['value'], indicator.unit, indicator.precision)}"
        for row in rows
    )
    text = f"{period} 年{indicator.name}排名前 {len(rows)}：{lead}。"
    blocks = [
        _block(
            "b1",
            "summary",
            "text",
            {"title": "排名结论", "paragraphs": [text]},
            text=text,
            title="排名结论",
        ),
        _block(
            "b2",
            "ranking",
            "ranking_bar",
            {
                "title": chart.title,
                "unit": indicator.unit,
                "period": str(period),
                "order": "desc",
                "items": [item.model_dump(mode="json") for item in ranking],
            },
            ranking=ranking,
            citations=[citation],
            title=chart.title,
        ),
        _block(
            "b3",
            "table",
            "data_table",
            {"title": f"{indicator.name}排名表", "columns": columns, "rows": table_rows, "unit": indicator.unit},
            columns=columns,
            rows=table_rows,
            citations=[citation],
            title=f"{indicator.name}排名表",
        ),
        _block(
            "b4",
            "chart",
            "bar_chart",
            {
                "chart_type": chart.type,
                "title": chart.title,
                "unit": chart.unit,
                "categories": categories,
                "series": [{"name": indicator.name, "values": values}],
                "max_items": len(rows),
            },
            chart=chart,
            citations=[citation],
            title=chart.title,
        ),
        _demo_notice("b5"),
        _source_block("b6", citations, citation.data_as_of),
        _actions_block("b7", None, indicator),
    ]
    _attach_data_ref(
        blocks,
        indicator_codes=[indicator.code],
        region_codes=[],
        periods=[str(period)],
        level=level,
    )
    draft = AnswerDraft(
        answer_markdown=text + "（演示数据，仅用于展示流程。）",
        intent="rank",
        blocks=blocks,
        citations=citations,
        actions=_actions_in(blocks),
        follow_up_questions=FOLLOW_UPS["rank"],
        status="done",
    )
    return AgentAnswer(draft=draft, tool_calls=ctx.calls, rows=ctx.rows, demo=True)


async def _compare(
    ctx: ToolContext,
    *,
    regions: list[Region],
    indicator: Indicator,
    period: int,
) -> AgentAnswer:
    payload = await execute_tool(
        ctx,
        "compare_regions",
        {
            "indicator_code": indicator.code,
            "region_codes": [region.code for region in regions[:6]],
            "period": period,
        },
    )
    rows = payload["rows"]
    citations = _citations(payload)
    if all(row["value"] is None for row in rows):
        return _notice_only(
            intent="compare",
            status="no_data",
            code="NO_DATA",
            text=f"{period} 年选定区域没有{indicator.name}的有效值，无法对比。",
            tool_calls=ctx.calls,
            rows=ctx.rows,
        )
    columns = ["区域", f"{indicator.name}（{indicator.unit}）", f"与{rows[0]['region_name']}的差"]
    table_rows = [
        [row["region_name"], row["value"], row["diff_from_first"]]
        for row in rows
    ]
    categories = [row["region_name"] for row in rows]
    values = [row["value"] for row in rows]
    chart = ChartSpec(
        version="1.0",
        type="bar",
        title=f"{period} 年{indicator.name}对比",
        subtitle=None,
        unit=indicator.unit,
        categories=categories,
        series=[ChartSeries(name=indicator.name, values=values)],
        columns=None,
        rows=None,
        options=ChartOptions(show_values=True, sort="none", max_items=len(rows)),
    )
    lead = "、".join(
        f"{row['region_name']} {_fmt(row['value'], indicator.unit, indicator.precision)}"
        for row in rows
    )
    first = rows[0]
    diff_text = ""
    if len(rows) > 1 and rows[1]["diff_from_first"] is not None:
        diff = rows[1]["diff_from_first"]
        direction = "多" if diff > 0 else ("少" if diff < 0 else "持平")
        if diff == 0:
            diff_text = f"；{rows[1]['region_name']}与{first['region_name']}持平"
        else:
            diff_text = (
                f"；{rows[1]['region_name']}比{first['region_name']}{direction} "
                f"{_fmt(abs(diff), indicator.unit, indicator.precision)}"
            )
    text = f"{period} 年{indicator.name}{lead}{diff_text}。"
    blocks = [
        _block(
            "b1",
            "summary",
            "text",
            {"title": "对比结论", "paragraphs": [text]},
            text=text,
            title="对比结论",
        ),
        _block(
            "b2",
            "table",
            "data_table",
            {"title": chart.title, "columns": columns, "rows": table_rows, "unit": indicator.unit},
            columns=columns,
            rows=table_rows,
            citations=citations,
            title=chart.title,
        ),
        _block(
            "b3",
            "chart",
            "bar_chart",
            {
                "chart_type": chart.type,
                "title": chart.title,
                "unit": chart.unit,
                "categories": categories,
                "series": [{"name": indicator.name, "values": values}],
                "max_items": len(rows),
            },
            chart=chart,
            citations=citations,
            title=chart.title,
        ),
        _demo_notice("b4"),
        _source_block("b5", citations, citations[0].data_as_of),
        _actions_block("b6", regions[0], indicator),
    ]
    _attach_data_ref(
        blocks,
        indicator_codes=[indicator.code],
        region_codes=[region.code for region in regions[:6]],
        periods=[str(period)],
        level="town",
    )
    draft = AnswerDraft(
        answer_markdown=text + "（演示数据，仅用于展示流程。）",
        intent="compare",
        blocks=blocks,
        citations=citations,
        actions=_actions_in(blocks),
        follow_up_questions=FOLLOW_UPS["compare"],
        status="done",
    )
    return AgentAnswer(draft=draft, tool_calls=ctx.calls, rows=ctx.rows, demo=True)


async def _profile(ctx: ToolContext, *, region: Region, period: int) -> AgentAnswer:
    payload = await execute_tool(
        ctx,
        "get_region_profile",
        {"region_code": region.code, "period": period},
    )
    citations = _citations(payload)
    metrics = [
        MetricGridItem(
            label=metric["label"],
            value=metric["value"],
            unit=metric["unit"],
            year=metric["period"],
            quality_status=metric["quality_status"],
            display=_fmt(metric["value"], metric["unit"]),
            citation_id=metric["citation_id"],
        )
        for metric in payload["metrics"]
    ]
    if not metrics and not payload.get("intro"):
        return _notice_only(
            intent="profile",
            status="no_data",
            code="NO_DATA",
            text=f"没有找到{region.name}的区域画像数据。",
            tool_calls=ctx.calls,
            rows=ctx.rows,
        )
    intro = payload.get("intro") or ""
    feature = payload.get("feature") or ""
    parts = [part for part in (intro, feature) if part]
    summary_text = f"{region.name}区域画像：" + " ".join(parts)
    body = summary_text if summary_text.strip() else f"{region.name}区域画像：暂无简介文本。"
    blocks = [
        _block(
            "b1",
            "summary",
            "text",
            {"title": f"{region.name}概况", "paragraphs": [body]},
            text=body,
            title=f"{region.name}概况",
        )
    ]
    if metrics and any(metric.value is not None for metric in metrics):
        blocks.append(
            _block(
                "b2",
                "metric_grid",
                "metric_grid",
                {
                    "title": f"{region.name}关键指标",
                    "columns": 2,
                    "items": [metric.model_dump(mode="json") for metric in metrics],
                },
                metrics=metrics,
                citations=citations,
                title=f"{region.name}关键指标",
            )
        )
    blocks.append(_demo_notice(f"b{len(blocks) + 1}"))
    blocks.append(_source_block(f"b{len(blocks) + 1}", citations, payload.get("data_as_of")))
    blocks.append(_actions_block(f"b{len(blocks) + 1}", region, None))
    _attach_data_ref(
        blocks,
        indicator_codes=[metric["indicator_code"] for metric in payload["metrics"]],
        region_codes=[region.code],
        periods=[str(period)],
        level=region.level,
    )
    draft = AnswerDraft(
        answer_markdown=body + "（演示数据，仅用于展示流程。）",
        intent="profile",
        blocks=blocks,
        citations=citations,
        actions=_actions_in(blocks),
        follow_up_questions=FOLLOW_UPS["profile"],
        status="done",
    )
    return AgentAnswer(draft=draft, tool_calls=ctx.calls, rows=ctx.rows, demo=True)


async def deterministic_answer(
    session: AsyncSession,
    *,
    question: str,
    context_period: str | None = None,
    context_region_id: int | None = None,
    context_indicator_id: int | None = None,
) -> AgentAnswer:
    regions = list(
        (
            await session.execute(
                select(Region).where(Region.enabled.is_(True)).order_by(Region.sort_order, Region.id)
            )
        )
        .scalars()
        .all()
    )
    indicators = {
        indicator.code: indicator
        for indicator in (
            await session.execute(select(Indicator).where(Indicator.enabled.is_(True)))
        )
        .scalars()
        .all()
    }
    aliases: dict[str, Region] = {}
    for alias, region in (
        await session.execute(
            select(RegionAlias.alias, Region).join(Region, RegionAlias.region_id == Region.id)
        )
    ).all():
        aliases[alias] = region

    matched_regions = _find_regions(question, regions, aliases)
    if context_region_id is not None:
        context_region = next((region for region in regions if region.id == context_region_id), None)
        if context_region is not None and all(r.id != context_region.id for r in matched_regions):
            matched_regions.insert(0, context_region)
    indicator = _find_indicator(question, indicators)
    if indicator is None and context_indicator_id is not None:
        indicator = next(
            (item for item in indicators.values() if item.id == context_indicator_id),
            None,
        )
    period = _detect_period(question, context_period)
    intent = _detect_intent(question, matched_regions, indicator)
    ctx = ToolContext(session=session)

    if intent == "refuse":
        text = (
            "该问题超出 Demo v0 的数据能力（不做预测、因果判断或个人隐私查询），"
            "请改问已发布的区域指标、排名、对比或区域画像。"
        )
        return _notice_only(intent="refuse", status="refused", code="REFUSED", text=text)

    try:
        if intent == "rank" and indicator is not None:
            return await _rank(
                ctx,
                indicator=indicator,
                period=period,
                level=_detect_level(question),
                limit=_detect_limit(question),
            )
        if intent == "compare" and indicator is not None and len(matched_regions) >= 2:
            return await _compare(
                ctx,
                regions=matched_regions,
                indicator=indicator,
                period=period,
            )
        if intent == "lookup" and indicator is not None and matched_regions:
            return await _lookup(
                ctx,
                region=matched_regions[0],
                indicator=indicator,
                period=period,
            )
        if intent == "profile" and matched_regions:
            return await _profile(ctx, region=matched_regions[0], period=period)
    except ToolError as exc:
        if exc.code == "INDICATOR_NOT_NUMERIC":
            text = "文本指标不支持排名或对比，请改用区域画像。"
        elif exc.code == "NO_DATA":
            text = "当前数据没有覆盖该区域、指标或年份，无法给出结论。"
        elif exc.code == "LIKE_NOT_SUPPORTED":
            text = "当前数据不支持该分析方式。"
        else:
            text = f"当前数据无法回答该问题（{exc.code}）。"
        return _notice_only(
            intent="clarify",
            status="no_data",
            code=exc.code,
            text=text,
            tool_calls=ctx.calls,
            rows=ctx.rows,
        )

    text = "未能从问题中识别出已发布的区域或指标，请补充镇街名称、指标名称与年份。"
    return _notice_only(intent="clarify", status="no_data", code="NO_DATA", text=text)
