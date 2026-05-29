#!/usr/bin/env python3
"""Validate the data inventory: vocabulary, uniqueness, and probe discipline.

Mirrors check_literature_registry.py for the data side. Blank seed rows (no
data_id) are skipped; vocabulary is only enforced on non-empty cells; and any
row that names an access_status must also record access_evidence OR a next_probe
(data-source existence is not data feasibility).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

INVENTORY = Path("discovery/data_inventory.csv")
CHECK_NAME = "check_data_inventory"

REQUIRED_COLUMNS = [
    "data_id", "dataset_name", "access_status", "unit",
    "access_evidence", "engineering_status", "skill_probe_status",
    "next_probe", "feasibility_status",
]
ACCESS_STATUS = {"located", "public", "restricted", "paid", "requested",
                 "granted", "unavailable", "unknown"}
ENGINEERING_STATUS = {"not_started", "located", "access_verified", "schema_inspected",
                      "variables_verified", "linkage_tested", "coverage_diagnosed",
                      "execution_ready"}
SKILL_PROBE_STATUS = {"not_started", "attempted", "blocked", "done"}
FEASIBILITY_STATUS = {"pursue", "revise", "pause", "drop", "tbd"}
PLACEHOLDERS = {"", "tbd", "todo", "unknown", "n/a", "na", "none"}

REMEDIATION_HINT = (
    "Fix data_inventory.csv: keep all required columns; use only allowed "
    "vocabulary; give every row a unique data_id; and any row with an "
    "access_status must record access_evidence OR a next_probe."
)


def _emit(as_json: bool, status: str, failures: list[str], rows_checked: int) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "rows_checked": rows_checked, "failures": failures,
                          "hint": REMEDIATION_HINT if status == "fail" else ""},
                         ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: data inventory is valid ({rows_checked} row(s) checked)")
    else:
        print("FAIL: data inventory problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the data inventory.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not INVENTORY.exists():
        return _emit(as_json, "fail", [f"missing {INVENTORY}"], 0)

    failures: list[str] = []
    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = [c for c in REQUIRED_COLUMNS if c not in columns]
        if missing:
            return _emit(as_json, "fail",
                         [f"missing required column: {c}" for c in missing], 0)
        rows = list(reader)

    seen: set[str] = set()
    checked = 0
    for row in rows:
        data_id = row.get("data_id", "").strip()
        if not data_id:
            continue  # blank seed row
        checked += 1
        if data_id in seen:
            failures.append(f"{data_id}: duplicate data_id")
        seen.add(data_id)

        def _vocab(col: str, allowed: set[str]) -> None:
            v = row.get(col, "").strip().lower()
            if v and v not in allowed:
                failures.append(f"{data_id}: invalid {col} {row.get(col, '').strip()!r}")

        _vocab("access_status", ACCESS_STATUS)
        _vocab("engineering_status", ENGINEERING_STATUS)
        _vocab("skill_probe_status", SKILL_PROBE_STATUS)
        _vocab("feasibility_status", FEASIBILITY_STATUS)

        if row.get("access_status", "").strip():
            evidence = row.get("access_evidence", "").strip().lower() not in PLACEHOLDERS
            probe = row.get("next_probe", "").strip().lower() not in PLACEHOLDERS
            if not (evidence or probe):
                failures.append(
                    f"{data_id}: a scouted source must record access_evidence OR a next_probe"
                )

    status = "fail" if failures else "pass"
    return _emit(as_json, status, failures, checked)


if __name__ == "__main__":
    sys.exit(main())
