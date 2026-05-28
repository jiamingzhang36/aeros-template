#!/usr/bin/env python3
"""Check that non-draft claims have evidence or result links."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


CLAIM_REGISTRY = Path("3_evidence/claim_registry.md")
EVIDENCE_LEDGER = Path("3_evidence/evidence_ledger.csv")
RESULT_INDEX = Path("3_evidence/result_index.csv")
FINAL_STATUSES = {"supported", "ambiguous", "unsupported"}


def read_ids(path: Path, column: str) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {row[column].strip() for row in reader if row.get(column, "").strip()}


def parse_claim_rows(markdown: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in markdown.splitlines():
        if not line.startswith("| C"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        if cells[0].lower() == "claim id":
            continue
        rows.append(
            {
                "claim_id": cells[0],
                "claim": cells[1],
                "type": cells[2],
                "status": cells[3].lower(),
                "evidence_ids": cells[4],
                "result_ids": cells[5],
            }
        )
    return rows


def split_ids(value: str) -> set[str]:
    return {item.strip() for item in re.split(r"[;, ]+", value) if item.strip() and item.strip() != "TBD"}


def main() -> int:
    if not CLAIM_REGISTRY.exists():
        print(f"FAIL: missing {CLAIM_REGISTRY}")
        return 1

    evidence_ids = read_ids(EVIDENCE_LEDGER, "evidence_id")
    result_ids = read_ids(RESULT_INDEX, "result_id")
    rows = parse_claim_rows(CLAIM_REGISTRY.read_text(encoding="utf-8"))

    failures: list[str] = []
    for row in rows:
        linked_evidence = split_ids(row["evidence_ids"])
        linked_results = split_ids(row["result_ids"])
        if row["status"] in FINAL_STATUSES and not (linked_evidence or linked_results):
            failures.append(f"{row['claim_id']}: {row['status']} claim has no evidence or result link")
        missing_evidence = linked_evidence - evidence_ids
        missing_results = linked_results - result_ids
        if missing_evidence:
            failures.append(f"{row['claim_id']}: missing evidence IDs {sorted(missing_evidence)}")
        if missing_results:
            failures.append(f"{row['claim_id']}: missing result IDs {sorted(missing_results)}")

    if failures:
        print("FAIL: claim registry problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: claim registry links are valid for {len(rows)} claim row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
