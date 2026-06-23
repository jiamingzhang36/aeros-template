#!/usr/bin/env python3
"""Run the default AEROS harness checks."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml


CHECKS = [
    "check_stage_agents.py",
    "check_architecture_freeze.py",
    "check_operating_dashboard.py",
    "check_session_scope.py",
    "check_next_action.py",
    "check_action_spec.py",
    "check_execution_envelope.py",
    "check_progress_semantics.py",
    "check_execution_profiles.py",
    "check_readiness_vector.py",
    "check_estimand_data_contract.py",
    "check_evidence_units.py",
    "check_parser_benchmark.py",
    "check_adversarial_benchmark.py",
    "check_stale_triage.py",
    "check_context_bundle.py",
    "check_context_graph.py",
    "check_cockpit.py",
    "check_harness_profiles.py",
    "check_skill_layer.py",
    "check_skill_invocations.py",
    "check_correction_ledger.py",
    "check_improvement_backlog.py",
    "check_update_ledger.py",
    "check_derived_vs_asserted_audit.py",
    "check_discovery_completeness.py",
    "check_gate_exit.py",
    "check_idea_bank.py",
    "check_feasibility_matrix.py",
    "check_literature_tools.py",
    "check_literature_adapters.py",
    "check_literature_fulltext_execution.py",
    "check_citation_audit.py",
    "check_external_tool_registry.py",
    "check_git_guardrails.py",
    "check_data_inventory.py",
    "check_data_first_readiness.py",
    "check_data_probe.py",
    "check_global_state.py",
    "check_event_log_replay.py",
    "check_sqlite_journal.py",
    "check_evidence_delta_log.py",
    "check_data_backfill_queue.py",
    "check_anchor.py",
    "check_funnel.py",
    "check_design_selection.py",
    "check_no_degenerate_content.py",
    "check_artifact_linkage.py",
    "check_dataset_aware_ideation.py",
    "check_data_contract.py",
    "check_protected_definitions.py",
    "check_claim_registry.py",
    "check_claim_toulmin_schema.py",
    "check_claim_vector.py",
    "check_claim_ceiling.py",
    "check_claim_method_consistency.py",
    "check_identification_gate.py",
    "check_estimand_cards.py",
    "check_research_graph.py",
    "check_artifact_admissibility.py",
    "check_referee_review_present.py",
    "check_claim_numbers_bound.py",
    "check_number_registry.py",
    "check_number_scan.py",
    "check_paper_package.py",
    "check_bib_verification_present.py",
    "check_table_cell_sources.py",
    "check_data_availability_present.py",
    "check_output_reproducibility.py",
    "check_result_registry.py",
    "check_review_verification.py",
    "check_analysis_ledger.py",
    "check_preanalysis_happens_before.py",
    "check_negative_result_ledger.py",
    "check_artifact_manifest.py",
    "check_project_status.py",
    "check_provenance.py",
    "check_provenance_boundary.py",
    "check_exception_scope.py",
    "check_meta_monitor.py",
    "check_data_provenance.py",
    "check_data_fitness.py",
    "check_data_lock.py",
    "check_task_contract.py",
    "check_task_automation_policy.py",
    "check_approval_freshness.py",
    "check_work_lanes.py",
    "check_agent_runs_tools.py",
    "check_action_receipts.py",
    "check_goal_mode_data_progress.py",
    "check_completion_receipts.py",
    "check_noop_runs.py",
    "check_reconcile.py",
    "check_pipeline_runs.py",
    "check_replication_package.py",
    "check_aea_replication_alignment.py",
    "check_compliance_gate.py",
]



def _load_profiles() -> dict:
    path = Path("harness/check_profiles.yml")
    if not path.exists():
        return {"profiles": {"full": {"checks": "all"}}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"profiles": {"full": {"checks": "all"}}}


def _available_profiles() -> list[str]:
    profiles = (_load_profiles().get("profiles") or {})
    return sorted(profiles) or ["full"]


def _checks_for_profile(profile: str) -> list[str]:
    profile = (profile or "full").strip()
    if profile == "full":
        return list(CHECKS)
    profiles = (_load_profiles().get("profiles") or {})
    if profile not in profiles:
        known = ", ".join(sorted(profiles) or ["full"])
        raise ValueError(f"unknown check profile {profile!r}; known profiles: {known}")
    checks = (profiles.get(profile) or {}).get("checks")
    if checks == "all":
        return list(CHECKS)
    if not isinstance(checks, list) or not checks:
        raise ValueError(f"profile {profile!r} has no checks")
    return [str(check) for check in checks]

def _is_template_repo() -> bool:
    """True only inside the AEROS template itself.

    tools/sync_aeros_latest.zsh lives only in the template and is never synced
    into downstream projects, so its presence is a reliable template marker.
    """
    return Path("tools/sync_aeros_latest.zsh").is_file()


def _template_only_checks() -> set[str]:
    """Checks that validate the template's own development process (see
    harness/check_scope.yml). Skipped when run inside a downstream project."""
    scope = Path("harness/check_scope.yml")
    if not scope.exists():
        return set()
    names: set[str] = set()
    in_list = False
    for raw in scope.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip().endswith(":") and not line.startswith((" ", "-", "\t")):
            in_list = line.strip() == "template_only_checks:"
            continue
        if in_list and line.lstrip().startswith("- "):
            names.add(line.lstrip()[2:].strip().strip("\"'"))
    return names


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    """Stop a timed-out check and its children when the platform supports it."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (AttributeError, ProcessLookupError, PermissionError):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (AttributeError, ProcessLookupError, PermissionError):
            proc.kill()
        proc.wait()


def _should_suppress_draft_line(line: str, suppressing: bool) -> tuple[bool, bool, bool]:
    warning_anchor = "WARN: protected files have uncommitted changes while status is draft:"
    if line.startswith(warning_anchor):
        return True, True, True
    if suppressing:
        if line.startswith("Draft mode:"):
            return True, False, False
        stripped = line.lstrip()
        if not stripped:
            return True, True, False
        if stripped[:1] in {"M", "D", "A", "R", "C", "U"}:
            return True, True, False
        return False, False, False
    return False, False, False


def _run_check(check_path: Path, draft_warning_mode: str, timeout_seconds: int) -> dict:
    started = time.monotonic()
    proc = subprocess.Popen(
        [sys.executable, str(check_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )

    draft_warning_seen = False
    suppressing_draft_warning = False

    assert proc.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    while True:
        if timeout_seconds > 0 and time.monotonic() - started > timeout_seconds:
            _terminate_process(proc)
            elapsed = time.monotonic() - started
            print(
                f"TIMEOUT: {check_path} exceeded {timeout_seconds}s "
                f"(elapsed {elapsed:.1f}s)",
                flush=True,
            )
            return {
                "name": str(check_path),
                "status": "timeout",
                "exit_code": 124,
                "elapsed_seconds": round(elapsed, 3),
                "draft_warning_seen": draft_warning_seen,
            }

        events = selector.select(timeout=0.1)
        if events:
            line = proc.stdout.readline()
        else:
            line = ""
        if line:
            line = line.rstrip("\n")
            if draft_warning_mode != "on":
                suppress, suppressing_draft_warning, saw_warning = _should_suppress_draft_line(
                    line, suppressing_draft_warning
                )
                draft_warning_seen = draft_warning_seen or saw_warning
                if suppress:
                    continue
            print(line, flush=True)
            continue

        if proc.poll() is not None:
            break

    selector.unregister(proc.stdout)

    returncode = proc.wait()
    elapsed = time.monotonic() - started
    print(f"<== {check_path} finished in {elapsed:.1f}s (exit {returncode})", flush=True)

    status = "pass" if returncode == 0 else "fail"
    if returncode != 0:
        return {
            "name": str(check_path),
            "status": status,
            "exit_code": returncode,
            "elapsed_seconds": round(elapsed, 3),
            "draft_warning_seen": draft_warning_seen,
        }

    if draft_warning_mode == "fail" and draft_warning_seen:
        print(
            "FAIL: draft-protected-definitions warning treated as failure "
            "(set AEROS_DRAFT_WARNING=off to ignore)",
            flush=True,
        )
        status = "fail"
        returncode = 1

    return {
        "name": str(check_path),
        "status": status,
        "exit_code": returncode,
        "elapsed_seconds": round(elapsed, 3),
        "draft_warning_seen": draft_warning_seen,
    }


def _normalize_draft_warning_mode(raw_mode: str | None) -> str:
    mode = (raw_mode or "").strip().lower()
    if mode in {"on", "off", "fail"}:
        return mode
    raise ValueError(f"invalid draft warning mode: {raw_mode}")


def _normalize_timeout(raw_timeout: str | int | None) -> int:
    try:
        timeout = int(raw_timeout or 300)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid check timeout: {raw_timeout}") from exc
    if timeout < 0:
        raise ValueError(f"invalid check timeout: {raw_timeout}")
    return timeout


def main() -> int:
    parser = argparse.ArgumentParser(description="Run default AEROS harness checks.")
    parser.add_argument(
        "--draft-warning",
        default=None,
        choices=["on", "off", "fail"],
        help="Draft-protected-definitions warning mode: on=show, off=suppress, fail=treat as failure",
    )
    parser.add_argument(
        "--timeout",
        default=None,
        type=int,
        help=(
            "per-check timeout in seconds; 0 disables timeout "
            "(default: AEROS_CHECK_TIMEOUT or 300)"
        ),
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="write a structured JSON summary while still streaming human-readable output",
    )
    parser.add_argument(
        "--profile",
        default="full",
        help="check profile to run: full, smoke, lane:data, lane:literature, lane:method, lane:claim, lane:writing, lane:compliance",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="list configured check profiles and exit",
    )
    args = parser.parse_args()
    if args.list_profiles:
        for profile in _available_profiles():
            print(profile)
        return 0

    draft_warning_mode = _normalize_draft_warning_mode(
        args.draft_warning or os.getenv("AEROS_DRAFT_WARNING", "off")
    )
    timeout_seconds = _normalize_timeout(
        args.timeout if args.timeout is not None else os.getenv("AEROS_CHECK_TIMEOUT", "300")
    )
    check_dir = Path("checks")
    failures = 0
    results: list[dict] = []
    try:
        selected_checks = _checks_for_profile(args.profile)
    except ValueError as exc:
        print(f"FAIL: {exc}", flush=True)
        return 2
    print(f"AEROS harness profile: {args.profile} ({len(selected_checks)} check(s))", flush=True)

    skip_checks: set[str] = set()
    if not _is_template_repo():
        skip_checks = _template_only_checks()

    for check in selected_checks:
        if check in skip_checks:
            print(f"==> checks/{check} SKIP (template-only; not run in a downstream project)", flush=True)
            results.append({"name": f"checks/{check}", "status": "skipped", "exit_code": 0})
            continue
        path = check_dir / check
        print(f"==> {path} (timeout: {'off' if timeout_seconds == 0 else str(timeout_seconds) + 's'})", flush=True)
        result = _run_check(path, draft_warning_mode, timeout_seconds)
        results.append(result)
        if result["status"] != "pass":
            failures += 1
    summary = {
        "status": "fail" if failures else "pass",
        "profile": args.profile,
        "failures": failures,
        "checks": results,
    }
    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"wrote JSON summary -> {out_path}", flush=True)
    if failures:
        print(f"FAIL: {failures} harness check(s) failed")
        return 1
    print("PASS: all harness checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
