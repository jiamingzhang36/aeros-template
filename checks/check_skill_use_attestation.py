#!/usr/bin/env python3
"""Validate completion-level skill use-or-waive proof."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.completion import write_completion_receipt
from aeros.runtime.contract import load_contract
from aeros.runtime.skill_receipt import validate_skill_invocations, write_skill_invocation_receipt


class CheckResult:
    name = "check_fixture.py"
    passed = True
    command = ["python3", "checks/check_fixture.py"]
    exit_code = 0
    elapsed_seconds = 0.01


def _write_common(root: Path) -> None:
    (root / "harness").mkdir(parents=True)
    (root / "outputs").mkdir(parents=True)
    (root / "outputs/demo.txt").write_text("demo\n", encoding="utf-8")
    (root / "harness/skill_map_core.yml").write_text(
        """skills:
  data_inventory:
    name: data-inventory
    source: fixture
    tier: core
    use_status: enabled
    aeros_stage: data_scouting
    human_gate_required: false
    aeros_constraints: []
  pre_submission:
    name: pre-submission-audit
    source: fixture
    tier: core
    use_status: enabled
    aeros_stage: submission_review
    human_gate_required: false
    aeros_constraints: []
""",
        encoding="utf-8",
    )
    (root / "harness/skill_obligation_policy.yml").write_text(
        "profile_required_skill_classes:\n  submit: [submission_review]\n"
        "classes:\n"
        "  data_source:\n    skills: [data-inventory]\n    triggers: [data]\n"
        "  submission_review:\n    skills: [pre-submission-audit]\n    triggers: [submission]\n",
        encoding="utf-8",
    )


def _write_contract(root: Path, *, waiver: bool = False) -> Path:
    path = root / ("task_with_waiver.yml" if waiver else "task.yml")
    waiver_block = ""
    if waiver:
        waiver_block = """skill_waivers:
  - skill_class: data_source
    reason: fixture explicitly waives data-source skill use
    scope: fixture only
    progress_label: ROUTE_READY
"""
    path.write_text(
        f"""task_id: T999
stage: execution
gate: G4
work_lane: data
goal: fixture skill proof
checks:
  - check_fixture.py
allowed_outputs:
  - outputs/demo.txt
allowed_skills:
  - data-inventory
required_skill_classes:
  - data_source
{waiver_block}""",
        encoding="utf-8",
    )
    return path


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_skill_use_") as tmp:
        root = Path(tmp)
        _write_common(root)
        contract = load_contract(_write_contract(root))

        missing = write_completion_receipt(root, contract, mode="recover", check_results=[CheckResult()])
        if missing.passed:
            failures.append("completion passed without skill invocation or waiver")
        att = missing.payload.get("skill_use_attestation") or {}
        if att.get("verdict") != "fail" or not att.get("missing_skill_decision"):
            failures.append("missing skill decision was not represented in skill_use_attestation")

        skill_receipt = write_skill_invocation_receipt(root, contract, skills_used=["data-inventory"])
        used = write_completion_receipt(root, contract, mode="recover", check_results=[CheckResult()], skill_receipt_path=skill_receipt)
        if not used.passed:
            failures.append(f"completion with valid skill invocation did not pass: {used.failures}")
        if (used.payload.get("skill_use_attestation") or {}).get("verdict") != "pass":
            failures.append("valid skill invocation did not produce passing attestation")
        invocation_failures = validate_skill_invocations(
            root, {contract.task_id: (contract, contract.path)}
        )
        if invocation_failures:
            failures.append(
                "candidate skill did not satisfy its required class in invocation validation: "
                + "; ".join(invocation_failures)
            )

        waiver_contract = load_contract(_write_contract(root, waiver=True))
        waived = write_completion_receipt(root, waiver_contract, mode="recover", check_results=[CheckResult()])
        if not waived.passed:
            failures.append(f"completion with explicit waiver did not pass: {waived.failures}")

        (root / "harness/research_profiles.yml").write_text(
            "default_profile: submit\nprofiles:\n  submit:\n    workspace: isolated_candidate_worktree\n",
            encoding="utf-8",
        )
        submit_path = root / "task_submit.yml"
        submit_path.write_text(
            "task_id: T_SUBMIT\nstage: paper\ngate: G10\nwork_lane: writing\n"
            "goal: submission manuscript audit\nchecks: [check_fixture.py]\n"
            "allowed_outputs: [outputs/demo.txt]\n",
            encoding="utf-8",
        )
        submit_contract = load_contract(submit_path)
        missing_submit = write_completion_receipt(root, submit_contract, mode="recover", check_results=[CheckResult()])
        if missing_submit.passed:
            failures.append("submit profile passed without its automatic submission-review skill")
        submit_receipt = write_skill_invocation_receipt(root, submit_contract, skills_used=["pre-submission-audit"])
        used_submit = write_completion_receipt(
            root, submit_contract, mode="recover", check_results=[CheckResult()], skill_receipt_path=submit_receipt,
        )
        if not used_submit.passed:
            failures.append(f"submit profile did not accept its automatic review skill: {used_submit.failures}")
    if failures:
        print("FAIL: skill use attestation problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: skill use attestation is enforced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
