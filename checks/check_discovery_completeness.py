#!/usr/bin/env python3
"""Check that the discovery harness scaffold is present."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


REQUIRED_FILES = [
    Path("discovery/idea_memo.md"),
    Path("discovery/literature_map.md"),
    Path("discovery/paper_registry.csv"),
    Path("discovery/data_inventory.csv"),
    Path("discovery/search_log.md"),
    Path("discovery/feasibility_matrix.md"),
    Path("discovery/feasibility_memo.md"),
    Path("discovery/design_sketch.md"),
    Path("discovery/PROMOTE_TO_HARNESS.md"),
]

REQUIRED_HEADINGS = {
    Path("discovery/idea_memo.md"): ["## Working Title", "## One-Sentence Research Question"],
    Path("discovery/literature_map.md"): ["## Research Strands", "## Gap Status"],
    Path("discovery/search_log.md"): ["## Search Rules"],
    Path("discovery/feasibility_matrix.md"): ["## Overall Decision", "## Minimum Viable Version"],
    Path("discovery/feasibility_memo.md"): ["## Decision"],
    Path("discovery/design_sketch.md"): ["## Project Type", "## Candidate Data"],
    Path("discovery/PROMOTE_TO_HARNESS.md"): ["## Promotion Criteria", "## Decision"],
}

REQUIRED_CSV_COLUMNS = {
    Path("discovery/paper_registry.csv"): ["paper_id", "title", "function", "notes"],
    Path("discovery/data_inventory.csv"): ["data_id", "dataset_name", "access_status", "unit", "feasibility_status"],
}


def csv_columns(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def main() -> int:
    failures: list[str] = []

    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing {path}")

    for path, headings in REQUIRED_HEADINGS.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [heading for heading in headings if heading not in text]
        if missing:
            failures.append(f"{path}: missing headings {missing}")

    for path, columns in REQUIRED_CSV_COLUMNS.items():
        if not path.exists():
            continue
        existing = set(csv_columns(path))
        missing = [column for column in columns if column not in existing]
        if missing:
            failures.append(f"{path}: missing columns {missing}")

    if failures:
        print("FAIL: discovery harness problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: discovery harness scaffold is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
