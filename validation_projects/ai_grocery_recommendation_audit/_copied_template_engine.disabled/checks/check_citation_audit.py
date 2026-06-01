#!/usr/bin/env python3
"""Check citation audit coverage for included or synthesized papers."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
AUDIT = Path("discovery/literature/citation_audit.md")
PAPER_ID_RE = re.compile(r"\bP\d{3,}\b")


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: missing {REGISTRY}")
        return 1
    if not AUDIT.exists():
        print(f"FAIL: missing {AUDIT}")
        return 1

    audit_text = AUDIT.read_text(encoding="utf-8")
    audited_ids = set(PAPER_ID_RE.findall(audit_text))

    failures: list[str] = []
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            paper_id = row.get("paper_id", "").strip()
            if not paper_id:
                continue
            needs_audit = (
                row.get("screening_decision", "").strip() in {"include", "maybe"}
                or row.get("used_in_synthesis", "").strip() == "yes"
                or row.get("status", "").strip() in {"full_text_obtained", "full_text_read", "extracted", "included"}
            )
            if needs_audit and paper_id not in audited_ids:
                failures.append(f"{paper_id}: missing from citation audit")

    if failures:
        print("FAIL: citation audit problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: citation audit covers papers requiring audit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
