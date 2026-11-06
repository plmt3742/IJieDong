#!/usr/bin/env python3
"""Check relative Markdown links in docs/ and root README/AGENTS.

Usage: python scripts/check-links.py
Exit code 0 = all links resolve; 1 = broken links found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    *sorted((ROOT / "docs").rglob("*.md")),
]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "tel:")


def is_external(target: str) -> bool:
    return target.startswith(SKIP_PREFIXES)


def check_file(path: Path) -> list[tuple[Path, int, str, str]]:
    broken: list[tuple[Path, int, str, str]] = []
    text = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in LINK_RE.finditer(line):
            raw = match.group(1).strip()
            # Drop optional title: [x](path "title")
            target = raw.split(" ", 1)[0].strip()
            if not target or is_external(target):
                continue
            # Drop anchor and query
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            # Normalize Windows separators / URL-encoded spaces
            target = target.replace("\\", "/").replace("%20", " ")
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                broken.append((path, line_no, raw, "escapes repository root"))
                continue
            if not resolved.exists():
                broken.append((path, line_no, raw, "not found"))
    return broken


def main() -> int:
    all_broken: list[tuple[Path, int, str, str]] = []
    for path in TARGETS:
        if not path.exists():
            all_broken.append((path, 0, str(path), "target file missing"))
            continue
        all_broken.extend(check_file(path))

    if all_broken:
        print(f"Broken links: {len(all_broken)}")
        for path, line_no, raw, reason in all_broken:
            rel = path.relative_to(ROOT)
            print(f"  {rel}:{line_no}: {raw} -> {reason}")
        return 1

    print(f"OK: checked {len(TARGETS)} markdown files; all relative links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
