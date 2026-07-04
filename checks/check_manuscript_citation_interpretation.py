#!/usr/bin/env python3
"""Require manuscript citation sentences to have approved interpretation records."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aeros.runtime.submission_driver import build_citation_faithfulness_rows  # noqa: E402


def main() -> int:
    rows = build_citation_faithfulness_rows(ROOT)
    if not rows:
        print("PASS: no manuscript citations found; citation interpretation check inactive")
        return 0
    failures = [row for row in rows if row.interpretation_status != "faithful" or row.support_status != "faithful"]
    if failures:
        print("FAIL: manuscript citation interpretation check failed")
        for row in failures[:25]:
            print(
                f"- {row.sentence_id} {row.manuscript_path} cite={row.citation_key} "
                f"paper={row.mapped_paper_id or '<unmapped>'} "
                f"interpretation={row.interpretation_status} support={row.support_status}: "
                f"{row.required_action} ({row.notes})"
            )
        if len(failures) > 25:
            print(f"- ... {len(failures) - 25} more")
        return 1
    print(f"PASS: {len(rows)} manuscript citation rows have approved faithful interpretation records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
