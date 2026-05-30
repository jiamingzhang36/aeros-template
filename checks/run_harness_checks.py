#!/usr/bin/env python3
"""Run the default AEROS harness checks."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


CHECKS = [
    "check_stage_agents.py",
    "check_skill_layer.py",
    "check_correction_ledger.py",
    "check_discovery_completeness.py",
    "check_gate_exit.py",
    "check_idea_bank.py",
    "check_feasibility_matrix.py",
    "check_literature_tools.py",
    "check_git_guardrails.py",
    "check_data_inventory.py",
    "check_data_contract.py",
    "check_protected_definitions.py",
    "check_claim_registry.py",
    "check_claim_method_consistency.py",
    "check_paper_numbers.py",
    "check_output_reproducibility.py",
    "check_project_status.py",
    "check_provenance.py",
    "check_task_contract.py",
    "check_agent_runs_tools.py",
    "check_pipeline_runs.py",
    "check_replication_package.py",
]


def _detect_draft_warning(lines: list[str]) -> tuple[bool, list[str]]:
    warning_anchor = "WARN: protected files have uncommitted changes while status is draft:"
    filtered: list[str] = []
    saw_warning = False
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith(warning_anchor):
            saw_warning = True
            i += 1
            while i < len(lines):
                candidate = lines[i]
                if candidate.startswith("Draft mode:"):
                    break
                stripped = candidate.lstrip()
                if not stripped:
                    i += 1
                    continue
                if stripped[:1] in {"M", "D", "A", "R", "C", "U"}:
                    i += 1
                    continue
                break
            if i < len(lines) and lines[i].startswith("Draft mode:"):
                i += 1
            continue
        filtered.append(line)
        i += 1

    return saw_warning, filtered


def _run_check(check_path: Path, draft_warning_mode: str) -> tuple[int, bool]:
    result = subprocess.run(
        [sys.executable, str(check_path)],
        capture_output=True,
        text=True,
    )

    output_lines = (result.stdout or "").splitlines()
    if result.stderr:
        output_lines.extend((result.stderr or "").splitlines())

    draft_warning_seen = False
    if draft_warning_mode != "on":
        draft_warning_seen, output_lines = _detect_draft_warning(output_lines)

    if output_lines:
        print("\n".join(output_lines))

    if result.returncode != 0:
        return 1, draft_warning_seen

    if draft_warning_mode == "fail" and draft_warning_seen:
        print(
            "FAIL: draft-protected-definitions warning treated as failure "
            "(set AEROS_DRAFT_WARNING=off to ignore)"
        )
        return 1, draft_warning_seen

    return 0, draft_warning_seen


def _normalize_draft_warning_mode(raw_mode: str | None) -> str:
    mode = (raw_mode or "").strip().lower()
    if mode in {"on", "off", "fail"}:
        return mode
    raise ValueError(f"invalid draft warning mode: {raw_mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run default AEROS harness checks.")
    parser.add_argument(
        "--draft-warning",
        default=None,
        choices=["on", "off", "fail"],
        help="Draft-protected-definitions warning mode: on=show, off=suppress, fail=treat as failure",
    )
    args = parser.parse_args()

    draft_warning_mode = _normalize_draft_warning_mode(
        args.draft_warning or os.getenv("AEROS_DRAFT_WARNING", "off")
    )
    check_dir = Path("checks")
    failures = 0

    for check in CHECKS:
        path = check_dir / check
        print(f"==> {path}")
        failure, _ = _run_check(path, draft_warning_mode)
        if failure:
            failures += 1
    if failures:
        print(f"FAIL: {failures} harness check(s) failed")
        return 1
    print("PASS: all harness checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
