#!/usr/bin/env python3
"""End-to-end campaign lifecycle check.

Unlike check_campaign_contract (unit-level assess/record assertions), this drives
the whole campaign loop through the real code paths in a throwaway project and
asserts the system-level behaviour:

  1. real progress accumulated via the completion path makes a breaker EMERGE,
  2. `run_task` (the real execution entrypoint) BLOCKS the next same-campaign task,
  3. a recorded human `continue` decision RELEASES the breaker,
  4. the release EXPIRES and the breaker re-arms (re-review forced),
  5. a plateaued objective metric raises `convergence_freeze`,
  6. a recorded human `stop` decision HALTS the campaign.

It exists because a static fixture once missed that zero-gain tasks were wrongly
rejected, which silently disabled convergence detection; this lifecycle test
would have caught it.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import subprocess
import json
import os

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.campaign import (  # noqa: E402
    assess_campaign, record_campaign_decision,
)
from aeros.runtime.completion import write_completion_receipt  # noqa: E402
from aeros.runtime.contract import load_contract  # noqa: E402
from aeros.runtime.kernel import run_task  # noqa: E402

CAMPAIGN = (
    "version: 1\ncampaign_id: leads\nwork_lane: data\nobjective_metric: clean_leads\n"
    "objective_markers:\n  - source leads\nobjective_outputs:\n  - data/backfill/\n"
    "current_value: 0\nstop_condition: reach a decision-relevant pool\nstop_condition_met: false\n"
    "task_budget: 100\nexpected_yield_per_task: 3\nmarginal_yield_window: 3\n"
    "convergence_window: 3\nconvergence_epsilon: 0\nbinding_constraint: numerator\n"
    "fallback_if_stalled: batch-ingest or escalate\n"
)


def _breakers(root: Path) -> list[str]:
    return [b["breaker_id"] for b in assess_campaign(root)["breakers"]]


def _collect(root: Path, tid: str, before: int, gain: int, *, value_event: bool = False) -> bool:
    ev = f"data/backfill/{tid}.csv"
    (root / ev).write_text("id\n" + "\n".join(f"{tid}_lead_{i}" for i in range(gain)) + ("\n" if gain else ""), encoding="utf-8")
    tp = root / f"tasks/{tid}.yml"
    event = ""
    if value_event:
        event = (
            "  research_value_events:\n"
            "    - event_type: resolved_data_gap\n"
            "      subject_id: DATA-GAP-1\n"
            "      before_status: blocking\n"
            "      after_status: resolved\n"
            f"      evidence_paths:\n        - {ev}\n"
            "      verification_check: checks/check_data_probe.py\n"
        )
    tp.write_text(
        f"task_id: {tid}\nstage: execution\nwork_lane: data\ncampaign_id: leads\n"
        f"campaign_progress:\n  task_type: source_capture\n  metric_before: {before}\n"
        f"  metric_after: {before + gain}\n  target_constraint: numerator\n"
        f"  used_batch_source: false\n  decision_metric_rerun: false\n  metric_evidence_path: {ev}\n"
        f"  metric_unique_key_columns:\n    - id\n"
        f"{event}"
        f"skill_waivers:\n  - skill_class: data_source\n    reason: e2e fixture local evidence\n"
        f"    scope: e2e\n    progress_label: CHECK_PASS\n"
        f"goal: collect source leads batch\nchecks: []\nallowed_outputs:\n  - {ev}\n",
        encoding="utf-8",
    )
    return write_completion_receipt(root, load_contract(tp), mode="deterministic", check_results=[]).passed


def _research_value_e2e() -> list[str]:
    failures: list[str] = []
    for has_value in (False, True):
        with tempfile.TemporaryDirectory(prefix="aeros_value_e2e_") as name:
            root = Path(name)
            for d in ("campaigns", "tasks", "data/backfill", "discovery/literature"):
                (root / d).mkdir(parents=True, exist_ok=True)
            (root / "project_manifest.yml").write_text("project:\n  name: value_e2e\n", encoding="utf-8")
            (root / "campaigns/active_campaign.yml").write_text(CAMPAIGN, encoding="utf-8")
            metric = 0
            for i in range(3):
                if not _collect(root, f"V{i}", metric, 1, value_event=has_value and i == 2):
                    failures.append(f"research-value fixture completion failed (has_value={has_value}, task={i})")
                metric += 1
            ids = _breakers(root)
            if has_value and "low_decision_value" in ids:
                failures.append("verified research_value_event did not prevent low_decision_value")
            if not has_value and "low_decision_value" not in ids:
                failures.append("quantity-only campaign did not trigger low_decision_value")
    return failures


def _signed_approval_e2e() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_signed_approval_") as name:
        root = Path(name)
        for d in ("campaigns", "harness", "decisions/approvals"):
            (root / d).mkdir(parents=True, exist_ok=True)
        (root / "project_manifest.yml").write_text("project:\n  name: signed_approval_e2e\n", encoding="utf-8")
        (root / "campaigns/active_campaign.yml").write_text(CAMPAIGN, encoding="utf-8")
        (root / "harness/permissions.yml").write_text(
            "human_approval:\n  enforcement: git_committer\n  approver_identity: [fixture-human]\n"
            "  agent_identity: [fixture-agent]\n  approval_artifact_dir: decisions/approvals\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "fixture-human"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        key = root / "fixture_signing_key"
        generated = subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], cwd=root, capture_output=True)
        if generated.returncode != 0:
            return ["ssh-keygen unavailable; signed approval positive E2E cannot run"]
        allowed = root / "allowed_signers"
        allowed.write_text("fixture@example.invalid " + key.with_suffix(".pub").read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["git", "config", "gpg.format", "ssh"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.signingkey", str(key)], cwd=root, check=True)
        subprocess.run(["git", "config", "gpg.ssh.allowedSignersFile", str(allowed)], cwd=root, check=True)
        env = dict(os.environ); env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        approve = subprocess.run([
            sys.executable, "-m", "aeros.cli", "approve", "--campaign-id", "leads",
            "--decision", "continue", "--reason", "signed bounded continuation",
            "--breaker", "low_decision_value", "--for-tasks", "1",
            "--decision-ref", "signed-e2e", "--authority-evidence", "signed_commit", "--commit",
        ], cwd=root, env=env, text=True, capture_output=True)
        if approve.returncode != 0:
            return [f"signed aeros approve failed: {approve.stderr or approve.stdout}"]
        artifact = "decisions/approvals/campaign_leads_continue.yml"
        consume = subprocess.run([
            sys.executable, "-m", "aeros.cli", "campaign", "continue", "--approval", artifact,
        ], cwd=root, env=env, text=True, capture_output=True)
        if consume.returncode != 0:
            failures.append(f"signed campaign approval was not consumable: {consume.stderr or consume.stdout}")
        decision_path = root / "campaigns/campaign_decisions.yml"
        data = __import__("yaml").safe_load(decision_path.read_text(encoding="utf-8")) if decision_path.exists() else {}
        records = (data or {}).get("decisions") or []
        evidence = records[-1].get("authority_evidence") if records else {}
        if not evidence or evidence.get("level") != "signed_commit" or not evidence.get("granted"):
            failures.append("consumed campaign decision does not retain verified signed_commit authority evidence")
    return failures


def _run_lifecycle() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_campaign_e2e_") as name:
        root = Path(name)
        for d in ("campaigns", "tasks", "data/backfill", "discovery/literature"):
            (root / d).mkdir(parents=True, exist_ok=True)
        (root / "project_manifest.yml").write_text("project:\n  name: campaign_e2e\n", encoding="utf-8")
        (root / "campaigns/active_campaign.yml").write_text(CAMPAIGN, encoding="utf-8")

        # No caller-controlled reviewer string may release authority.
        try:
            record_campaign_decision(root, decision="continue", reason="agent self-release")
            failures.append("phase0: campaign decision succeeded without a human approval artifact")
        except PermissionError:
            pass

        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "fixture-human"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        (root / "harness").mkdir(exist_ok=True)
        (root / "decisions/approvals").mkdir(parents=True, exist_ok=True)
        (root / "harness/permissions.yml").write_text(
            "human_approval:\n  enforcement: git_committer\n  approver_identity:\n    - fixture-human\n"
            "  agent_identity:\n    - fixture-agent\n  approval_artifact_dir: decisions/approvals\n",
            encoding="utf-8",
        )

        def approval(decision: str, *, breaker: str = "all", horizon: int = 1) -> str:
            rel = f"decisions/approvals/campaign_leads_{decision}.yml"
            (root / rel).write_text(
                f"version: 1\ncampaign_id: leads\ndecision: {decision}\nreason: fixture human decision\n"
                f"breaker_id: {breaker}\nexpires_after_tasks: {horizon}\n"
                "approved_at: 2026-07-11T00:00:00Z\ndecision_ref: fixture-review\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "harness/permissions.yml", rel], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", f"human {decision} approval"], cwd=root, check=True, capture_output=True)
            return rel

        # Phase 1: breaker emerges from real accumulated diminishing-returns progress.
        metric = 0
        for i, gain in enumerate([5, 4, 2, 1, 1], start=1):
            if not _collect(root, f"C{i}", metric, gain):
                failures.append(f"phase1: completion of C{i} failed")
            metric += gain
        if "low_marginal_yield" not in _breakers(root):
            failures.append("phase1: low_marginal_yield did not emerge from accumulated progress")

        # Phase 2: the real run entrypoint blocks the next same-campaign task.
        blk = root / "tasks/C6.yml"
        blk.write_text(
            "task_id: C6\nstage: execution\nwork_lane: data\ncampaign_id: leads\n"
            "goal: collect more source leads\nchecks: []\nallowed_outputs:\n  - data/backfill/c6.csv\n"
            "budget:\n  max_agent_calls: 0\n  max_dollars: 0\n",
            encoding="utf-8",
        )
        if run_task(blk) != 2:
            failures.append("phase2: run_task did not BLOCK the next same-campaign task")
        if (root / "data/backfill/c6.csv").exists():
            failures.append("phase2: blocked task unexpectedly produced output")

        # Phase 3: a human continue decision releases the breaker.
        record_campaign_decision(root, decision="continue", approval_artifact=approval(
            "continue", breaker="low_marginal_yield", horizon=1))
        if "low_marginal_yield" in _breakers(root):
            failures.append("phase3: continue decision did not release the breaker")

        # Phase 4: the release expires and the breaker re-arms.
        if not _collect(root, "C6b", metric, 1):
            failures.append("phase4: completion of C6b failed")
        metric += 1
        if "low_marginal_yield" not in _breakers(root):
            failures.append("phase4: expired continue decision did not re-arm the breaker")

        # Phase 5: a plateaued objective metric raises convergence_freeze.
        for i in range(3):
            if not _collect(root, f"P{i}", metric, 0):
                failures.append(f"phase5: zero-gain plateau task P{i} failed to record")
        if "convergence_freeze" not in _breakers(root):
            failures.append("phase5: convergence_freeze did not fire on a plateaued metric")

        # Phase 6: a human stop decision halts the campaign.
        record_campaign_decision(root, decision="stop", approval_artifact=approval("stop"))
        rep = assess_campaign(root)
        if not rep.get("campaign_halted") or [b["breaker_id"] for b in rep["breakers"]] != ["human_stop"]:
            failures.append("phase6: stop decision did not halt the campaign")
    return failures


def main() -> int:
    failures = _run_lifecycle() + _research_value_e2e() + _signed_approval_e2e()
    if failures:
        print("FAIL: campaign end-to-end lifecycle problems detected")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS: campaign lifecycle, signed approval, and research-value positive/negative E2E are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
