#!/usr/bin/env python3
"""Check final-manuscript citation faithfulness against registry/cards.

This checks traceability, not scientific truth: every cited manuscript sentence
must map to a paper_registry row and a non-placeholder extraction-card support
chain before submission-style readiness can be claimed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.submission_driver import build_citation_faithfulness  # noqa: E402


def main() -> int:
    report = build_citation_faithfulness(ROOT)
    failures = report.get("failures") or []
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif failures:
        print("FAIL: manuscript citation faithfulness problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        status = report.get("status")
        counts = report.get("counts") or {}
        if status == "inactive":
            print("PASS: manuscript citation faithfulness inactive (no cited manuscript sentences detected)")
        else:
            print(f"PASS: manuscript citation faithfulness traceability valid ({counts})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
