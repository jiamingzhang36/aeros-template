#!/usr/bin/env python3
"""Validate substantive full-text literature-review execution.

This is deliberately separate from bookkeeping checks. Source-bound or metadata
cards may make the literature database consistent, but they cannot support
function-specific synthesis or paper positioning until full-text execution is
recorded.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REGISTRY = Path("discovery/literature/paper_registry.csv")
CARDS_DIR = Path("discovery/literature/extraction_cards")
SYNTHESIS_DIR = Path("discovery/literature/synthesis")
PAPER_ID_RE = re.compile(r"\bP\d{3,}\b")
PLACEHOLDERS = {"", "tbd", "todo", "unknown", "not stated", "n/a", "na", "none"}
FULL_TEXT_STATUSES = {"full_text_read", "extracted", "included"}
FULL_TEXT_BASIS = {"full_text", "extraction_card"}
ALLOWED_FUNCTIONS = {
    "idea-inspiring",
    "gap-verification",
    "method-identification",
    "data-measurement",
    "background-institutional",
    "theory-mechanism",
}
REQUIRED_FULLTEXT_HEADINGS = [
    "## Full Text Status",
    "## Extraction Depth",
    "## Literature Function",
    "## Content Summary",
    "## Direct Evidence Notes",
    "## What This Paper Can Support",
    "## What This Paper Cannot Support",
    "## Opened Source",
]
INDEX_ONLY_FILES = {
    Path("discovery/literature/synthesis/function_matrix.csv"),
    Path("discovery/literature/synthesis/closest_literature_matrix.csv"),
    Path("discovery/literature/synthesis/data_matrix.csv"),
    Path("discovery/literature/synthesis/findings_matrix.csv"),
    Path("discovery/literature/synthesis/method_matrix.csv"),
}


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    start += len(heading)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        next_heading = len(text)
    return text[start:next_heading].strip()


def _substantive(value: str) -> bool:
    lines = [line.strip(" |-:\t") for line in value.splitlines()]
    return any(line and line.lower() not in PLACEHOLDERS and "TBD" not in line for line in lines)


def _direct_evidence_substantive(text: str) -> bool:
    section = _section(text, "## Direct Evidence Notes")
    if not section or "TBD" in section:
        return False
    rows = [line for line in section.splitlines() if line.strip().startswith("|")]
    evidence_rows = [line for line in rows if "---" not in line and "Page / section" not in line]
    return any(_substantive(row) for row in evidence_rows)


def _read_registry() -> dict[str, dict[str, str]]:
    if not REGISTRY.exists():
        return {}
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        return {
            row.get("paper_id", "").strip(): row
            for row in csv.DictReader(handle)
            if row.get("paper_id", "").strip()
        }


def _requires_fulltext(row: dict[str, str]) -> bool:
    return any([
        _norm(row.get("used_in_synthesis")).lower() == "yes",
        _norm(row.get("status")) in FULL_TEXT_STATUSES,
        _norm(row.get("evidence_basis")) in FULL_TEXT_BASIS,
        "full" in _norm(row.get("reading_depth")).lower(),
    ])


def _fulltext_card_ok(paper_id: str, row: dict[str, str], failures: list[str]) -> bool:
    ok = True
    card = CARDS_DIR / f"{paper_id}.md"
    if _norm(row.get("full_text_available")).lower() != "yes":
        failures.append(f"{paper_id}: full-text execution requires full_text_available=yes")
        ok = False
    if not _norm(row.get("opened_source")):
        failures.append(f"{paper_id}: full-text execution requires opened_source")
        ok = False
    if not _norm(row.get("opened_date")):
        failures.append(f"{paper_id}: full-text execution requires opened_date")
        ok = False
    if _norm(row.get("evidence_basis")) not in FULL_TEXT_BASIS:
        failures.append(f"{paper_id}: full-text execution requires evidence_basis in {sorted(FULL_TEXT_BASIS)}")
        ok = False
    if _norm(row.get("extraction_card")).lower() != "yes":
        failures.append(f"{paper_id}: full-text execution requires extraction_card=yes")
        ok = False
    if not card.exists():
        failures.append(f"{paper_id}: missing full-text extraction card {card}")
        return False

    text = card.read_text(encoding="utf-8")
    for heading in REQUIRED_FULLTEXT_HEADINGS:
        if heading not in text:
            failures.append(f"{card}: missing full-text heading {heading}")
            ok = False
    status_section = _section(text, "## Full Text Status")
    if "full_text_obtained" not in status_section:
        failures.append(f"{card}: Full Text Status must include full_text_obtained")
        ok = False
    depth_section = _section(text, "## Extraction Depth")
    if "full_text_extraction" not in depth_section:
        failures.append(f"{card}: Extraction Depth must be full_text_extraction, not source_bound_stub")
        ok = False
    function = _norm(row.get("primary_function"))
    if function not in ALLOWED_FUNCTIONS:
        failures.append(f"{paper_id}: invalid primary_function {function!r}")
        ok = False
    for heading in [
        "## Content Summary",
        "## What This Paper Can Support",
        "## What This Paper Cannot Support",
        "## Opened Source",
    ]:
        if not _substantive(_section(text, heading)):
            failures.append(f"{card}: missing substantive content under {heading}")
            ok = False
    if not _direct_evidence_substantive(text):
        failures.append(f"{card}: Direct Evidence Notes must contain at least one non-placeholder page/section row")
        ok = False
    return ok


def _synthesis_files() -> list[Path]:
    if not SYNTHESIS_DIR.exists():
        return []
    out: list[Path] = []
    for path in sorted(SYNTHESIS_DIR.glob("*")):
        if path in INDEX_ONLY_FILES:
            continue
        if path.suffix.lower() in {".md", ".csv"}:
            out.append(path)
    return out


def main() -> int:
    registry = _read_registry()
    if not registry:
        print("PASS: literature full-text execution inactive (no registry rows yet)")
        return 0

    failures: list[str] = []
    fulltext_ok: dict[str, bool] = {}

    for paper_id, row in registry.items():
        if _requires_fulltext(row):
            fulltext_ok[paper_id] = _fulltext_card_ok(paper_id, row, failures)
        else:
            fulltext_ok[paper_id] = False

    cited: set[str] = set()
    for path in _synthesis_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for paper_id in sorted(set(PAPER_ID_RE.findall(text))):
            cited.add(paper_id)
            row = registry.get(paper_id)
            if row is None:
                failures.append(f"{path}: cites unknown paper_id {paper_id}")
                continue
            if not fulltext_ok.get(paper_id, False):
                failures.append(
                    f"{path}: cites {paper_id}, but it is not a verified full-text extraction; "
                    "source-bound/stub cards cannot support synthesis"
                )

    for paper_id, row in registry.items():
        if _norm(row.get("used_in_synthesis")).lower() == "yes" and paper_id not in cited:
            failures.append(f"{paper_id}: used_in_synthesis=yes but no synthesis file cites it")

    if failures:
        print("FAIL: literature full-text execution problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    count = sum(1 for ok in fulltext_ok.values() if ok)
    print(f"PASS: literature full-text execution valid ({count} verified full-text extraction(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
