#!/usr/bin/env python3
"""Check literature registry status, columns, and extraction-card consistency."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
CARDS_DIR = Path("discovery/literature/extraction_cards")
REQUIRED_COLUMNS = [
    "paper_id",
    "title",
    "authors",
    "year",
    "source",
    "doi",
    "url",
    "status",
    "full_text_available",
    "screening_decision",
    "extraction_card",
    "used_in_synthesis",
    "notes",
]
ALLOWED_STATUSES = {
    "discovered",
    "title_abstract_screened",
    "abstract_only",
    "full_text_obtained",
    "full_text_read",
    "extracted",
    "included",
    "excluded",
    "full_text_unavailable",
}
YES_NO = {"yes", "no"}


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: missing {REGISTRY}")
        return 1

    failures: list[str] = []
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            print("FAIL: literature registry missing required columns:")
            print("\n".join(missing))
            return 1

        rows = list(reader)

    seen_ids: set[str] = set()
    for row in rows:
        paper_id = row.get("paper_id", "").strip()
        if not paper_id:
            continue
        if paper_id in seen_ids:
            failures.append(f"{paper_id}: duplicate paper_id")
        seen_ids.add(paper_id)

        status = row.get("status", "").strip()
        if status and status not in ALLOWED_STATUSES:
            failures.append(f"{paper_id}: invalid status {status!r}")

        for column in ["full_text_available", "extraction_card", "used_in_synthesis"]:
            value = row.get(column, "").strip()
            if value and value not in YES_NO:
                failures.append(f"{paper_id}: {column} must be yes/no, got {value!r}")

        has_card = row.get("extraction_card", "").strip() == "yes"
        used = row.get("used_in_synthesis", "").strip() == "yes"
        card_path = CARDS_DIR / f"{paper_id}.md"
        if (status in {"extracted", "included"} or has_card or used) and not card_path.exists():
            failures.append(f"{paper_id}: extraction card expected at {card_path}")
        if used and status in {"abstract_only", "discovered", "title_abstract_screened", "full_text_unavailable"}:
            failures.append(f"{paper_id}: cannot use status {status!r} in synthesis")

    if failures:
        print("FAIL: literature registry problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: literature registry is valid ({len(rows)} row(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
