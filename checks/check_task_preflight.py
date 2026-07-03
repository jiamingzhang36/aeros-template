#!/usr/bin/env python3
"""Validate task start preflight packet generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.task_preflight import build_task_preflight


def main() -> int:
    failures: list[str] = []
    report = build_task_preflight(ROOT, lane="data", intent="recapture sources in browser for denominator")
    if report.get("task_mode") != "source_capture":
        failures.append(f"expected source_capture, got {report.get('task_mode')}")
    if "staging_artifact" not in (report.get("output_intents") or []):
        failures.append("source preflight did not include staging_artifact output intent")
    if not report.get("allowed_to_touch"):
        failures.append("preflight did not report allowed_to_touch")
    if "data/raw/" not in (report.get("must_not_touch") or []):
        failures.append("preflight did not protect data/raw/")
    fraud = build_task_preflight(ROOT, lane="data", intent="franchise fraud litigation negative seed route")
    if fraud.get("route") != "negative_seed_first":
        failures.append("negative seed route was not inferred for dispute/fraud context")
    if "--json" in sys.argv:
        print(json.dumps({"status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: task preflight problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: task preflight is valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
