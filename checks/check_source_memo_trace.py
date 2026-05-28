#!/usr/bin/env python3
"""Check source memo traceability scaffold and status values."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


TRACE = Path("discovery/source_memo_trace.csv")
REQUIRED_COLUMNS = [
    "trace_id",
    "source_memo",
    "item_type",
    "item_text",
    "priority",
    "target_file",
    "target_id",
    "status",
    "next_probe",
    "notes",
]
ALLOWED_TYPES = {"data_source", "mechanism", "design_step", "literature_lead", "institutional_detail", "claim_risk", "other", ""}
ALLOWED_PRIORITIES = {"high", "medium", "low", ""}
ALLOWED_STATUSES = {"pending", "mapped", "probed", "blocked", "deferred", "dropped", ""}
PLACEHOLDERS = {"", "tbd", "todo", "unknown", "n/a", "na"}


def missing_value(row: dict[str, str], column: str) -> bool:
    return row.get(column, "").strip().lower() in PLACEHOLDERS


def main() -> int:
    if not TRACE.exists():
        print(f"FAIL: missing {TRACE}")
        return 1

    failures: list[str] = []
    with TRACE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            print("FAIL: source memo trace missing required columns:")
            print("\n".join(missing))
            return 1
        rows = list(reader)

    for row in rows:
        trace_id = row.get("trace_id", "").strip() or "<missing trace_id>"
        item_type = row.get("item_type", "").strip()
        priority = row.get("priority", "").strip()
        status = row.get("status", "").strip()
        if item_type not in ALLOWED_TYPES:
            failures.append(f"{trace_id}: invalid item_type {item_type!r}")
        if priority not in ALLOWED_PRIORITIES:
            failures.append(f"{trace_id}: invalid priority {priority!r}")
        if status not in ALLOWED_STATUSES:
            failures.append(f"{trace_id}: invalid status {status!r}")
        if priority == "high" and status not in {"dropped", "deferred"}:
            for column in ["target_file", "target_id", "next_probe"]:
                if missing_value(row, column):
                    failures.append(f"{trace_id}: high-priority trace requires {column}")

    if failures:
        print("FAIL: source memo trace problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: source memo trace is valid ({len(rows)} row(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
