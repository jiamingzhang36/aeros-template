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
            "work_lane: data",
            "objective_metric: clean_restriction_events",
            "objective_markers:",
            "  - clean restriction events",
            "  - source verification",
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


def _campaign_progress(tmp: Path, levels: list[tuple[float, float]]) -> None:
    (tmp / "campaigns").mkdir(parents=True, exist_ok=True)
    with (tmp / "campaigns/campaign_progress.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["campaign_id", "task_id", "task_type", "metric_before", "metric_after",
                    "marginal_yield", "target_constraint", "used_batch_source", "decision_metric_rerun"])
        for i, (b, a) in enumerate(levels):
            w.writerow(["t", f"T{i}", "collect", b, a, a - b, "numerator", "false", "false"])


def _freeze_and_decision_valve() -> list[str]:
    """FREEZE breaker, human continue/stop release valve (with expiry), and the
    metric anti-inflation check must all hold."""
    from aeros.runtime.campaign import (
        assess_campaign, record_campaign_decision, record_campaign_progress,
    )
    import tempfile as _tempfile

    base = ("version: 1\ncampaign_id: t\nwork_lane: data\nobjective_metric: n\ncurrent_value: 5\n"
            "stop_condition: x\nstop_condition_met: false\ntask_budget: 100\nexpected_yield_per_task: 3\n"
            "marginal_yield_window: 3\nconvergence_window: 3\nconvergence_epsilon: 0\n"
            "binding_constraint: numerator\nfallback_if_stalled: escalate\n")
    failures: list[str] = []

    def approve(tmp: Path, decision: str, *, breaker: str = "all", horizon: int = 1) -> str:
        subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "fixture-human"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp, check=True)
        (tmp / "harness").mkdir(exist_ok=True)
        (tmp / "decisions/approvals").mkdir(parents=True, exist_ok=True)
        (tmp / "harness/permissions.yml").write_text(
            "human_approval:\n  enforcement: git_committer\n  approver_identity:\n    - fixture-human\n"
            "  agent_identity:\n    - fixture-agent\n  approval_artifact_dir: decisions/approvals\n",
            encoding="utf-8",
        )
        rel = f"decisions/approvals/campaign_t_{decision}.yml"
        (tmp / rel).write_text(
            f"version: 1\ncampaign_id: t\ndecision: {decision}\nreason: fixture human decision\n"
            f"breaker_id: {breaker}\nexpires_after_tasks: {horizon}\n"
            "approved_at: 2026-07-11T00:00:00Z\ndecision_ref: fixture-review\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "harness/permissions.yml", rel], cwd=tmp, check=True)
        subprocess.run(["git", "commit", "-m", "human campaign approval"], cwd=tmp, check=True, capture_output=True)
        return rel

    # FREEZE: a plateaued objective metric must raise convergence_freeze.
    with _tempfile.TemporaryDirectory() as d:
        tmp = Path(d); (tmp / "campaigns").mkdir()
        (tmp / "campaigns/active_campaign.yml").write_text(base, encoding="utf-8")
        _campaign_progress(tmp, [(40, 50), (50, 50), (50, 50), (50, 50), (50, 50), (50, 50)])
        ids = [b["breaker_id"] for b in assess_campaign(tmp)["breakers"]]
        if "convergence_freeze" not in ids:
            failures.append("plateaued objective metric did not raise the convergence_freeze breaker")

    # CONTINUE decision releases the named breaker, then expires and re-applies.
    with _tempfile.TemporaryDirectory() as d:
        tmp = Path(d); (tmp / "campaigns").mkdir()
        (tmp / "campaigns/active_campaign.yml").write_text(base, encoding="utf-8")
        _campaign_progress(tmp, [(10, 11), (11, 12), (12, 13)])
        approval = approve(tmp, "continue", breaker="low_marginal_yield", horizon=2)
        record_campaign_decision(tmp, decision="continue", approval_artifact=approval)
        rep = assess_campaign(tmp)
        if any(b["breaker_id"] == "low_marginal_yield" for b in rep["breakers"]):
            failures.append("continue decision did not release the low_marginal_yield breaker")
        if not any(x["breaker_id"] == "low_marginal_yield" for x in rep.get("released_breakers", [])):
            failures.append("released breaker was not reported")
        _campaign_progress(tmp, [(i, i + 1) for i in range(6)])  # past the 2-task horizon
        if not any(b["breaker_id"] == "low_marginal_yield" for b in assess_campaign(tmp)["breakers"]):
            failures.append("continue decision must expire and let the breaker re-apply")

    # STOP decision halts the campaign.
    with _tempfile.TemporaryDirectory() as d:
        tmp = Path(d); (tmp / "campaigns").mkdir()
        (tmp / "campaigns/active_campaign.yml").write_text(base, encoding="utf-8")
        _campaign_progress(tmp, [(10, 11), (11, 12), (12, 13)])
        approval = approve(tmp, "stop")
        record_campaign_decision(tmp, decision="stop", approval_artifact=approval)
        rep = assess_campaign(tmp)
        if not rep.get("campaign_halted") or [b["breaker_id"] for b in rep["breakers"]] != ["human_stop"]:
            failures.append("stop decision must halt the campaign with a human_stop breaker")

    # METRIC anti-inflation: a claimed integer gain must be backed by evidence rows.
    with _tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for sub in ("campaigns", "data/backfill"):
            (tmp / sub).mkdir(parents=True)
        (tmp / "campaigns/active_campaign.yml").write_text(base, encoding="utf-8")
        (tmp / "data/backfill/leads.csv").write_text("h\nr1\nr2\n", encoding="utf-8")  # 2 data rows

        class _C:
            task_id = "TX"; work_lane = "data"; allowed_outputs = ["data/backfill/leads.csv"]
            campaign_id = "t"
            campaign_progress = {"metric_before": 0, "metric_after": 100, "target_constraint": "numerator",
                                 "metric_evidence_path": "data/backfill/leads.csv", "task_type": "collect"}

        res = record_campaign_progress(tmp, _C(), completion_mode="auto", completion_receipt_path="r.yml")
        if res["status"] != "invalid_progress_declaration" or not any("exceeds evidence rows" in f for f in res["failures"]):
            failures.append("inflated metric_after (unbacked by evidence rows) must be rejected")

        # Duplicate IDs are one unique unit, not three rows of progress.
        (tmp / "data/backfill/dupes.csv").write_text("id\nr1\nr1\nr1\n", encoding="utf-8")
        class _D:
            task_id = "TD"; work_lane = "data"; allowed_outputs = ["data/backfill/dupes.csv"]
            campaign_id = "t"
            campaign_progress = {"metric_before": 0, "metric_after": 3, "target_constraint": "numerator",
                                 "metric_evidence_path": "data/backfill/dupes.csv", "task_type": "collect",
                                 "metric_unique_key_columns": ["id"]}
        dres = record_campaign_progress(tmp, _D(), completion_mode="auto", completion_receipt_path="rd.yml")
        if not any("novel units 1" in f for f in dres.get("failures", [])):
            failures.append("duplicate evidence keys inflated campaign metric progress")

        # A legitimate zero-gain task ("found nothing new") must still record: it
        # is the diminishing-returns/plateau signal the breakers depend on.
        (tmp / "data/backfill/none.csv").write_text("id\n", encoding="utf-8")  # header only

        class _Z:
            task_id = "TZ"; work_lane = "data"; allowed_outputs = ["data/backfill/none.csv"]
            campaign_id = "t"
            campaign_progress = {"metric_before": 13, "metric_after": 13, "target_constraint": "numerator",
                                 "metric_evidence_path": "data/backfill/none.csv", "task_type": "collect"}

        zres = record_campaign_progress(tmp, _Z(), completion_mode="auto", completion_receipt_path="rz.yml")
        if zres["status"] == "invalid_progress_declaration":
            failures.append(f"zero-gain task must record, not be rejected as empty: {zres['failures']}")

    # Research-value inference: a real value artifact produced since the campaign
    # started must suppress low_decision_value (declared ∪ inferred); an empty
    # project must still fire it with a dual interpretation; and a pre-campaign
    # result must not grant permanent immunity.
    import time as _time
    with _tempfile.TemporaryDirectory() as d:
        tmp = Path(d); (tmp / "campaigns").mkdir()
        (tmp / "campaigns/active_campaign.yml").write_text(base, encoding="utf-8")
        _campaign_progress(tmp, [(0, 5), (5, 10), (10, 15)])  # decent yield, no value events
        fired = [b["breaker_id"] for b in assess_campaign(tmp)["breakers"]]
        if "low_decision_value" not in fired:
            failures.append("no recorded/inferred value must fire low_decision_value")
        (tmp / "evidence").mkdir()
        _time.sleep(0.02)
        (tmp / "evidence/result_registry.csv").write_text("result_id,estimate\nR1,0.4\n", encoding="utf-8")
        rep = assess_campaign(tmp)
        if any(b["breaker_id"] == "low_decision_value" for b in rep["breakers"]):
            failures.append("a real result produced since the campaign must suppress low_decision_value")
        if not rep.get("inferred_research_value"):
            failures.append("inferred research value was not reported")
    return failures


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
        if "low_decision_value" not in ids:
            failures.append("campaign without research_value_events did not raise low_decision_value")
        for expected in ["task_budget_exhausted", "binding_constraint_drift", "batch_source_unused", "collecting_without_testing"]:
            if expected not in ids:
                failures.append(f"campaign breaker did not fire {expected}")
        if report.get("status") != "ESCALATE":
            failures.append("campaign with fired breakers should report ESCALATE")
        if report.get("work_lane") != "data" or "source verification" not in (report.get("objective_markers") or []):
            failures.append("campaign assessment did not retain scope lane/objective markers")
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

    failures.extend(_freeze_and_decision_valve())

    if failures:
        print("FAIL: campaign contract problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: campaign contract circuit breaker is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
