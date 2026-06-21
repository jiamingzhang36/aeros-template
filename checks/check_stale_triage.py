#!/usr/bin/env python3
"""Validate deterministic stale triage plumbing."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aeros.runtime.stale_triage import BUCKETS, format_stale_triage, triage_stale_tasks  # noqa: E402


def main() -> int:
    failures: list[str] = []
    policy_path = ROOT / "harness/stale_triage_policy.yml"
    if not policy_path.exists():
        failures.append("missing harness/stale_triage_policy.yml")
    else:
        data = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        buckets = set((data.get("buckets") or {}).keys())
        if buckets != BUCKETS:
            failures.append(f"policy buckets mismatch: {sorted(buckets)}")
        text = policy_path.read_text(encoding="utf-8").lower()
        for marker in ["no llm", "deterministic", "must not mark tasks stale", "must not"]:
            if marker not in text:
                failures.append(f"policy missing boundary marker {marker!r}")
    try:
        result = triage_stale_tasks(ROOT, stage="discovery", lane="")
        rendered = format_stale_triage(result)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"stale triage failed: {exc}")
        result = None
        rendered = ""
    if result is not None:
        for item in result.items:
            if item.bucket not in BUCKETS:
                failures.append(f"{item.task_id}: invalid bucket {item.bucket}")
            if item.bucket == "rerun_required" and "--dry-run" not in item.command:
                failures.append(f"{item.task_id}: rerun_required command must be dry-run")
            if item.bucket == "revalidate_free" and " recover " not in f" {item.command} " and "--check" not in item.command:
                failures.append(f"{item.task_id}: revalidate_free command must use recover --check")
            if item.bucket == "suppress_as_irrelevant" and item.command.lower() != "no action":
                failures.append(f"{item.task_id}: suppressed stale item must not execute anything")
            if item.bucket == "suppress_as_irrelevant" and (item.frontier_connected or item.output_changed):
                failures.append(f"{item.task_id}: suppressed item is not proven irrelevant")
            if item.claim_bound and item.impact_level != "high":
                failures.append(f"{item.task_id}: claim-bound stale item must be high impact")
    for marker in ["STALE_TRIAGE", "does_not_prove", "does not run agents"]:
        if marker not in rendered:
            failures.append(f"rendered stale triage missing {marker!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    count = len(result.items) if result is not None else 0
    print(f"PASS: stale triage is valid ({count} item(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
