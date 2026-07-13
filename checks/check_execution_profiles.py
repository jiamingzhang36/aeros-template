#!/usr/bin/env python3
"""Validate ExecutionProfile wiring."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.execution_profile import load_execution_profiles, resolved_command  # noqa: E402
from aeros.runtime.profile_runtime import runtime_check_plan  # noqa: E402


def main() -> int:
    root = Path.cwd()
    profiles = load_execution_profiles(root)
    failures: list[str] = []
    if "smoke" not in profiles:
        failures.append("missing smoke execution profile")
    for name, profile in profiles.items():
        if not profile.cwd:
            failures.append(f"{name}: missing cwd")
        if not profile.python:
            failures.append(f"{name}: missing python")
        if profile.command and not resolved_command(profile):
            failures.append(f"{name}: command did not resolve")
        if any(hook not in {"reconcile", "session_scope"} for hook in profile.post_run_hooks):
            failures.append(f"{name}: unsupported post_run_hook in {profile.post_run_hooks}")
    policy_path = root / "harness/research_profiles.yml"
    if not policy_path.exists():
        failures.append("missing harness/research_profiles.yml")
    else:
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        if policy.get("default_profile") != "research":
            failures.append("research profile must be the user-facing default")
        if policy.get("status") != "runtime_enforced":
            failures.append("research profiles must be runtime-enforced, not mapping-only")
        research_profiles = policy.get("profiles") or {}
        expected = {"explore", "research", "submit", "regulated"}
        if set(research_profiles) != expected:
            failures.append("research profiles must be exactly explore/research/submit/regulated")
        invariants = policy.get("immutable_invariants") or []
        if len(invariants) != 8 or len({str(item.get('id')) for item in invariants if isinstance(item, dict)}) != 8:
            failures.append("research profiles must share exactly eight named immutable invariants")
        for name, mapping in research_profiles.items():
            if not isinstance(mapping, dict) or mapping.get("promotion_authority") != "unchanged":
                failures.append(f"{name}: profile must not weaken promotion authority")
            if not isinstance(mapping, dict) or mapping.get("workspace") != "isolated_candidate_worktree":
                failures.append(f"{name}: profile must use isolated candidate worktree")
        post_action = policy.get("candidate_post_action_contract") or {}
        required_inputs = set(post_action.get("required_inputs") or [])
        required_failures = set(post_action.get("fail_closed_on") or [])
        if required_inputs != {
            "observed_write_or_dependency_paths",
            "observed_action_exit_code",
            "expected_output_paths",
        }:
            failures.append("candidate post-action contract must require paths, action exit, and expected outputs")
        if not {
            "action_exit_not_observed",
            "action_exit_nonzero",
            "expected_outputs_not_declared",
            "expected_output_missing",
            "expected_output_empty",
            "expected_output_outside_project",
        }.issubset(required_failures):
            failures.append("candidate post-action contract is not fail-closed")
        research_plan = runtime_check_plan(
            root,
            contract_checks=["check_task_preflight.py", "check_action_receipts.py"],
            observed_paths=["outputs/analysis/fixture.csv"],
            profile="research",
        )
        if "check_task_preflight.py" in research_plan.checks or "check_provenance.py" not in research_plan.checks:
            failures.append("ordinary research profile did not replace process checks with artifact-selected checks")
        submit_plan = runtime_check_plan(root, contract_checks=[], observed_paths=["paper/main.tex"], profile="submit")
        if "check_manuscript_citation_interpretation.py" not in submit_plan.checks:
            failures.append("submit profile did not automatically include manuscript truth checks")
        regulated_plan = runtime_check_plan(root, contract_checks=["check_task_preflight.py"], observed_paths=[], profile="regulated")
        if regulated_plan.checks != ("check_task_preflight.py",):
            failures.append("regulated profile did not preserve explicit contract checks")
    if failures:
        print("FAIL: execution profile problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: execution profiles and immutable research-profile mapping are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
