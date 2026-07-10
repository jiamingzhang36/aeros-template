#!/usr/bin/env python3
"""Validate task start preflight packet generation."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.task_preflight import build_task_preflight
from aeros.runtime.kernel import run_task


def _campaign_breaker_blocks_preflight() -> list[str]:
    """A tripped campaign circuit breaker must force preflight to BLOCKED, and no
    active campaign must leave preflight unaffected (backward compatible)."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_preflight_campaign_") as name:
        tmp = Path(name)
        (tmp / "discovery/literature").mkdir(parents=True)
        # no active campaign -> preflight must not be campaign-blocked
        base = build_task_preflight(tmp, lane="data", intent="collect more source leads")
        if base.get("campaign_status") != "NO_ACTIVE_CAMPAIGN" or base.get("campaign_breakers"):
            failures.append("no active campaign should yield zero breakers")
        # Active campaign whose last window all yield below expected. It must
        # block only matching tasks; unrelated and mismatched tasks stay free.
        (tmp / "campaigns").mkdir()
        (tmp / "campaigns/active_campaign.yml").write_text(
            "version: 1\ncampaign_id: t\nobjective_metric: n\ncurrent_value: 5\n"
            "stop_condition: x\nstop_condition_met: false\ntask_budget: 8\n"
            "expected_yield_per_task: 3\nmarginal_yield_window: 3\n"
            "binding_constraint: numerator\nfallback_if_stalled: escalate\n",
            encoding="utf-8",
        )
        with (tmp / "campaigns/campaign_progress.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["task_id", "task_type", "metric_before", "metric_after",
                        "marginal_yield", "target_constraint", "used_batch_source", "decision_metric_rerun"])
            for i in range(3):
                w.writerow([f"T{i}", "collect", i, i + 1, 1, "numerator", "false", "false"])
        unrelated = build_task_preflight(tmp, lane="writing", intent="edit an unrelated appendix")
        if unrelated.get("status") == "BLOCKED" or unrelated.get("campaign_status") != "TASK_NOT_IN_CAMPAIGN":
            failures.append("active campaign must not block a task with no campaign_id")
        mismatch = build_task_preflight(tmp, lane="data", intent="another campaign", campaign_id="other")
        if mismatch.get("status") == "BLOCKED" or mismatch.get("campaign_status") != "CAMPAIGN_MISMATCH":
            failures.append("active campaign must not block a different campaign_id")
        tripped = build_task_preflight(tmp, lane="data", intent="collect more source leads", campaign_id="t")
        if tripped.get("status") != "BLOCKED":
            failures.append(f"tripped campaign breaker must BLOCK preflight, got {tripped.get('status')}")
        if "low_marginal_yield" not in [b.get("breaker_id") for b in (tripped.get("campaign_breakers") or [])]:
            failures.append("preflight did not surface the low_marginal_yield breaker")
        if not tripped.get("needs_human_decision"):
            failures.append("tripped breaker must set needs_human_decision")
        # The real run entrypoint must enforce the same block, not merely render
        # a preflight packet that callers can bypass.
        (tmp / "project_manifest.yml").write_text("project:\n  name: fixture\n", encoding="utf-8")
        (tmp / "tasks").mkdir()
        task_path = tmp / "tasks/T_MATCH.yml"
        task_path.write_text(
            "task_id: T_MATCH\nstage: execution\nwork_lane: data\ncampaign_id: t\n"
            "goal: collect more source leads\nchecks: []\nallowed_outputs:\n  - outputs/should_not_exist.txt\n"
            "budget:\n  max_agent_calls: 0\n  max_dollars: 0\n",
            encoding="utf-8",
        )
        if run_task(task_path) != 2:
            failures.append("aeros run did not enforce matching campaign preflight block")
        if (tmp / "outputs/should_not_exist.txt").exists():
            failures.append("blocked task unexpectedly executed its output path")
    return failures


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
    broad = build_task_preflight(ROOT, lane="data", intent="broad search all possible official source leads")
    if broad.get("task_mode") != "broad_capture" or broad.get("execution_mode") != "broad_capture":
        failures.append("broad source search should default to broad_capture mode")
    if "lead_queue" not in (broad.get("output_intents") or []):
        failures.append("broad_capture preflight should include lead_queue output intent")
    promote = build_task_preflight(ROOT, lane="data", intent="promote source candidate to canonical processed data")
    if promote.get("task_mode") == "broad_capture":
        failures.append("promotion/canonical work must not remain in broad_capture mode")
    failures.extend(_campaign_breaker_blocks_preflight())
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
