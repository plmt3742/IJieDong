#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u20E3]")
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
SCAN_DIRS = ["docs", "apps", "services", "packages", "contracts", "deploy", "scripts"]


def _markdown_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return sorted(
        path
        for path in base.rglob("*.md")
        if not any(part in EXCLUDED_PARTS for part in path.parts)
    )


def _targets() -> list[Path]:
    targets = [ROOT / "README.md", ROOT / "AGENTS.md"]
    for name in SCAN_DIRS:
        targets.extend(_markdown_files(ROOT / name))
    return targets


def main() -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    targets = _targets()
    found: list[tuple[Path, int, str]] = []
    for path in targets:
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for char in EMOJI.findall(line):
                found.append((path, line_no, char))
    if not found:
        print(f"OK: checked {len(targets)} markdown files; no emoji found.")
        return 0
    print(f"Emoji found: {len(found)}")
    for path, line_no, char in found:
        print(f"  {path.relative_to(ROOT)}:{line_no}: U+{ord(char):04X} {char}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
