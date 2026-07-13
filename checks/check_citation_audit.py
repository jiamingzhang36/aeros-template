#!/usr/bin/env python3
"""Check citation audit coverage and faithfulness fields for evidence-use papers."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
AUDIT = Path("discovery/literature/citation_audit.md")
LITERATURE_ID_RE = re.compile(r"\b(?:P\d{3,}|CITE\d{3,})\b")
REQUIRED_COLUMNS = ["Citation exists", "Metadata faithful", "Claim support checked", "Evidence level"]
OK_VALUES = {"yes", "no", "partial", "abstract_only", "full_text", "not_checked", "n/a", "na"}


def _parse_table(text: str) -> tuple[list[str], dict[str, list[str]]]:
    headers: list[str] = []
    rows: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0] == "Paper ID":
            headers = cells
            continue
        if cells and LITERATURE_ID_RE.fullmatch(cells[0]):
            rows[cells[0]] = cells
    return headers, rows


def _row_faithfulness_failures(
    literature_id: str,
    cells: list[str],
    header_index: dict[str, int],
) -> list[str]:
    failures: list[str] = []
    for column in REQUIRED_COLUMNS:
        idx = header_index.get(column)
        if idx is None:
            continue
        if idx >= len(cells):
            failures.append(f"{literature_id}: {column} must be explicit before evidence use")
            continue
        value = cells[idx].strip().lower()
        if not value or value in {"tbd", "todo", "unknown"}:
            failures.append(f"{literature_id}: {column} must be explicit before evidence use")
        elif column != "Evidence level" and value not in OK_VALUES:
            failures.append(f"{literature_id}: {column} has non-standard value {value!r}")
    return failures


def _fixture_failures() -> list[str]:
    fixture = """
| Paper ID | Citation exists | Metadata faithful | Claim support checked | Evidence level |
|---|---|---|---|---|
| P001 | yes | yes | yes | full_text |
| CITE008 | yes | yes | yes | full_text |
| CITE009 | yes | yes | TBD | full_text |
| CITE010 | yes | yes |
"""
    headers, rows = _parse_table(fixture)
    failures: list[str] = []
    if set(rows) != {"P001", "CITE008", "CITE009", "CITE010"}:
        failures.append("fixture: citation audit must parse both P### and CITE### identifiers")
        return failures

    header_index = {name: idx for idx, name in enumerate(headers)}
    if _row_faithfulness_failures("P001", rows["P001"], header_index):
        failures.append("fixture: valid P### row failed faithfulness validation")
    if _row_faithfulness_failures("CITE008", rows["CITE008"], header_index):
        failures.append("fixture: valid CITE### row failed faithfulness validation")
    invalid_failures = _row_faithfulness_failures("CITE009", rows["CITE009"], header_index)
    if not any("Claim support checked must be explicit" in failure for failure in invalid_failures):
        failures.append("fixture: unresolved CITE### faithfulness field did not fail closed")
    truncated_failures = _row_faithfulness_failures("CITE010", rows["CITE010"], header_index)
    if not any("Evidence level must be explicit" in failure for failure in truncated_failures):
        failures.append("fixture: truncated CITE### row did not fail closed")
    return failures


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: missing {REGISTRY}")
        return 1
    if not AUDIT.exists():
        print(f"FAIL: missing {AUDIT}")
        return 1

    audit_text = AUDIT.read_text(encoding="utf-8")
    headers, audit_rows = _parse_table(audit_text)
    audited_ids = set(audit_rows) | set(LITERATURE_ID_RE.findall(audit_text))

    failures = _fixture_failures()
    for column in REQUIRED_COLUMNS:
        if column not in headers:
            failures.append(f"citation audit table missing faithfulness column: {column}")

    header_index = {name: idx for idx, name in enumerate(headers)}
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            paper_id = row.get("paper_id", "").strip()
            if not paper_id:
                continue
            status = row.get("status", "").strip()
            screening = row.get("screening_decision", "").strip()
            used = row.get("used_in_synthesis", "").strip() == "yes"
            extracted = row.get("extraction_card", "").strip() == "yes"
            needs_audit = (
                screening in {"include", "maybe"}
                or used
                or status in {"full_text_obtained", "full_text_read", "extracted", "included"}
            )
            if needs_audit and paper_id not in audited_ids:
                failures.append(f"{paper_id}: missing from citation audit")
                continue
            if (used or extracted or status in {"extracted", "included"}) and paper_id in audit_rows and headers:
                failures.extend(_row_faithfulness_failures(paper_id, audit_rows[paper_id], header_index))

    if failures:
        print("FAIL: citation audit problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: citation audit covers papers requiring audit and includes faithfulness fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
