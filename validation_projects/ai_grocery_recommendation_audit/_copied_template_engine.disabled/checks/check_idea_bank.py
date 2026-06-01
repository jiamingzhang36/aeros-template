#!/usr/bin/env python3
"""Check exploratory idea bank statuses and required fields."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


IDEA_BANK = Path("discovery/idea_bank.csv")
REQUIRED_COLUMNS = [
    "idea_id",
    "idea",
    "source",
    "intake_ref",
    "intake_priority",
    "status",
    "evidence_needed",
    "next_action",
    "human_decision",
    "notes",
]
ALLOWED_STATUSES = {
    "speculative",
    "under_verification",
    "supported",
    "revised",
    "parked",
    "dropped",
    "promoted_to_design",
}
ALLOWED_HUMAN_DECISIONS = {
    "pending",
    "promote",
    "revise",
    "park",
    "drop",
    "defer",
}
ALLOWED_INTAKE_PRIORITIES = {"high", "medium", "low", ""}


def main() -> int:
    if not IDEA_BANK.exists():
        print(f"FAIL: missing {IDEA_BANK}")
        return 1

    failures: list[str] = []
    with IDEA_BANK.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            print("FAIL: idea bank missing required columns:")
            print("\n".join(missing))
            return 1
        rows = list(reader)

    seen_ids: set[str] = set()
    for row in rows:
        idea_id = row.get("idea_id", "").strip()
        if not idea_id:
            continue
        if idea_id in seen_ids:
            failures.append(f"{idea_id}: duplicate idea_id")
        seen_ids.add(idea_id)

        status = row.get("status", "").strip()
        if status not in ALLOWED_STATUSES:
            failures.append(f"{idea_id}: invalid status {status!r}")

        intake_priority = row.get("intake_priority", "").strip()
        if intake_priority not in ALLOWED_INTAKE_PRIORITIES:
            failures.append(f"{idea_id}: invalid intake_priority {intake_priority!r}")

        human_decision = row.get("human_decision", "").strip()
        if human_decision not in ALLOWED_HUMAN_DECISIONS:
            failures.append(f"{idea_id}: invalid human_decision {human_decision!r}")

        if status == "promoted_to_design" and human_decision != "promote":
            failures.append(f"{idea_id}: promoted_to_design requires human_decision=promote")
        if status in {"supported", "promoted_to_design"} and not row.get("evidence_needed", "").strip():
            failures.append(f"{idea_id}: supported/promoted ideas must record evidence basis or remaining evidence needed")

    if failures:
        print("FAIL: idea bank problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: idea bank statuses are valid ({len(rows)} row(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
