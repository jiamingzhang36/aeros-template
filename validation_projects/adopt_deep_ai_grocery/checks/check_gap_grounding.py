#!/usr/bin/env python3
"""Check that gap memos cite only extracted gap-verification papers."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
GAP_FILES = [
    Path("discovery/gap_memo.md"),
    Path("discovery/literature/synthesis/gap_memo.md"),
]
PAPER_ID_RE = re.compile(r"\bP\d{3,}\b")


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: missing {REGISTRY}")
        return 1

    registry: dict[str, dict[str, str]] = {}
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            paper_id = row.get("paper_id", "").strip()
            if paper_id:
                registry[paper_id] = row

    failures: list[str] = []
    for path in GAP_FILES:
        if not path.exists():
            continue
        for paper_id in sorted(set(PAPER_ID_RE.findall(path.read_text(encoding="utf-8")))):
            row = registry.get(paper_id)
            if row is None:
                failures.append(f"{path}: cites unknown paper_id {paper_id}")
                continue
            if row.get("primary_function", "").strip() != "gap-verification":
                failures.append(f"{path}: {paper_id} is not primary_function=gap-verification")
            if row.get("extraction_card", "").strip() != "yes":
                failures.append(f"{path}: {paper_id} lacks extraction_card=yes")
            if row.get("evidence_basis", "").strip() != "extraction_card":
                failures.append(f"{path}: {paper_id} lacks evidence_basis=extraction_card")

    if failures:
        print("FAIL: gap grounding problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: gap memos are grounded in extracted gap-verification papers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
