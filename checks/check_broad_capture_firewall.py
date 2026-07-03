#!/usr/bin/env python3
"""Validate broad-capture low-audit boundaries.

The point of broad_capture is to stop wasting governance on early lead
collection while preserving a hard firewall around processed/canonical/claim
and paper-facing surfaces.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.broad_capture import LEAD_QUEUE_REQUIRED_FIELDS, summarize_broad_capture, validate_broad_capture_writes
from aeros.runtime.execution_mode import recommend_execution_mode
from aeros.runtime.source_capture_permission import classify_source_capture_permission
from aeros.runtime.task_preflight import build_task_preflight


def main() -> int:
    failures: list[str] = []

    mode_policy = yaml.safe_load((ROOT / "harness/execution_mode_policy.yml").read_text(encoding="utf-8")) or {}
    broad = ((mode_policy.get("modes") or {}).get("broad_capture") or {})
    for key, expected in {
        "receipt_level": "lightweight",
        "audit_level": "batch_only",
        "claim_surface": "none_by_construction",
    }.items():
        if broad.get(key) != expected:
            failures.append(f"broad_capture policy must set {key}: {expected}")
    for item in ["data/intermediate", "data/processed", "canonical", "claim_registry"]:
        if item not in (broad.get("promotion_required_for") or []):
            failures.append(f"broad_capture promotion_required_for missing {item}")

    report = recommend_execution_mode(ROOT, lane="data", intent="broad search lead sweep")
    if report.get("mode") != "broad_capture":
        failures.append(f"broad search intent should select broad_capture, got {report.get('mode')}")
    if report.get("claim_surface") != "none_by_construction":
        failures.append("execution mode report did not expose claim_surface none_by_construction")

    preflight = build_task_preflight(ROOT, lane="data", intent="broad search lead sweep into lead queue")
    if preflight.get("task_mode") != "broad_capture":
        failures.append(f"preflight should select broad_capture, got {preflight.get('task_mode')}")
    if preflight.get("execution_mode") != "broad_capture":
        failures.append("preflight broad_capture task did not use broad_capture execution mode")
    if (preflight.get("source_capture_permission") or {}).get("approval_required") != "none_for_broad_lead_capture":
        failures.append("broad lead capture should not require repeated human approval")
    for protected in ["data/processed/", "paper/", "evidence/claim_registry.md"]:
        if protected not in (preflight.get("must_not_touch") or []):
            failures.append(f"preflight must protect {protected}")

    permission = classify_source_capture_permission(
        ROOT,
        lane="data",
        task_mode="broad_capture",
        intent="public broad search lead sweep",
        output_intents=["lead_queue", "candidate_queue", "audit_note"],
        allowed_to_touch=["work/leads/search_notes.md", "data/backfill/foo_lead_queue.csv", "data/backfill/foo_candidate_queue.csv"],
    )
    if permission.get("approval_required") != "none_for_broad_lead_capture":
        failures.append(f"broad capture permission was not green: {permission.get('approval_required')}")

    ok = validate_broad_capture_writes(
        [
            "work/leads/search_notes.md",
            "data/backfill/foo_lead_queue.csv",
            "data/backfill/foo_candidate_queue.csv",
            "audits/broad_capture/batch_roi.md",
        ]
    )
    if not ok.ok:
        failures.append("allowed broad_capture fixture failed: " + "; ".join(ok.failures))

    blocked = validate_broad_capture_writes(
        [
            "data/processed/final.csv",
            "evidence/claim_registry.md",
            "paper/draft.md",
            "data/backfill/freeform.csv",
        ]
    )
    if blocked.ok:
        failures.append("blocked broad_capture fixture unexpectedly passed")
    expected_fragments = ["data/processed/final.csv", "evidence/claim_registry.md", "paper/draft.md", "data/backfill/freeform.csv"]
    joined = "\n".join(blocked.failures)
    for fragment in expected_fragments:
        if fragment not in joined:
            failures.append(f"blocked broad_capture fixture did not mention {fragment}")

    with tempfile.TemporaryDirectory(prefix="aeros_broad_capture_") as tmp_name:
        tmp = Path(tmp_name)
        backfill = tmp / "data" / "backfill"
        backfill.mkdir(parents=True)
        lead_queue = backfill / "demo_lead_queue.csv"
        lead_queue.write_text(
            ",".join(LEAD_QUEUE_REQUIRED_FIELDS + ("promotion_blocker",))
            + "\n"
            + "L001,https://example.test/a,2026-07-01,manual,possible denominator source,negative_seed_first,dedupe-a,unreviewed,30,review source identity,none\n"
            + "L002,https://example.test/b,2026-05-01,manual,possible source,broad_capture,dedupe-b,stale,30,review route,fulltext_missing\n",
            encoding="utf-8",
        )
        candidate_queue = backfill / "demo_candidate_queue.csv"
        candidate_queue.write_text("candidate_id,lead_id,source_url\nC001,L001,https://example.test/a\n", encoding="utf-8")
        summary = summarize_broad_capture(tmp)
        if summary.get("status") != "PASS":
            failures.append("broad capture lead schema fixture failed: " + "; ".join(summary.get("validation_failures") or []))
        if summary.get("total_leads") != 2 or summary.get("total_candidates") != 1:
            failures.append("broad capture metrics did not count lead/candidate queues")
        if summary.get("stale_lead_count") != 1:
            failures.append("broad capture metrics did not count stale leads")

    if failures:
        print("FAIL: broad capture firewall problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: broad capture firewall is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
