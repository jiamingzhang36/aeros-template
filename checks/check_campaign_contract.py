#!/usr/bin/env python3
"""Exercise AEROS campaign contract circuit-breaker semantics."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.campaign import assess_campaign  # noqa: E402
from aeros.runtime.completion import write_completion_receipt  # noqa: E402
from aeros.runtime.contract import load_contract  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _write_contract(path: Path, extra: str = "") -> None:
    path.write_text(
        "\n".join([
            "version: 1",
            "campaign_id: restriction_backfill_test",
            "objective_metric: clean_restriction_events",
            "current_value: 46",
            "stop_condition: own_ctrl_RF_p < 0.05 robust",
            "stop_condition_met: false",
            "task_budget: 4",
            "expected_yield_per_task: 3",
            "marginal_yield_window: 3",
            "binding_constraint: numerator_size",
            "fallback_if_stalled: batch-ingest trackers or escalate to human",
            "batch_source_available: true",
            "rerun_decision_metric_after_gain: 5",
            extra,
            "",
        ]),
        encoding="utf-8",
    )


def _write_progress(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "task_id",
        "task_type",
        "metric_before",
        "metric_after",
        "marginal_yield",
        "target_constraint",
        "used_batch_source",
        "decision_metric_rerun",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        no_active = assess_campaign(tmp)
        if no_active.get("status") != "NO_ACTIVE_CAMPAIGN":
            failures.append("missing campaign contract should be an inactive advisory state")

        contract = tmp / "campaign.yml"
        progress = tmp / "progress.csv"
        _write_contract(contract)
        _write_progress(progress, [
            {"task_id": "T1", "task_type": "single_lookup", "metric_before": 46, "metric_after": 47, "marginal_yield": 1, "target_constraint": "numerator_size", "used_batch_source": "false", "decision_metric_rerun": "false"},
            {"task_id": "T2", "task_type": "single_lookup", "metric_before": 47, "metric_after": 48, "marginal_yield": 1, "target_constraint": "numerator_size", "used_batch_source": "false", "decision_metric_rerun": "false"},
            {"task_id": "T3", "task_type": "single_lookup", "metric_before": 48, "metric_after": 49, "marginal_yield": 1, "target_constraint": "official_purity", "used_batch_source": "false", "decision_metric_rerun": "false"},
            {"task_id": "T4", "task_type": "single_lookup", "metric_before": 49, "metric_after": 52, "marginal_yield": 3, "target_constraint": "numerator_size", "used_batch_source": "false", "decision_metric_rerun": "false"},
        ])
        report = assess_campaign(tmp, contract_path=contract, progress_path=progress)
        ids = {breaker.get("breaker_id") for breaker in report.get("breakers") or []}
        for expected in ["task_budget_exhausted", "binding_constraint_drift", "batch_source_unused", "collecting_without_testing"]:
            if expected not in ids:
                failures.append(f"campaign breaker did not fire {expected}")
        if report.get("status") != "ESCALATE":
            failures.append("campaign with fired breakers should report ESCALATE")
        if not report.get("does_not_prove"):
            failures.append("campaign report must carry does_not_prove boundaries")

        healthy = tmp / "healthy.csv"
        _write_progress(healthy, [
            {"task_id": "H1", "task_type": "batch_ingest", "metric_before": 46, "metric_after": 51, "marginal_yield": 5, "target_constraint": "numerator_size", "used_batch_source": "true", "decision_metric_rerun": "true"},
        ])
        healthy_report = assess_campaign(tmp, contract_path=contract, progress_path=healthy)
        if healthy_report.get("status") != "CONTINUE":
            failures.append("healthy campaign should continue")

        # A passed campaign task records evidence-bound progress exactly once.
        auto_root = tmp / "auto_progress"
        (auto_root / "campaigns").mkdir(parents=True)
        (auto_root / "tasks").mkdir()
        (auto_root / "outputs").mkdir()
        _write_contract(auto_root / "campaigns/active_campaign.yml")
        evidence = auto_root / "outputs/metric.json"
        evidence.write_text('{"clean_official_events": 47}\n', encoding="utf-8")
        task_path = auto_root / "tasks/T_CAMPAIGN.yml"
        task_path.write_text(
            "task_id: T_CAMPAIGN\nstage: execution\nwork_lane: data\n"
            "campaign_id: restriction_backfill_test\n"
            "campaign_progress:\n  task_type: source_verification\n  metric_before: 46\n"
            "  metric_after: 47\n  target_constraint: numerator_size\n"
            "  used_batch_source: false\n  decision_metric_rerun: false\n"
            "  metric_evidence_path: outputs/metric.json\n"
            "skill_waivers:\n  - skill_class: data_source\n"
            "    reason: deterministic fixture uses a precomputed local metric artifact\n"
            "    scope: campaign_progress_fixture\n    progress_label: CHECK_PASS\n"
            "goal: verify one clean official event\nchecks: []\n"
            "allowed_outputs:\n  - outputs/metric.json\n",
            encoding="utf-8",
        )
        task_contract = load_contract(task_path)
        first = write_completion_receipt(auto_root, task_contract, mode="deterministic", check_results=[])
        second = write_completion_receipt(auto_root, task_contract, mode="revalidation", check_results=[])
        if not first.passed or not second.passed:
            failures.append(
                "valid campaign task completion should pass and remain idempotent: "
                f"first={first.failures}; second={second.failures}"
            )
        progress_path = auto_root / "campaigns/campaign_progress.csv"
        auto_rows: list[dict[str, str]] = []
        if not progress_path.exists():
            failures.append("campaign completion did not create campaign_progress.csv")
        else:
            with progress_path.open(newline="", encoding="utf-8") as handle:
                auto_rows = list(csv.DictReader(handle))
        if len(auto_rows) != 1 or auto_rows[0].get("marginal_yield") != "1":
            failures.append("campaign completion did not append exactly one computed progress row")
        if not auto_rows or not auto_rows[0].get("metric_evidence_sha256"):
            failures.append("campaign progress row is not anchored to metric evidence")

        proc = subprocess.run(
            [sys.executable, "-m", "aeros.cli", "campaign", "assess", "--contract", str(contract), "--progress", str(progress), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            failures.append("aeros campaign assess failed: " + (proc.stderr or proc.stdout)[-800:])
        else:
            payload = json.loads(proc.stdout)
            if payload.get("model") != "AEROS-CAMPAIGN-001":
                failures.append("campaign CLI did not emit AEROS-CAMPAIGN-001 model")
            if payload.get("status") != "ESCALATE":
                failures.append("campaign CLI did not surface ESCALATE")

    if failures:
        print("FAIL: campaign contract problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: campaign contract circuit breaker is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
