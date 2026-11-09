"""Build the committed 227-node region fixture from the read-only data template.

Developer-only one-time script. It reads the ``数据模板`` sheet of
``Resource/Integration Materials/*.xls``, extracts the unique region type/name
pairs, normalises the ``玉窖镇`` village prefix to the standard ``玉滘镇``, and
writes structure-only JSON to ``scripts/fixtures/regions_2025.json``.

The runtime seed (``scripts/seed_demo.py``) only reads the committed JSON, so
the ``Resource/`` directory is not required to seed a demo database.

Usage (from ``services/api``):

    python scripts/build_region_fixture.py

Exit code is non-zero when the extracted counts no longer match
1 district + 15 towns + 211 villages = 227.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

import xlrd

SCRIPT_DIR = Path(__file__).resolve().parent
API_ROOT = SCRIPT_DIR.parent
REPO_ROOT = API_ROOT.parents[1]
RESOURCE_GLOB = str(REPO_ROOT / "Resource" / "Integration Materials" / "*.xls")
OUTPUT_PATH = SCRIPT_DIR / "fixtures" / "regions_2025.json"

SHEET_NAME = "数据模板"
DISTRICT_TYPE = "揭东区"
TOWN_TYPE = "镇街"
VILLAGE_TYPE = "村居"

DISTRICT_CODE = "JD"
EXPECTED_DISTRICT_COUNT = 1
EXPECTED_TOWN_COUNT = 15
EXPECTED_VILLAGE_COUNT = 211
EXPECTED_REGION_COUNT = 227

DEVELOPMENT_ZONE_NAMES = {
    "揭东经济开发区",
    "揭东中德金属生态城",
}

# 模板村居使用非标准前缀，统一为标准镇名后通过 region_aliases 兼容导入。
NAME_REPLACEMENTS = {
    "玉窖镇": "玉滘镇",
}


def _normalise_name(name: str) -> str:
    for source, target in NAME_REPLACEMENTS.items():
        name = name.replace(source, target)
    return name


def _locate_template() -> Path:
    matches = sorted(glob.glob(RESOURCE_GLOB))
    if not matches:
        raise SystemExit(f"no .xls template found under {RESOURCE_GLOB}")
    return Path(matches[0])


def _read_unique_regions(template_path: Path) -> tuple[str, list[str], list[str]]:
    """Return (district name, town names, village names) in first-seen order."""
    book = xlrd.open_workbook(str(template_path))
    if SHEET_NAME not in book.sheet_names():
        raise SystemExit(f"sheet {SHEET_NAME!r} not found in {template_path.name}")
    sheet = book.sheet_by_name(SHEET_NAME)

    header = [str(sheet.cell_value(0, column)).strip() for column in range(sheet.ncols)]
    if header[:2] != ["区域类型", "区域名称"]:
        raise SystemExit(f"unexpected header in {template_path.name}: {header[:2]}")

    district_name: str | None = None
    towns: "OrderedDict[str, None]" = OrderedDict()
    villages: "OrderedDict[str, None]" = OrderedDict()

    for row in range(1, sheet.nrows):
        region_type = str(sheet.cell_value(row, 0)).strip()
        region_name = str(sheet.cell_value(row, 1)).strip()
        if not region_type or not region_name:
            continue
        if region_type == DISTRICT_TYPE:
            district_name = _normalise_name(region_name)
        elif region_type == TOWN_TYPE:
            towns[_normalise_name(region_name)] = None
        elif region_type == VILLAGE_TYPE:
            villages[_normalise_name(region_name)] = None

    if district_name is None:
        raise SystemExit(f"no {DISTRICT_TYPE} row found in {template_path.name}")

    return district_name, list(towns), list(villages)


def build_regions(
    district_name: str,
    town_names: list[str],
    village_names: list[str],
) -> list[dict[str, Any]]:
    """Assemble the flat 227-node region list with stable codes and parents."""
    regions: list[dict[str, Any]] = [
        {
            "code": DISTRICT_CODE,
            "name": district_name,
            "level": "district",
            "category": "administrative",
            "parent_code": None,
            "sort_order": 0,
            "external_code": None,
            "enabled": True,
        }
    ]

    town_codes: dict[str, str] = {}
    for index, town_name in enumerate(town_names, start=1):
        code = f"JD-T-{index:02d}"
        town_codes[town_name] = code
        regions.append(
            {
                "code": code,
                "name": town_name,
                "level": "town",
                "category": (
                    "development_zone"
                    if town_name in DEVELOPMENT_ZONE_NAMES
                    else "administrative"
                ),
                "parent_code": DISTRICT_CODE,
                "sort_order": index,
                "external_code": None,
                "enabled": True,
            }
        )

    village_sort_order: dict[str, int] = {name: 0 for name in town_names}
    for index, village_name in enumerate(village_names, start=1):
        parent_name, separator, _ = village_name.partition("-")
        if not separator or parent_name not in town_codes:
            raise SystemExit(f"village {village_name!r} has no resolvable town parent")
        village_sort_order[parent_name] += 1
        regions.append(
            {
                "code": f"JD-V-{index:03d}",
                "name": village_name,
                "level": "village",
                "category": "administrative",
                "parent_code": town_codes[parent_name],
                "sort_order": village_sort_order[parent_name],
                "external_code": None,
                "enabled": True,
            }
        )

    return regions


def validate_regions(regions: list[dict[str, Any]]) -> dict[str, int]:
    """Validate the contract counts; raise ``SystemExit`` on mismatch."""
    district_count = sum(1 for region in regions if region["level"] == "district")
    town_count = sum(1 for region in regions if region["level"] == "town")
    village_count = sum(1 for region in regions if region["level"] == "village")
    administrative_town_count = sum(
        1
        for region in regions
        if region["level"] == "town" and region["category"] == "administrative"
    )
    development_zone_count = sum(
        1
        for region in regions
        if region["level"] == "town" and region["category"] == "development_zone"
    )

    failures: list[str] = []
    if len(regions) != EXPECTED_REGION_COUNT:
        failures.append(f"regions={len(regions)} expected={EXPECTED_REGION_COUNT}")
    if district_count != EXPECTED_DISTRICT_COUNT:
        failures.append(f"districts={district_count} expected={EXPECTED_DISTRICT_COUNT}")
    if town_count != EXPECTED_TOWN_COUNT:
        failures.append(f"towns={town_count} expected={EXPECTED_TOWN_COUNT}")
    if village_count != EXPECTED_VILLAGE_COUNT:
        failures.append(f"villages={village_count} expected={EXPECTED_VILLAGE_COUNT}")
    if administrative_town_count != 13:
        failures.append(f"administrative towns={administrative_town_count} expected=13")
    if development_zone_count != 2:
        failures.append(f"development zones={development_zone_count} expected=2")

    if failures:
        raise SystemExit("region fixture count mismatch: " + "; ".join(failures))

    return {
        "regions": len(regions),
        "districts": district_count,
        "towns": town_count,
        "villages": village_count,
        "administrative_towns": administrative_town_count,
        "development_zones": development_zone_count,
    }


def main() -> int:
    template_path = _locate_template()
    district_name, town_names, village_names = _read_unique_regions(template_path)
    regions = build_regions(district_name, town_names, village_names)
    counts = validate_regions(regions)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(regions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(
        json.dumps(
            {
                "template": template_path.name,
                "output": str(OUTPUT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                **counts,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
