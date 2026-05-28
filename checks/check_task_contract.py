#!/usr/bin/env python3
"""Check that task files include the core harness contract sections."""

from __future__ import annotations

import sys
from pathlib import Path


TASK_DIR = Path("tasks")
REQUIRED_HEADINGS = [
    "## Objective",
    "## Harness Mode",
    "## Files to Inspect",
    "## Files Allowed to Modify",
    "## Files Forbidden to Modify",
    "## Constraints",
    "## Expected Output",
    "## Checks to Run",
    "## Done When",
]


def main() -> int:
    failures: list[str] = []
    for path in sorted(TASK_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
        if missing:
            failures.append(f"{path}: missing {', '.join(missing)}")

    if failures:
        print("FAIL: task contract problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: task contracts include required harness sections ({len(list(TASK_DIR.glob('*.md')))} file(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
