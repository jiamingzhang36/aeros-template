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
    tidy = build_task_preflight(ROOT, intent="tidy up the folder structure")
    if tidy.get("task_mode") != "general_guardrail":
        failures.append(f"neutral work should default to general_guardrail, got {tidy.get('task_mode')}")
    if "evidence/claim_registry.md" not in (tidy.get("must_not_touch") or []):
        failures.append("neutral preflight incorrectly unlocked claim_registry")
    permission = report.get("source_capture_permission") or {}
    if permission.get("approval_required") != "route_level":
        failures.append("recapture/browser-ish preflight should require route-level approval")
    fraud = build_task_preflight(ROOT, lane="data", intent="franchise fraud litigation negative seed route")
    if fraud.get("route") != "pending" or fraud.get("route_suggestion") != "negative_seed_first":
        failures.append("route decision should remain pending while surfacing negative_seed_first as suggestion")
    public = build_task_preflight(ROOT, lane="data", intent="public official source snapshot")
    if (public.get("source_capture_permission") or {}).get("approval_required") != "none_for_staging_public_capture":
        failures.append("public staging source capture should not require human approval")
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
