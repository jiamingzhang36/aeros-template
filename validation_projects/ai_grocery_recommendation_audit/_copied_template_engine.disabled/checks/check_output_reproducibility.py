#!/usr/bin/env python3
"""Check that registered outputs have documented generating scripts."""

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
            output_path = row.get("path", "").strip()
            source = row.get("script_or_source", "").strip()
            if not output_path:
                continue
            checked += 1
            if not source:
                failures.append(f"{result_id}: output path is populated but script_or_source is empty")
            elif source.startswith(("code/", "checks/")) and not Path(source).exists():
                failures.append(f"{result_id}: generating script does not exist: {source}")

    if failures:
        print("FAIL: output reproducibility problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: registered outputs have generating sources ({checked} populated output(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
