#!/usr/bin/env python3
"""Check that synthesis uses only papers with extraction cards."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
SYNTHESIS_DIR = Path("discovery/literature/synthesis")
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
    for path in sorted(SYNTHESIS_DIR.glob("*")):
        if path.suffix not in {".md", ".csv"}:
            continue
        text = path.read_text(encoding="utf-8")
        for paper_id in sorted(set(PAPER_ID_RE.findall(text))):
            row = registry.get(paper_id)
            if row is None:
                failures.append(f"{path}: cites unknown paper_id {paper_id}")
                continue
            if row.get("extraction_card", "").strip() != "yes":
                failures.append(f"{path}: cites {paper_id} without extraction_card=yes")
            if row.get("status", "").strip() in {"abstract_only", "full_text_unavailable", "discovered"}:
                failures.append(f"{path}: cites {paper_id} with non-synthesis status {row.get('status')!r}")

    if failures:
        print("FAIL: synthesis grounding problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: synthesis files cite only extraction-card-backed paper IDs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
