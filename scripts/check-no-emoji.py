#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u20E3]")
TARGETS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    *sorted((ROOT / "docs").rglob("*.md")),
    *sorted((ROOT / "apps").rglob("*.md")),
    *sorted((ROOT / "services").rglob("*.md")),
    *sorted((ROOT / "packages").rglob("*.md")),
    *sorted((ROOT / "contracts").rglob("*.md")),
    *sorted((ROOT / "deploy").rglob("*.md")),
    *sorted((ROOT / "scripts").rglob("*.md")),
]


def main() -> int:
    found: list[tuple[Path, int, str]] = []
    for path in TARGETS:
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for char in EMOJI.findall(line):
                found.append((path, line_no, char))
    if not found:
        print(f"OK: checked {len(TARGETS)} markdown files; no emoji found.")
        return 0
    print(f"Emoji found: {len(found)}")
    for path, line_no, char in found:
        print(f"  {path.relative_to(ROOT)}:{line_no}: U+{ord(char):04X} {char}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
