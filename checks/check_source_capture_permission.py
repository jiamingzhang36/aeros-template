#!/usr/bin/env python3
"""Validate source capture permission tiering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.source_capture_permission import classify_source_capture_permission

POLICY = Path("harness/source_capture_permission_policy.yml")


def main() -> int:
    failures: list[str] = []
    data = yaml.safe_load(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    tiers = set((data or {}).get("tiers") or {})
    expected = {"green_public_staging", "green_broad_capture", "yellow_route_level", "red_human_required"}
    if tiers != expected:
        failures.append(f"policy tiers mismatch: expected {sorted(expected)}, got {sorted(tiers)}")

    green = classify_source_capture_permission(
        ROOT,
        lane="data",
        task_mode="source_capture",
        intent="public official source snapshot",
        output_intents=["probe_only", "staging_artifact", "audit_note"],
        allowed_to_touch=["work/recapture_sources/", "source_snapshots/", "audits/source_recapture/"],
    )
    if green.get("approval_required") != "none_for_staging_public_capture":
        failures.append(f"green fixture required approval: {green.get('approval_required')}")
    broad = classify_source_capture_permission(
        ROOT,
        lane="data",
        task_mode="broad_capture",
        intent="public broad search lead sweep",
        output_intents=["lead_queue", "candidate_queue", "audit_note"],
        allowed_to_touch=["work/leads/", "data/backfill/demo_lead_queue.csv", "data/backfill/demo_candidate_queue.csv"],
    )
    if broad.get("approval_required") != "none_for_broad_lead_capture":
        failures.append(f"broad fixture required approval: {broad.get('approval_required')}")
    if broad.get("allowed_without_human_approval") is not True:
        failures.append("broad fixture was not allowed_without_human_approval")
    broad_cn = classify_source_capture_permission(
        ROOT,
        lane="data",
        task_mode="broad_capture",
        intent="广泛搜索政府来源，先抓取尽可能多的数据，不进入 processed/canonical/claim",
        output_intents=["lead_queue", "candidate_queue", "audit_note"],
        allowed_to_touch=["work/leads/", "data/backfill/demo_lead_queue.csv", "data/backfill/demo_candidate_queue.csv"],
    )
    if broad_cn.get("approval_required") != "none_for_broad_lead_capture" or broad_cn.get("allowed_without_human_approval") is not True:
        failures.append("Chinese broad-capture fixture should be green without human approval")

    yellow = classify_source_capture_permission(
        ROOT,
        lane="data",
        task_mode="source_capture",
        intent="chrome browser batch portal crawl with possible cloudflare",
        output_intents=["staging_artifact"],
        allowed_to_touch=["work/recapture_sources/", "source_snapshots/"],
    )
    if yellow.get("approval_required") != "route_level":
        failures.append(f"yellow fixture did not require route approval: {yellow.get('approval_required')}")

    red = classify_source_capture_permission(
        ROOT,
        lane="data",
        task_mode="source_capture",
        intent="paid login API key source capture",
        output_intents=["canonical_update"],
        allowed_to_touch=["data/raw/", "evidence/claim_registry.md"],
    )
    if red.get("approval_required") != "human_required":
        failures.append(f"red fixture did not require human approval: {red.get('approval_required')}")

    if "--json" in sys.argv:
        print(json.dumps({"status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: source capture permission problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: source capture permission tiers are valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
