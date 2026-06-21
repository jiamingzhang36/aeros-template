#!/usr/bin/env python3
"""Check citation audit coverage and faithfulness fields for evidence-use papers."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
AUDIT = Path("discovery/literature/citation_audit.md")
PAPER_ID_RE = re.compile(r"\bP\d{3,}\b")
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
        if cells and PAPER_ID_RE.fullmatch(cells[0]):
            rows[cells[0]] = cells
    return headers, rows


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: missing {REGISTRY}")
        return 1
    if not AUDIT.exists():
        print(f"FAIL: missing {AUDIT}")
        return 1

    audit_text = AUDIT.read_text(encoding="utf-8")
    headers, audit_rows = _parse_table(audit_text)
    audited_ids = set(audit_rows) | set(PAPER_ID_RE.findall(audit_text))

    failures: list[str] = []
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
                cells = audit_rows[paper_id]
                for column in REQUIRED_COLUMNS:
                    idx = header_index.get(column)
                    if idx is None or idx >= len(cells):
                        continue
                    value = cells[idx].strip().lower()
                    if not value or value in {"tbd", "todo", "unknown"}:
                        failures.append(f"{paper_id}: {column} must be explicit before evidence use")
                    elif column != "Evidence level" and value not in OK_VALUES:
                        failures.append(f"{paper_id}: {column} has non-standard value {value!r}")

    if failures:
        print("FAIL: citation audit problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: citation audit covers papers requiring audit and includes faithfulness fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
