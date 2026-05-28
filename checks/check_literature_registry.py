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
    "pdf_url",
    "primary_function",
    "secondary_functions",
    "reading_depth",
    "status",
    "full_text_available",
    "opened_source",
    "opened_date",
    "evidence_basis",
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
ALLOWED_FUNCTIONS = {
    "idea-inspiring",
    "gap-verification",
    "method-identification",
    "data-measurement",
    "background-institutional",
    "theory-mechanism",
}
ALLOWED_READING_DEPTHS = {"skim", "abstract", "targeted", "full_text", "not_read"}
ALLOWED_EVIDENCE = {"none", "title", "abstract", "full_text", "extraction_card"}
ALLOWED_SCREENING_DECISIONS = {"include", "maybe", "exclude", "defer"}
SOURCE_LOCATOR_COLUMNS = ["doi", "url", "pdf_url"]
SOURCE_LOCATOR_PLACEHOLDERS = {"", "tbd", "todo", "unknown", "n/a", "na"}
SOURCE_LOCATOR_STATUSES = {"full_text_obtained", "full_text_read", "extracted", "included"}


def has_source_locator(row: dict[str, str]) -> bool:
    return any(
        row.get(column, "").strip().lower() not in SOURCE_LOCATOR_PLACEHOLDERS
        for column in SOURCE_LOCATOR_COLUMNS
    )


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

        primary_function = row.get("primary_function", "").strip()
        if primary_function not in ALLOWED_FUNCTIONS:
            failures.append(f"{paper_id}: invalid primary_function {primary_function!r}")

        for function in [item.strip() for item in row.get("secondary_functions", "").split(";") if item.strip()]:
            if function not in ALLOWED_FUNCTIONS:
                failures.append(f"{paper_id}: invalid secondary function {function!r}")

        reading_depth = row.get("reading_depth", "").strip()
        if reading_depth and reading_depth not in ALLOWED_READING_DEPTHS:
            failures.append(f"{paper_id}: invalid reading_depth {reading_depth!r}")

        evidence_basis = row.get("evidence_basis", "").strip()
        if evidence_basis and evidence_basis not in ALLOWED_EVIDENCE:
            failures.append(f"{paper_id}: invalid evidence_basis {evidence_basis!r}")

        screening_decision = row.get("screening_decision", "").strip()
        if screening_decision and screening_decision not in ALLOWED_SCREENING_DECISIONS:
            failures.append(f"{paper_id}: invalid screening_decision {screening_decision!r}")

        for column in ["full_text_available", "extraction_card", "used_in_synthesis"]:
            value = row.get(column, "").strip()
            if value and value not in YES_NO:
                failures.append(f"{paper_id}: {column} must be yes/no, got {value!r}")

        has_card = row.get("extraction_card", "").strip() == "yes"
        used = row.get("used_in_synthesis", "").strip() == "yes"
        card_path = CARDS_DIR / f"{paper_id}.md"
        if (status in SOURCE_LOCATOR_STATUSES or has_card or used) and not has_source_locator(row):
            failures.append(f"{paper_id}: evidence-eligible papers require a DOI, URL, or PDF/source locator")
        if status in {"extracted", "included"} and not has_card:
            failures.append(f"{paper_id}: status {status!r} requires extraction_card=yes")
        if status in {"extracted", "included"} and row.get("full_text_available", "").strip() != "yes":
            failures.append(f"{paper_id}: status {status!r} requires full_text_available=yes")
        if status == "included" and screening_decision != "include":
            failures.append(f"{paper_id}: status 'included' requires screening_decision=include")
        if status == "excluded" and screening_decision != "exclude":
            failures.append(f"{paper_id}: status 'excluded' requires screening_decision=exclude")
        if (status in {"extracted", "included"} or has_card or used) and not card_path.exists():
            failures.append(f"{paper_id}: extraction card expected at {card_path}")
        if used and status in {"abstract_only", "discovered", "title_abstract_screened", "full_text_unavailable"}:
            failures.append(f"{paper_id}: cannot use status {status!r} in synthesis")
        if primary_function == "gap-verification" and status in {"included", "extracted"} and not has_card:
            failures.append(f"{paper_id}: gap-verification included/extracted papers require extraction_card=yes")
        if has_card and evidence_basis != "extraction_card":
            failures.append(f"{paper_id}: extraction_card=yes requires evidence_basis=extraction_card")

    if failures:
        print("FAIL: literature registry problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: literature registry is valid ({len(rows)} row(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
