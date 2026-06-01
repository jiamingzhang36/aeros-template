#!/usr/bin/env python3
"""Check an expanded AI-output collection design when present."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


PLAN = Path("execution/collection/expanded_collection_plan.md")
GRID = Path("outputs/audit_runs/expanded_prompt_grid.csv")

REQUIRED_GRID_COLUMNS = {
    "prompt_id",
    "persona",
    "prompt_variant",
    "model",
    "run_index",
    "planned_timestamp_policy",
}


def _nonempty_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def main() -> int:
    if not PLAN.exists() and not GRID.exists():
        print("SKIP: expanded collection design artifacts not present yet")
        return 0

    failures: list[str] = []
    if not PLAN.exists():
        failures.append(f"missing {PLAN}")
    elif _nonempty_lines(PLAN) < 20:
        failures.append(f"{PLAN}: plan is too short")

    if not GRID.exists():
        failures.append(f"missing {GRID}")
    else:
        with GRID.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_GRID_COLUMNS - set(reader.fieldnames or [])
            rows = list(reader)
        if missing:
            failures.append(f"{GRID}: missing columns {', '.join(sorted(missing))}")
        if len(rows) < 12:
            failures.append(f"{GRID}: expected at least 12 planned prompt-run rows")
        prompt_ids = [row.get("prompt_id", "").strip() for row in rows]
        if len(prompt_ids) != len(set(prompt_ids)):
            failures.append(f"{GRID}: prompt_id values must be unique")

    if failures:
        print("FAIL: expanded collection design problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: expanded collection design is present and auditable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
