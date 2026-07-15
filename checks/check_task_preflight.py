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
from aeros.runtime import kernel as kernel_mod
from aeros.runtime import state as state_mod
from aeros.runtime.contract import load_contract
from aeros.runtime.kernel import run_task


def _accepted_task_reuse_is_enforced() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_preflight_reuse_") as name:
        tmp = Path(name)
        (tmp / "tasks").mkdir()
        (tmp / "data").mkdir()
        (tmp / "outputs").mkdir()
        (tmp / "project_manifest.yml").write_text("project:\n  name: reuse-fixture\n", encoding="utf-8")
        (tmp / "data/input.csv").write_text("id,value\n1,10\n", encoding="utf-8")
        (tmp / "outputs/result.csv").write_text("id,result\n1,20\n", encoding="utf-8")
        task_path = tmp / "tasks/T_REUSE.yml"
        task_path.write_text(
            "task_id: T_REUSE\nstage: execution\ngate: G4\nwork_lane: data\n"
            "goal: process a large data input once\ninputs:\n  - data/input.csv\n"
            "checks: []\nallowed_outputs:\n  - outputs/result.csv\n"
            "allowed_skills: []\nrequired_skill_classes: []\n"
            "budget:\n  max_agent_calls: 1\n  max_dollars: 0.01\n"
            "  max_retries: 0\n  task_timeout_seconds: 5\n",
            encoding="utf-8",
        )
        contract = load_contract(task_path)
        contracts = {contract.task_id: (contract, task_path)}
        state = state_mod.load_state(tmp)
        state_mod.set_status(state, contract.task_id, "passed")
        kernel_mod._record_task_fingerprints(state, contract, tmp, contracts)
        state_mod.save_state(tmp, state)
        report = build_task_preflight(tmp, task_id=contract.task_id, lane="data", intent=contract.goal)
        reuse = report.get("reuse_decision") or {}
        if reuse.get("status") != "PREVIOUSLY_ACCEPTED" or reuse.get("should_execute") is not False:
            failures.append("passed task with present accepted output was not routed to reuse")
        original_fingerprint = kernel_mod._fingerprint_paths
        try:
            def _unexpected_content_hash(*_args, **_kwargs):
                raise AssertionError("unchanged stat guards should avoid content hashing")
            kernel_mod._fingerprint_paths = _unexpected_content_hash
            if kernel_mod._stale_reason(state, contract, tmp, contracts):
                failures.append("unchanged stat guards unexpectedly marked the task stale")
            if run_task(task_path) != 0:
                failures.append("direct run did not reuse an unchanged passed task")
        except AssertionError as exc:
            failures.append(str(exc))
        finally:
            kernel_mod._fingerprint_paths = original_fingerprint
        (tmp / "data/input.csv").write_text("id,value\n1,11\n", encoding="utf-8")
        if kernel_mod._stale_reason(state, contract, tmp, contracts) != "input_changed":
            failures.append("changed large-data input was not detected after the stat-guard fast path")
    return failures


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
            "version: 1\ncampaign_id: t\nwork_lane: data\nobjective_metric: n\n"
            "objective_markers:\n  - source leads\n  - numerator\ncurrent_value: 5\n"
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
        undeclared_same = build_task_preflight(tmp, lane="data", intent="collect more source leads")
        if undeclared_same.get("status") != "BLOCKED" or undeclared_same.get("campaign_status") != "UNDECLARED_CAMPAIGN_SCOPE":
            failures.append("undeclared same-lane/same-objective work must be blocked after a campaign breaker trips")
        if "undeclared_campaign_scope" not in [b.get("breaker_id") for b in (undeclared_same.get("campaign_breakers") or [])]:
            failures.append("undeclared campaign escape guard did not surface its breaker")
        if not undeclared_same.get("needs_human_decision"):
            failures.append("undeclared campaign scope must require a human decision")
        unrelated_data = build_task_preflight(tmp, lane="data", intent="validate a separate outcome data dictionary")
        if unrelated_data.get("status") == "BLOCKED" or unrelated_data.get("campaign_status") != "TASK_NOT_IN_CAMPAIGN":
            failures.append("same-lane work with no objective-marker match must remain outside the active campaign")
        mismatch = build_task_preflight(tmp, lane="data", intent="another campaign", campaign_id="other")
        if mismatch.get("status") == "BLOCKED" or mismatch.get("campaign_status") != "CAMPAIGN_MISMATCH":
            failures.append("active campaign must not block a different campaign_id")
        mismatch_same = build_task_preflight(tmp, lane="data", intent="collect more source leads", campaign_id="other")
        if mismatch_same.get("status") != "BLOCKED" or mismatch_same.get("campaign_status") != "CAMPAIGN_SCOPE_COLLISION":
            failures.append("different campaign_id must not bypass a stopped campaign with the same lane/objective markers")
        if "campaign_scope_collision" not in [b.get("breaker_id") for b in (mismatch_same.get("campaign_breakers") or [])]:
            failures.append("campaign scope collision did not surface its breaker")
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
        undeclared_path = tmp / "tasks/T_UNDECLARED.yml"
        undeclared_path.write_text(
            "task_id: T_UNDECLARED\nstage: execution\nwork_lane: data\n"
            "goal: collect more source leads\nchecks: []\nallowed_outputs:\n"
            "  - outputs/undeclared_should_not_exist.txt\nbudget:\n"
            "  max_agent_calls: 0\n  max_dollars: 0\n",
            encoding="utf-8",
        )
        if run_task(undeclared_path) != 2:
            failures.append("aeros run did not block undeclared same-campaign work")
        if (tmp / "outputs/undeclared_should_not_exist.txt").exists():
            failures.append("undeclared campaign escape unexpectedly produced output")
        (tmp / "campaigns/active_campaign.yml").write_text(
            "version: 1\ncampaign_id: legacy\nwork_lane: data\nobjective_metric: n\ncurrent_value: 5\n"
            "stop_condition: x\nstop_condition_met: false\ntask_budget: 8\n"
            "expected_yield_per_task: 3\nmarginal_yield_window: 3\n"
            "binding_constraint: numerator\nfallback_if_stalled: escalate\n",
            encoding="utf-8",
        )
        legacy_same_lane = build_task_preflight(tmp, lane="data", intent="continue another collection task")
        if legacy_same_lane.get("status") != "BLOCKED" or legacy_same_lane.get("campaign_status") != "UNDECLARED_CAMPAIGN_SCOPE":
            failures.append("legacy active campaign without objective_markers must fail closed for undeclared same-lane work")
        # Output-target dimension: rewording the intent to dodge every objective
        # marker must NOT escape when the task still writes into the campaign's
        # owned output class; genuinely unrelated output must stay free.
        (tmp / "campaigns/active_campaign.yml").write_text(
            "version: 1\ncampaign_id: t2\nwork_lane: data\nobjective_metric: n\n"
            "objective_markers:\n  - source leads\n"
            "objective_outputs:\n  - data/backfill/\ncurrent_value: 5\n"
            "stop_condition: x\nstop_condition_met: false\ntask_budget: 8\n"
            "expected_yield_per_task: 3\nmarginal_yield_window: 3\n"
            "binding_constraint: numerator\nfallback_if_stalled: escalate\n",
            encoding="utf-8",
        )
        reworded = tmp / "tasks/T_REWORDED.yml"
        reworded.write_text(
            "task_id: T_REWORDED\nstage: execution\nwork_lane: data\n"
            "goal: grab more data points for the sample\nchecks: []\n"
            "allowed_outputs:\n  - data/backfill/reworded.csv\n"
            "budget:\n  max_agent_calls: 0\n  max_dollars: 0\n",
            encoding="utf-8",
        )
        rw = build_task_preflight(tmp, task_id="T_REWORDED", lane="data",
                                  intent="grab more data points for the sample")
        if rw.get("status") != "BLOCKED" or rw.get("campaign_status") != "UNDECLARED_CAMPAIGN_SCOPE":
            failures.append("reworded intent writing to the campaign output class must not escape the breaker")
        if not rw.get("campaign_scope_match") or not rw["campaign_scope_match"].get("output_match"):
            failures.append("output-target scope match did not fire for campaign-owned output class")
        unrelated_out = tmp / "tasks/T_UNRELATED_OUT.yml"
        unrelated_out.write_text(
            "task_id: T_UNRELATED_OUT\nstage: execution\nwork_lane: data\n"
            "goal: draft a separate data codebook\nchecks: []\n"
            "allowed_outputs:\n  - docs/codebook.md\n"
            "budget:\n  max_agent_calls: 0\n  max_dollars: 0\n",
            encoding="utf-8",
        )
        uo = build_task_preflight(tmp, task_id="T_UNRELATED_OUT", lane="data",
                                  intent="draft a separate data codebook")
        if uo.get("status") == "BLOCKED" or uo.get("campaign_status") != "TASK_NOT_IN_CAMPAIGN":
            failures.append("work writing only to an unrelated output class must stay outside the campaign")
        # Inferred output class: a campaign that declares NO objective_outputs
        # must still learn its output footprint from the contracts of tasks that
        # recorded progress, so reworded same-output work cannot escape; generic
        # scaffolding dirs must not be learned (no over-block).
        (tmp / "campaigns/active_campaign.yml").write_text(
            "version: 1\ncampaign_id: t3\nwork_lane: data\nobjective_metric: n\n"
            "objective_markers:\n  - source leads\ncurrent_value: 5\n"
            "stop_condition: x\nstop_condition_met: false\ntask_budget: 8\n"
            "expected_yield_per_task: 3\nmarginal_yield_window: 3\n"
            "binding_constraint: numerator\nfallback_if_stalled: escalate\n",
            encoding="utf-8",
        )
        for i in range(3):
            (tmp / f"tasks/P{i}.yml").write_text(
                f"task_id: P{i}\nstage: execution\nwork_lane: data\ngoal: collect source leads\n"
                f"checks: []\nallowed_outputs:\n  - data/backfill/leads_{i}.csv\n  - audits/note.md\n"
                "budget:\n  max_agent_calls: 0\n  max_dollars: 0\n",
                encoding="utf-8",
            )
        with (tmp / "campaigns/campaign_progress.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["task_id", "task_type", "metric_before", "metric_after",
                        "marginal_yield", "target_constraint", "used_batch_source", "decision_metric_rerun"])
            for i in range(3):
                w.writerow([f"P{i}", "collect", i, i + 1, 1, "numerator", "false", "false"])
        (tmp / "tasks/T_INFERRED.yml").write_text(
            "task_id: T_INFERRED\nstage: execution\nwork_lane: data\n"
            "goal: grab more data points\nchecks: []\n"
            "allowed_outputs:\n  - data/backfill/more.csv\n"
            "budget:\n  max_agent_calls: 0\n  max_dollars: 0\n",
            encoding="utf-8",
        )
        inferred = build_task_preflight(tmp, task_id="T_INFERRED", lane="data",
                                        intent="grab more data points")
        if inferred.get("status") != "BLOCKED" or inferred.get("campaign_status") != "UNDECLARED_CAMPAIGN_SCOPE":
            failures.append("reworded work writing to a progress-inferred output class must be blocked")
        learned = (inferred.get("campaign_scope_match") or {}).get("inferred_outputs") or []
        if "data/backfill/" not in learned:
            failures.append("campaign output class was not inferred from progress task contracts")
        if any(p.startswith(("audits/", "agent_runs/")) for p in learned):
            failures.append("generic scaffolding dir was wrongly inferred as a campaign output class")
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
    broad_skill = broad.get("skill_use_contract") or {}
    if broad_skill.get("use_or_waive_required") or broad_skill.get("required_skill_classes"):
        failures.append("broad_capture preflight must not create a skill use-or-waive obligation")
    promote = build_task_preflight(ROOT, lane="data", intent="promote source candidate to canonical processed data")
    if promote.get("task_mode") == "broad_capture":
        failures.append("promotion/canonical work must not remain in broad_capture mode")
    portfolio = build_task_preflight(ROOT, intent="prioritize the research portfolio, enforce WIP, and decide pivot or hold")
    portfolio_skills = ((portfolio.get("skill_use_contract") or {}).get("candidate_skills_by_class") or {})
    if "research-portfolio-gatekeeper" not in portfolio_skills.get("portfolio_governance", []):
        failures.append("portfolio work did not surface research-portfolio-gatekeeper")
    recovery = build_task_preflight(ROOT, intent="recover missing evidence after 403 and enforce the claim ceiling")
    recovery_skills = ((recovery.get("skill_use_contract") or {}).get("candidate_skills_by_class") or {})
    if "evidence-recovery-and-claim-ceiling" not in recovery_skills.get("evidence_recovery", []):
        failures.append("evidence recovery work did not surface evidence-recovery-and-claim-ceiling")
    release = build_task_preflight(ROOT, intent="prepare the canonical PDF release package")
    release_skills = ((release.get("skill_use_contract") or {}).get("candidate_skills_by_class") or {})
    if "research-release-controller" not in release_skills.get("release_control", []):
        failures.append("release work did not surface research-release-controller")
    failures.extend(_accepted_task_reuse_is_enforced())
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
