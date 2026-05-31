#!/usr/bin/env python3
"""Validate agent run report index consistency."""

from __future__ import annotations

import csv
from pathlib import Path


INDEX_PATH = Path("agent_runs/INDEX.csv")
REPORT_DIR = Path("agent_runs")
RUN_FIELDS = {
    "run_file",
    "run_id",
    "task_id",
    "task_name",
    "agent",
    "date",
    "mode",
    "work_mode",
    "completion_status",
}


def _run_report_files() -> set[str]:
    return {
        str(path) for path in sorted(REPORT_DIR.glob("*.md"))
        if not path.name.startswith("TEMPLATE_") and path.name != "INDEX.csv"
    }


def _load_index_rows() -> list[dict[str, str]]:
    if not INDEX_PATH.exists():
        return []
    with INDEX_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    failures: list[str] = []
    report_files = _run_report_files()

    if not INDEX_PATH.exists():
        failures.append(f"missing index file: {INDEX_PATH}")
        if not report_files:
            print("PASS: no agent runs found and no index file is required")
            return 0
        print("FAIL: no agent run reports expected without index")
        print("\n".join(failures))
        return 1

    rows = _load_index_rows()
    if not rows:
        failures.append("agent_runs index exists but has no rows")
    index_by_file = {row.get("run_file", ""): row for row in rows if row.get("run_file")}

    for run_file in sorted(report_files):
        if run_file not in index_by_file:
            failures.append(f"missing index entry for {run_file}")

    for indexed_file in sorted(index_by_file):
        if indexed_file not in report_files:
            failures.append(f"index entry references non-report file: {indexed_file}")

    for run_file, row in index_by_file.items():
        for field in sorted(RUN_FIELDS):
            if field not in row:
                failures.append(f"index row for {run_file} missing column '{field}'")

    if failures:
        print("FAIL: agent_runs index consistency problems:")
        print("\n".join(failures))
        return 1

    print(f"PASS: agent_runs index is consistent ({len(index_by_file)} report(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
