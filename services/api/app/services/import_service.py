"""Minimal Demo v0 Excel import: parse, validate, and upsert data values."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.errors import AppError
from app.models import DataSource, DataValue, ImportJob, Indicator, Region, RegionAlias, User
from app.schemas.admin import ImportErrorsOut, ImportIssueOut, ImportJobOut
from app.services.audit_service import write_audit

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_DATA_ROWS = 5000
DEFAULT_PERIOD_YEAR = 2025
HEADER_COLUMNS = ("区域类型", "区域名称", "数据名称", "数据期", "单位", "数据值")
REGION_TYPE_LEVELS = {"揭东区": "district", "镇街": "town", "村居": "village"}
NUMERIC_VALUE_TYPES = {"integer", "decimal", "currency", "percentage", "ratio"}
QUALITY_MISSING = "missing"
QUALITY_VERIFIED = "verified"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CellRow:
    row_number: int
    values: list[Any]


@dataclass(frozen=True)
class ParsedWorkbook:
    headers: list[str]
    rows: list[CellRow]


@dataclass
class ValidatedRow:
    row_number: int
    region: Region
    indicator: Indicator
    value_number: Decimal | None
    value_text: str | None
    quality_status: str
    issues: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        return any(issue.get("severity") == "error" for issue in self.issues)

    @property
    def region_name(self) -> str:
        return self.region.name

    @property
    def indicator_name(self) -> str:
        return self.indicator.name


@dataclass(frozen=True)
class RegionMaps:
    by_level_name: dict[tuple[str, str], Region]
    aliases: dict[tuple[str, str], Region]
    villages_by_parent: dict[tuple[int, str], Region]
    village_names: dict[str, list[Region]]


def _header_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _is_blank_row(values: list[Any]) -> bool:
    return all(_cell_text(value) == "" for value in values)


def _parse_xlsx(content: bytes) -> ParsedWorkbook:
    from openpyxl import load_workbook

    workbook = load_workbook(filename=BytesIO(content), read_only=True, data_only=True)
    try:
        if not workbook.worksheets:
            raise AppError("IMPORT_VALIDATION_FAILED", "Workbook has no worksheets", 422)
        worksheet = workbook.worksheets[0]
        iterator = worksheet.iter_rows(values_only=True)
        try:
            raw_headers = next(iterator)
        except StopIteration as exc:
            raise AppError("IMPORT_VALIDATION_FAILED", "Workbook is empty", 422) from exc
        headers = [_header_text(value) for value in raw_headers]
        rows: list[CellRow] = []
        for row_number, values in enumerate(iterator, start=2):
            row_values = list(values)
            if _is_blank_row(row_values):
                continue
            rows.append(CellRow(row_number=row_number, values=row_values))
        return ParsedWorkbook(headers=headers, rows=rows)
    finally:
        workbook.close()


def _parse_xls(content: bytes) -> ParsedWorkbook:
    import xlrd

    workbook = xlrd.open_workbook(file_contents=content)
    if workbook.nsheets == 0:
        raise AppError("IMPORT_VALIDATION_FAILED", "Workbook has no worksheets", 422)
    sheet = workbook.sheet_by_index(0)
    if sheet.nrows == 0:
        raise AppError("IMPORT_VALIDATION_FAILED", "Workbook is empty", 422)
    headers = [_header_text(sheet.cell_value(0, column)) for column in range(sheet.ncols)]
    rows: list[CellRow] = []
    for row_index in range(1, sheet.nrows):
        values = [sheet.cell_value(row_index, column) for column in range(sheet.ncols)]
        if _is_blank_row(values):
            continue
        rows.append(CellRow(row_number=row_index + 1, values=values))
    return ParsedWorkbook(headers=headers, rows=rows)


def parse_workbook(filename: str | None, content: bytes) -> ParsedWorkbook:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".xlsx":
        return _parse_xlsx(content)
    if suffix == ".xls":
        return _parse_xls(content)
    raise AppError(
        "IMPORT_FILE_TYPE_INVALID",
        "Only .xls and .xlsx files are supported",
        status_code=422,
    )


def _issue(
    *,
    row_number: int | None,
    column: str | None,
    code: str,
    message: str,
    suggestion: str | None = None,
    severity: str = "error",
    region_name: str | None = None,
    indicator_name: str | None = None,
) -> dict[str, Any]:
    return {
        "row_number": row_number,
        "column": column,
        "code": code,
        "message": message,
        "suggestion": suggestion,
        "severity": severity,
        "region_name": region_name,
        "indicator_name": indicator_name,
    }


def _has_errors(issues: list[dict[str, Any]]) -> bool:
    return any(issue.get("severity") == "error" for issue in issues)


def _validate_headers(headers: list[str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for column in HEADER_COLUMNS:
        if column not in headers:
            issues.append(
                _issue(
                    row_number=1,
                    column=column,
                    code="HEADER_MISSING",
                    message=f"缺少必填列：{column}",
                    suggestion="请使用标准六列模板",
                )
            )
    for header in headers:
        if header and header not in HEADER_COLUMNS:
            issues.append(
                _issue(
                    row_number=1,
                    column=header,
                    code="COLUMN_UNKNOWN",
                    message=f"未知列：{header}",
                    suggestion="忽略该列或改用标准模板",
                    severity="warning",
                )
            )
    return issues


async def _load_region_maps(session: AsyncSession) -> RegionMaps:
    regions = (
        await session.execute(select(Region).where(Region.enabled.is_(True)))
    ).scalars().all()
    by_level_name: dict[tuple[str, str], Region] = {}
    villages_by_parent: dict[tuple[int, str], Region] = {}
    village_names: dict[str, list[Region]] = {}
    for region in regions:
        by_level_name.setdefault((region.level, region.name), region)
        if region.level == "village":
            if region.parent_id is not None:
                villages_by_parent.setdefault((region.parent_id, region.name), region)
            village_names.setdefault(region.name, []).append(region)

    alias_rows = (
        await session.execute(
            select(RegionAlias, Region).join(Region, RegionAlias.region_id == Region.id)
        )
    ).all()
    aliases: dict[tuple[str, str], Region] = {}
    for alias, region in alias_rows:
        aliases.setdefault((region.level, alias.alias), region)
        if region.level == "village":
            if region.parent_id is not None:
                villages_by_parent.setdefault((region.parent_id, alias.alias), region)
            village_names.setdefault(alias.alias, []).append(region)

    return RegionMaps(
        by_level_name=by_level_name,
        aliases=aliases,
        villages_by_parent=villages_by_parent,
        village_names=village_names,
    )


def _resolve_place(maps: RegionMaps, level: str, name: str) -> Region | None:
    return maps.by_level_name.get((level, name)) or maps.aliases.get((level, name))


def _resolve_region(
    maps: RegionMaps, level: str, name: str
) -> tuple[Region | None, str | None, str | None]:
    if level in {"district", "town"}:
        region = _resolve_place(maps, level, name)
        if region is None:
            return None, "REGION_NOT_FOUND", f"区域不存在：{name}"
        return region, None, None

    if "-" in name:
        parent_name, village_name = (part.strip() for part in name.split("-", 1))
        parent = _resolve_place(maps, "town", parent_name)
        if parent is None:
            return None, "REGION_PARENT_NOT_FOUND", f"村居父级不存在：{parent_name}"
        region = maps.villages_by_parent.get((parent.id, village_name))
        if region is None:
            return None, "REGION_NOT_FOUND", f"村居不存在：{name}"
        return region, None, None

    candidates = maps.village_names.get(name, [])
    if not candidates:
        return None, "REGION_NOT_FOUND", f"村居不存在：{name}"
    if len(candidates) > 1:
        return None, "REGION_AMBIGUOUS", f"村居名称不唯一：{name}"
    return candidates[0], None, None


def _parse_numeric(
    raw: str,
    indicator: Indicator,
) -> tuple[Decimal | None, str | None, str | None]:
    cleaned = raw.replace(",", "").replace("，", "").replace(" ", "")
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None, "NUMBER_FORMAT_INVALID", f"数据值不是有效数字：{raw}"
    if not number.is_finite():
        return None, "NUMBER_FORMAT_INVALID", f"数据值不是有限数字：{raw}"
    if indicator.value_type == "integer" and number != number.to_integral_value():
        return None, "VALUE_TYPE_INVALID", f"指标“{indicator.name}”要求整数，实际为{raw}"
    return number, None, None


def _validate_row(
    *,
    row: CellRow,
    column_index: dict[str, int],
    maps: RegionMaps,
    indicators_by_name: dict[str, Indicator],
    seen_keys: dict[tuple[int, int, int], int],
) -> tuple[ValidatedRow | None, list[dict[str, Any]]]:
    def cell(column: str) -> str:
        index = column_index.get(column)
        if index is None or index >= len(row.values):
            return ""
        return _cell_text(row.values[index])

    region_type = cell("区域类型")
    region_name = cell("区域名称")
    indicator_name = cell("数据名称")
    period_raw = cell("数据期")
    unit = cell("单位")
    value_raw = cell("数据值")

    issues: list[dict[str, Any]] = []
    for column, value in (
        ("区域类型", region_type),
        ("区域名称", region_name),
        ("数据名称", indicator_name),
        ("数据期", period_raw),
        ("单位", unit),
    ):
        if not value:
            issues.append(
                _issue(
                    row_number=row.row_number,
                    column=column,
                    code="REQUIRED_FIELD_MISSING",
                    message=f"{column}不能为空",
                    suggestion="补全模板必填列",
                    region_name=region_name or None,
                    indicator_name=indicator_name or None,
                )
            )

    level = REGION_TYPE_LEVELS.get(region_type)
    if region_type and level is None:
        issues.append(
            _issue(
                row_number=row.row_number,
                column="区域类型",
                code="REGION_LEVEL_MISMATCH",
                message=f"未知区域类型：{region_type}",
                suggestion="只能填写揭东区、镇街、村居",
                region_name=region_name or None,
            )
        )

    region: Region | None = None
    if level is not None and region_name:
        region, code, message = _resolve_region(maps, level, region_name)
        if code is not None:
            issues.append(
                _issue(
                    row_number=row.row_number,
                    column="区域名称",
                    code=code,
                    message=message or "区域无法解析",
                    suggestion="检查区域名称或别名表",
                    region_name=region_name,
                )
            )

    indicator = indicators_by_name.get(indicator_name) if indicator_name else None
    if indicator_name and indicator is None:
        issues.append(
            _issue(
                row_number=row.row_number,
                column="数据名称",
                code="INDICATOR_NOT_FOUND",
                message=f"指标不存在：{indicator_name}",
                suggestion="核对指标字典",
                region_name=region_name or None,
                indicator_name=indicator_name,
            )
        )

    if indicator is not None and region is not None:
        if region.level not in (indicator.applicable_levels or []):
            issues.append(
                _issue(
                    row_number=row.row_number,
                    column="区域名称",
                    code="INDICATOR_NOT_APPLICABLE",
                    message=f"指标“{indicator.name}”不适用于{region.name}",
                    suggestion="核对指标适用层级",
                    region_name=region.name,
                    indicator_name=indicator.name,
                )
            )
        categories = indicator.applicable_region_categories
        if categories and region.category not in categories:
            issues.append(
                _issue(
                    row_number=row.row_number,
                    column="区域名称",
                    code="INDICATOR_NOT_APPLICABLE",
                    message=f"指标“{indicator.name}”不适用于{region.name}的区域类别",
                    suggestion="核对指标适用范围",
                    region_name=region.name,
                    indicator_name=indicator.name,
                )
            )

    if indicator is not None and unit and unit != indicator.unit:
        issues.append(
            _issue(
                row_number=row.row_number,
                column="单位",
                code="UNIT_MISMATCH",
                message=f"指标“{indicator.name}”的单位应为“{indicator.unit}”，实际为“{unit}”",
                suggestion="检查模板列或指标选择",
                region_name=region_name or None,
                indicator_name=indicator.name,
            )
        )

    period_year: int | None = None
    if period_raw:
        try:
            period_year = int(Decimal(period_raw))
        except (InvalidOperation, ValueError):
            period_year = None
        if period_year != DEFAULT_PERIOD_YEAR:
            issues.append(
                _issue(
                    row_number=row.row_number,
                    column="数据期",
                    code="PERIOD_INVALID",
                    message=f"数据期只支持 {DEFAULT_PERIOD_YEAR}，实际为{period_raw}",
                    suggestion="改为 2025",
                    region_name=region_name or None,
                    indicator_name=indicator_name or None,
                )
            )

    value_number: Decimal | None = None
    value_text: str | None = None
    quality_status = QUALITY_VERIFIED
    if indicator is not None:
        if value_raw == "":
            quality_status = QUALITY_MISSING
            issues.append(
                _issue(
                    row_number=row.row_number,
                    column="数据值",
                    code="EMPTY_VALUE",
                    message="数据值为空，按缺失处理，不写 0",
                    suggestion="如确有数据请补充数值",
                    severity="warning",
                    region_name=region_name or None,
                    indicator_name=indicator.name,
                )
            )
        elif indicator.value_type in NUMERIC_VALUE_TYPES:
            value_number, code, message = _parse_numeric(value_raw, indicator)
            if code is not None:
                issues.append(
                    _issue(
                        row_number=row.row_number,
                        column="数据值",
                        code=code,
                        message=message or "数值格式错误",
                        suggestion="检查数值格式",
                        region_name=region_name or None,
                        indicator_name=indicator.name,
                    )
                )
        else:
            value_text = value_raw
            max_length = indicator.max_length or (
                5000 if indicator.value_type == "long_text" else 500
            )
            if len(value_text) > max_length:
                issues.append(
                    _issue(
                        row_number=row.row_number,
                        column="数据值",
                        code="TEXT_TOO_LONG",
                        message=f"文本长度 {len(value_text)} 超过上限 {max_length}",
                        suggestion="精简文本或拆分说明",
                        region_name=region_name or None,
                        indicator_name=indicator.name,
                    )
                )

    if region is not None and indicator is not None and period_year is not None:
        key = (region.id, indicator.id, period_year)
        if key in seen_keys:
            issues.append(
                _issue(
                    row_number=row.row_number,
                    column="数据值",
                    code="DUPLICATE_ROW",
                    message=f"与第 {seen_keys[key]} 行重复（区域+指标+数据期）",
                    suggestion="删除重复行",
                    region_name=region.name,
                    indicator_name=indicator.name,
                )
            )
        else:
            seen_keys[key] = row.row_number

    if region is None or indicator is None:
        return None, issues
    return (
        ValidatedRow(
            row_number=row.row_number,
            region=region,
            indicator=indicator,
            value_number=value_number,
            value_text=value_text,
            quality_status=quality_status,
            issues=issues,
        ),
        issues,
    )


async def _upsert_value(
    session: AsyncSession,
    *,
    job: ImportJob,
    row: ValidatedRow,
    current_user: User,
) -> None:
    existing = (
        await session.execute(
            select(DataValue).where(
                DataValue.region_id == row.region.id,
                DataValue.indicator_id == row.indicator.id,
                DataValue.period_year == DEFAULT_PERIOD_YEAR,
                DataValue.period_type == "year",
                DataValue.dimension_hash == "",
            )
        )
    ).scalars().first()

    if existing is None:
        existing = DataValue(
            region_id=row.region.id,
            indicator_id=row.indicator.id,
            period_year=DEFAULT_PERIOD_YEAR,
            period_type="year",
            dimension_hash="",
            version=1,
        )
        session.add(existing)
    else:
        existing.version = (existing.version or 1) + 1

    existing.value_number = row.value_number
    existing.value_text = row.value_text
    existing.quality_status = row.quality_status
    existing.status = "published"
    existing.dimensions = None
    if job.source_id is not None:
        existing.source_id = job.source_id
    existing.import_job_id = job.id
    existing.updated_by = current_user.id


def _job_out(job: ImportJob) -> ImportJobOut:
    return ImportJobOut(
        id=job.id,
        job_type=job.job_type,
        filename=job.filename,
        status=job.status,
        mode=job.mode,
        total_rows=job.total_rows,
        success_rows=job.success_rows,
        error_rows=job.error_rows,
        source_id=job.source_id,
        created_by=job.created_by,
        created_at=job.created_at,
        finished_at=job.finished_at,
        errors=[ImportIssueOut(**issue) for issue in (job.errors or [])],
    )


async def run_import(
    session: AsyncSession,
    *,
    filename: str | None,
    content: bytes,
    mode: str,
    source_id: int | None,
    current_user: User,
    request: Request,
) -> ImportJobOut:
    if len(content) > MAX_FILE_BYTES:
        raise AppError(
            "IMPORT_TOO_LARGE",
            "File exceeds the 10MB limit",
            status_code=413,
        )
    if source_id is not None and await session.get(DataSource, source_id) is None:
        raise AppError(
            "NOT_FOUND",
            "Data source not found",
            status_code=404,
            details={"source_id": source_id},
        )

    job = ImportJob(
        job_type="excel",
        filename=filename,
        status="running",
        mode=mode,
        total_rows=0,
        success_rows=0,
        error_rows=0,
        source_id=source_id,
        created_by=current_user.id,
    )
    session.add(job)
    await session.flush()

    try:
        parsed = await run_in_threadpool(parse_workbook, filename, content)
    except AppError as exc:
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc)
        job.error_rows = 1
        job.errors = [
            _issue(
                row_number=1,
                column=None,
                code=exc.code,
                message=exc.message,
                suggestion="检查上传文件",
            )
        ]
        await write_audit(
            session,
            action="import.create",
            resource_type="import_job",
            resource_id=job.id,
            detail={"filename": filename, "status": job.status, "mode": mode},
            request=request,
            user_id=current_user.id,
        )
        await session.commit()
        return _job_out(job)
    except Exception:
        logger.exception("Excel parse failed for import job %s", job.id)
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc)
        job.error_rows = 1
        job.errors = [
            _issue(
                row_number=1,
                column=None,
                code="IMPORT_FAILED",
                message="文件解析失败",
                suggestion="检查文件是否为有效的 Excel 工作簿",
            )
        ]
        await write_audit(
            session,
            action="import.create",
            resource_type="import_job",
            resource_id=job.id,
            detail={"filename": filename, "status": job.status, "mode": mode},
            request=request,
            user_id=current_user.id,
        )
        await session.commit()
        return _job_out(job)

    job.total_rows = len(parsed.rows)
    header_issues = _validate_headers(parsed.headers)
    if _has_errors(header_issues):
        job.status = "failed"
        job.error_rows = len([issue for issue in header_issues if issue["severity"] == "error"])
        job.errors = header_issues
        job.finished_at = datetime.now(timezone.utc)
        await write_audit(
            session,
            action="import.create",
            resource_type="import_job",
            resource_id=job.id,
            detail={"filename": filename, "status": job.status, "mode": mode},
            request=request,
            user_id=current_user.id,
        )
        await session.commit()
        return _job_out(job)

    if len(parsed.rows) > MAX_DATA_ROWS:
        job.status = "failed"
        job.error_rows = len(parsed.rows)
        job.errors = [
            _issue(
                row_number=MAX_DATA_ROWS + 2,
                column=None,
                code="IMPORT_ROW_LIMIT",
                message=f"数据行 {len(parsed.rows)} 超过上限 {MAX_DATA_ROWS}",
                suggestion="拆分文件后分批导入",
            )
        ]
        job.finished_at = datetime.now(timezone.utc)
        await write_audit(
            session,
            action="import.create",
            resource_type="import_job",
            resource_id=job.id,
            detail={"filename": filename, "status": job.status, "mode": mode},
            request=request,
            user_id=current_user.id,
        )
        await session.commit()
        return _job_out(job)

    column_index = {header: index for index, header in enumerate(parsed.headers) if header}
    maps = await _load_region_maps(session)
    indicators = (
        await session.execute(select(Indicator).where(Indicator.enabled.is_(True)))
    ).scalars().all()
    indicators_by_name = {indicator.name: indicator for indicator in indicators}

    seen_keys: dict[tuple[int, int, int], int] = {}
    issues: list[dict[str, Any]] = list(header_issues)
    validated: list[ValidatedRow] = []
    for row in parsed.rows:
        result, row_issues = _validate_row(
            row=row,
            column_index=column_index,
            maps=maps,
            indicators_by_name=indicators_by_name,
            seen_keys=seen_keys,
        )
        issues.extend(row_issues)
        if result is not None:
            validated.append(result)

    error_rows = len({issue["row_number"] for issue in issues if issue["severity"] == "error"})
    job.errors = issues
    job.error_rows = error_rows

    if mode == "atomic" and _has_errors(issues):
        job.status = "failed"
        job.success_rows = 0
    else:
        written = 0
        for result in validated:
            if result.has_error:
                continue
            await _upsert_value(session, job=job, row=result, current_user=current_user)
            written += 1
        job.success_rows = written
        job.status = "partial" if _has_errors(issues) else "success"

    job.finished_at = datetime.now(timezone.utc)
    await write_audit(
        session,
        action="import.create",
        resource_type="import_job",
        resource_id=job.id,
        detail={
            "filename": filename,
            "status": job.status,
            "mode": mode,
            "total_rows": job.total_rows,
            "success_rows": job.success_rows,
            "error_rows": job.error_rows,
        },
        request=request,
        user_id=current_user.id,
    )
    await session.commit()
    return _job_out(job)


async def list_import_jobs(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ImportJobOut], int]:
    total = int(
        (await session.execute(select(func.count()).select_from(ImportJob))).scalar_one()
    )
    rows = (
        await session.execute(
            select(ImportJob)
            .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return [_job_out(row) for row in rows], total


async def get_import_job(session: AsyncSession, job_id: int) -> ImportJobOut:
    job = await session.get(ImportJob, job_id)
    if job is None:
        raise AppError(
            "NOT_FOUND",
            "Import job not found",
            status_code=404,
            details={"id": job_id},
        )
    return _job_out(job)


async def get_import_errors(session: AsyncSession, job_id: int) -> ImportErrorsOut:
    job = await session.get(ImportJob, job_id)
    if job is None:
        raise AppError(
            "NOT_FOUND",
            "Import job not found",
            status_code=404,
            details={"id": job_id},
        )
    return ImportErrorsOut(
        job_id=job.id,
        errors=[ImportIssueOut(**issue) for issue in (job.errors or [])],
    )
