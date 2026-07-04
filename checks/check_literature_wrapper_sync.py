#!/usr/bin/env python3
"""Check source-project literature assets are visible to an AEROS wrapper.

Inactive when no source project is configured. When configured, the wrapper must
not silently hide source extraction cards, because that makes AEROS think the
literature lane is empty or less complete than the real project state.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.submission_driver import build_literature_wrapper_sync  # noqa: E402


def main() -> int:
    report = build_literature_wrapper_sync(ROOT)
    failures = report.get("failures") or []
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif failures:
        print("FAIL: literature wrapper/source sync problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        status = report.get("status")
        if status == "inactive":
            print("PASS: literature wrapper sync inactive (no source project configured)")
        else:
            print(
                "PASS: literature wrapper sync valid "
                f"(source_cards={report.get('source_card_count')}, wrapper_cards={report.get('wrapper_card_count')})"
            )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
