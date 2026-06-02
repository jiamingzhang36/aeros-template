#!/usr/bin/env python3
"""Lightweight placeholder for paper-output number consistency checks.

This script intentionally starts conservative. It verifies that registered
result paths exist when they are populated. Project-specific numeric extraction
rules can be added later once the paper and output formats are known.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


RESULT_INDEX = Path("evidence/result_index.csv")


def main() -> int:
    if not RESULT_INDEX.exists():
        print(f"FAIL: missing {RESULT_INDEX}")
        return 1

    failures: list[str] = []
    checked = 0
    with RESULT_INDEX.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            result_id = row.get("result_id", "").strip()
            path_value = row.get("path", "").strip()
            if not path_value:
                continue
            checked += 1
            if not Path(path_value).exists():
                failures.append(f"{result_id}: registered output path does not exist: {path_value}")

    if failures:
        print("FAIL: result index path problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: registered result paths exist ({checked} populated path(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
