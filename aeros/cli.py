"""AEROS runtime CLI.

    aeros run  tasks/discovery/D001a_framing.yml [--dry-run]
    aeros check tasks/discovery/D001a_framing.yml
    aeros status
    aeros list-tasks

(Before install you can use `python3 -m aeros.cli ...` identically.)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

import yaml

from .kernel.events import Event as KernelEvent, append_event as append_kernel_event, artifact_ref as kernel_artifact_ref
from .runtime.adjudicate import adjudicate, feasibility, write_selection
from .runtime.action_receipt import ActionReceiptArgs, write_action_receipt
from .runtime.adoption import AdoptionArgs, run_adoption
from .runtime.checks import run_checks
from .runtime.collection import collect_prompt_grid, resolve_config
from .runtime.contract import load_contract
from .runtime.controller_loop import ControllerLoopArgs, format_run_until, run_until, run_until_json
from .runtime.context_bundle import build_context_bundle, format_context_bundle, write_context_bundle
from .runtime.cockpit import build_cockpit, format_cockpit, write_cockpit
from .runtime.controller import run_iteration
from .runtime import identity
from .runtime.data_backfill import BackfillArgs, run_data_backfill
from .runtime.data_first import format_plan as format_data_first_plan, write_gaps as write_data_gaps, write_scan as write_data_scan
from .runtime.data_probe import run_probe as run_data_probe, write_probe_plan, write_probe_report
from .runtime.global_state import write_global_state
from .paper_ci.result_registry import register_payload_file, sync_result_index
from .runtime.decision_packet import write_decision_packet
from .runtime.evidence_delta import EvidenceDeltaArgs, append_delta, read_delta_records
from .runtime.init_project import init_project
from .runtime.kernel import find_project_root, run_pipeline, run_task
from .runtime.literature_adapter import LiteratureSearchArgs, format_literature_status, run_literature_search
from .runtime.kernel import _record_task_fingerprints, _task_gates, discover_contracts, topo_order
from .runtime.milestones import format_roadmap, format_simple_status
from .runtime.next_action import compute_next_action, format_next_action, write_next_action
from .runtime.skill_router import format_skill_hint, skill_route
from .runtime.stale_triage import format_stale_triage, stale_triage_json, triage_stale_tasks, write_stale_triage
from .runtime.write_audit import audit_writes, format_write_audit, write_write_audit
from .runtime.state import (
    approve_gate,
    block_gate,
    load_state,
    record_run_summary,
    recompute_candidate_gate,
    save_state,
    set_status,
)

print = partial(print, flush=True)


def _project_root() -> Path:
    return find_project_root(Path.cwd())


def _display_rel(path: str | Path, root: Path) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return p.as_posix()


def _cmd_run(args: argparse.Namespace) -> int:
    if getattr(args, "until", ""):
        root = _project_root()
        rc, records = run_until(root, ControllerLoopArgs(
            until=args.until,
            lane=args.lane or "",
            max_steps=args.max_steps,
            no_progress_limit=args.no_progress_limit,
            max_wall_time_seconds=args.max_wall_time_seconds,
            max_provider_calls=args.max_provider_calls,
            max_cost_usd=args.max_cost_usd,
            dry_run=args.dry_run,
            allow_task_runs=args.allow_task_runs,
            task_timeout=args.task_timeout,
            max_retries=args.max_retries,
        ))
        print(run_until_json(records) if args.json else format_run_until(records))
        return rc
    if not args.contract:
        print("FAIL: provide a task contract, or use `aeros run --until human-gate --dry-run`")
        return 2
    return run_task(args.contract, dry_run=args.dry_run,
                    max_retries_override=args.max_retries,
                    task_timeout_override=args.task_timeout)


def _cmd_event_append(args: argparse.Namespace) -> int:
    root = _project_root()
    inputs = [kernel_artifact_ref(root, p) for p in (args.input or [])]
    outputs = [kernel_artifact_ref(root, p) for p in (args.output or [])]
    # An event minted for an artifact that does not exist gets no hash and no
    # integrity guarantee. Surface that instead of recording it silently.
    missing = [ref["path"] for ref in (*inputs, *outputs) if not ref.get("exists")]
    if missing:
        for rel in missing:
            print(f"WARNING: declared artifact does not exist (recorded with empty hash): {rel}", file=sys.stderr)
        if getattr(args, "require_artifacts", False):
            print("FAIL: --require-artifacts set and some artifacts are missing", file=sys.stderr)
            return 1
    event = KernelEvent(
        event_type=args.event_type,
        action=args.action_name,
        inputs=inputs,
        outputs=outputs,
        evidence=float(args.evidence),
        metadata={"note": args.note or ""},
    )
    path = append_kernel_event(root, event)
    print(f"appended event -> {path.relative_to(root)}")
    return 0


def _cmd_event_replay(args: argparse.Namespace) -> int:
    from .kernel.event_replay import replay
    root = _project_root()
    state = replay(root)
    print(f"events: {state.event_count}")
    print(f"digest: {state.digest}")
    if state.violations:
        print("violations:")
        for violation in state.violations:
            print(f"  - {violation}")
        return 1
    return 0


def _parse_key_value_items(items: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in items or []:
        item = str(raw)
        if "=" not in item:
            out[item] = ""
            continue
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _cmd_delta(args: argparse.Namespace) -> int:
    root = _project_root()
    if args.delta_command == "append":
        path, record, failures = append_delta(
            root,
            EvidenceDeltaArgs(
                lane=args.lane,
                summary=args.summary,
                artifacts_added=args.artifact_added or [],
                artifacts_updated=args.artifact_updated or [],
                coverage_delta=_parse_key_value_items(args.coverage_delta),
                judgment_implications=args.judgment_implication or [],
                remaining_gaps=args.remaining_gap or [],
                next_best_increment=args.next_best_increment,
                sufficiency=args.sufficiency,
                task_id=args.task_id or "",
                run_ref=args.run_ref or "",
                dry_run=args.dry_run,
            ),
        )
        verb = "would append" if args.dry_run else "appended"
        if failures:
            print("delta is not valid:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print(f"{verb} {record['delta_id']} -> {path.relative_to(root)}")
        return 0
    if args.delta_command == "list":
        records, failures = read_delta_records(root)
        if failures:
            print("delta log is not valid:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        if args.lane:
            records = [r for r in records if r.get("lane") == args.lane]
        limit = max(int(args.limit or 20), 0)
        rows = records[-limit:] if limit else records
        if not rows:
            print("no evidence deltas")
            return 0
        for record in rows:
            print(
                f"{record.get('delta_id')} lane={record.get('lane')} "
                f"sufficiency={record.get('sufficiency_for_current_purpose')} "
                f"summary={record.get('summary')}"
            )
        return 0
    raise ValueError(f"unknown delta command: {args.delta_command}")



def _cmd_paper_ci(args: argparse.Namespace) -> int:
    root = _project_root()
    if args.paper_ci_command == "register-result":
        try:
            path, record = register_payload_file(root, Path(args.record), dry_run=args.dry_run)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"FAIL: {exc}")
            return 1
        action = "would register" if args.dry_run else "registered"
        print(f"{action} result {record.result_id} -> {path.relative_to(root)}")
        print(f"spec_id: {record.spec_id}")
        print(f"eligibility: {record.claim_type_eligibility}")
        return 0
    if args.paper_ci_command == "sync-result-index":
        path, count = sync_result_index(root, dry_run=args.dry_run)
        action = "would sync" if args.dry_run else "synced"
        print(f"{action} {count} result registry row(s) -> {path.relative_to(root)}")
        # Keep the provenance layer in lockstep so a registered result does not
        # trip check_provenance / check_gate_exit for a missing provenance JSON.
        if not args.dry_run and not args.no_provenance:
            from .runtime.provenance import sync_provenance
            written, skipped = sync_provenance(root)
            print(f"provenance synced: {len(written)} record(s) -> outputs/.provenance/")
            for message in skipped:
                print(f"  provenance skipped: {message}")
        return 0
    if args.paper_ci_command == "schema":
        print("Phase 0 result registry schema:")
        print("  template: templates/result_registry_record.json")
        print("  contract: harness/result_adapter_contract.yml")
        print("  registry: evidence/result_registry.csv")
        print("Adapters should introspect fit objects; manual prose is not ground truth.")
        return 0
    print("unknown paper-ci command")
    return 2


def _cmd_init(args: argparse.Namespace) -> int:
    root = init_project(args.path, force=args.force)
    print(f"initialized AEROS project at {root}")
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    root = _project_root()
    return run_adoption(root, AdoptionArgs(
        idea=args.idea or "",
        source="",
        target=args.target or "",
        mode=args.mode,
        dry_run=args.dry_run,
        deep=not args.no_deep,
    ))


def _cmd_adopt(args: argparse.Namespace) -> int:
    root = _project_root()
    return run_adoption(root, AdoptionArgs(
        idea=args.idea or "",
        source=args.source or "",
        target=args.target or "",
        mode=args.mode,
        dry_run=args.dry_run,
        deep=not args.no_deep,
    ))


def _cmd_check(args: argparse.Namespace) -> int:
    root = _project_root()
    if getattr(args, "profile", ""):
        cmd = [
            sys.executable,
            "checks/run_harness_checks.py",
            "--profile",
            args.profile,
        ]
        if getattr(args, "timeout", None) is not None:
            cmd.extend(["--timeout", str(args.timeout)])
        return subprocess.call(cmd, cwd=root)
    if not args.contract:
        print("FAIL: provide a task contract, or use `aeros check --profile smoke`")
        return 2
    contract_path = Path(args.contract)
    contract = load_contract(contract_path)
    root = find_project_root(contract_path.resolve())
    passed, results = run_checks(root, contract.checks)
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.name}")
        for f in r.failures:
            print(f"      - {f}")
    print("OK" if passed else "FAILED")
    return 0 if passed else 1


def _resolve_contract(root: Path, task_or_contract: str):
    candidate = Path(task_or_contract)
    if candidate.exists():
        contract = load_contract(candidate)
        return contract, candidate
    contracts = discover_contracts(root)
    if task_or_contract not in contracts:
        known = ", ".join(sorted(contracts)) or "(none)"
        raise KeyError(f"unknown task_id {task_or_contract!r}; known tasks: {known}")
    return contracts[task_or_contract]


def _latest_pending_prompt(root: Path, task_id: str) -> Path | None:
    pending_dir = root / "outputs" / "pending_tasks"
    matches = sorted(pending_dir.glob(f"{task_id}_*.md")) if pending_dir.exists() else []
    return matches[-1] if matches else None


def _cmd_recover(args: argparse.Namespace) -> int:
    root = _project_root()
    try:
        contract, path = _resolve_contract(root, args.task)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    prompt = _latest_pending_prompt(root, contract.task_id)
    if prompt:
        print(f"latest pending prompt: {prompt.relative_to(root)}")
    else:
        print("latest pending prompt: (none found)")

    if not args.check:
        print("REFUSED: recover requires --check so state only advances after mechanical checks pass")
        return 2

    passed, results = run_checks(root, contract.checks)
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'}  {result.name}")
        for failure in result.failures:
            print(f"      - {failure}")
    if not passed:
        print(f"FAILED: {contract.task_id} was not recovered; fix artifacts and rerun recover --check")
        return 1

    from .runtime.completion import write_completion_receipt
    from .runtime.skill_receipt import write_skill_invocation_receipt
    state = load_state(root)
    all_contracts = discover_contracts(root)
    _record_task_fingerprints(state, contract, root, all_contracts)
    entry = state["tasks"].setdefault(contract.task_id, {})
    receipt = write_completion_receipt(
        root,
        contract,
        mode="manual_recover",
        check_results=results,
        skill_receipt_path=write_skill_invocation_receipt(root, contract, skills_used=[], run_report_path=None),
        input_fingerprint=entry.get("input_fingerprint", ""),
        output_fingerprint=entry.get("output_fingerprint", ""),
        dependency_fingerprint=entry.get("dependency_fingerprint", ""),
    )
    if not receipt.passed:
        print(f"FAILED: {contract.task_id} cannot be recovered; completion receipt failed")
        for failure in receipt.failures:
            print(f"      - {failure}")
        return 2
    set_status(state, contract.task_id, "passed")
    recompute_candidate_gate(state, _task_gates(all_contracts))
    record_run_summary(state, contract.task_id, calls=0, cost_usd=0.0)
    save_state(root, state)
    print(f"recovered {contract.task_id} from {_display_rel(path, root)}")
    print(f"completion receipt: {receipt.path.relative_to(root)}")
    print(f"candidate: {state.get('candidate_stage', '?')} / {state.get('candidate_gate', '?')}")
    print("gate was not approved automatically")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    root = _project_root()
    if args.simple:
        print(format_simple_status(root))
        return 0
    state = load_state(root)
    print(f"project root : {root}")
    print(f"current stage: {state.get('current_stage', '?')}")
    print(f"current gate : {state.get('current_gate', '?')}")
    print(f"gate status  : {state.get('gate_status', 'open')}")
    print(f"candidate   : {state.get('candidate_stage', '?')} / {state.get('candidate_gate', '?')}")
    history = state.get("gate_history", [])
    if history:
        last = history[-1]
        print(f"last gate move: {last.get('gate', '?')} via {last.get('task_id', '?')}"
              f" ({last.get('reason', '?')})")
    tasks = state.get("tasks", {})
    if not tasks:
        print("tasks        : (none run yet)")
        return 0
    print("tasks:")
    for task_id, entry in tasks.items():
        print(f"  - {task_id:32s} status={entry.get('status','?'):10s} "
              f"last_run={entry.get('last_run_calls',0)} call(s)/"
              f"${entry.get('last_run_cost_usd',0.0):.4f}  "
              f"cumulative={entry.get('agent_calls_total',0)} call(s)/"
              f"${entry.get('cost_usd_total',0.0):.4f}")
    return 0


def _cmd_context(args: argparse.Namespace) -> int:
    root = _project_root()
    bundle = build_context_bundle(root, lane=args.lane or "project", brief=args.brief)
    if args.stale:
        stale = bundle.get("context_staleness") or {}
        print(f"context_stale: {stale.get('stale', False)}")
        print(f"status: {stale.get('status', 'unknown')}")
        print(f"message: {stale.get('message', '')}")
        changed = stale.get("changed_sources") or []
        if changed:
            print("changed_sources:")
            for rel in changed:
                print(f"  - {rel}")
        return 1 if stale.get("stale") else 0
    if args.json:
        print(json.dumps(bundle, indent=2, ensure_ascii=False))
    else:
        print(format_context_bundle(bundle, brief=args.brief))
    if args.write:
        md_path, json_path = write_context_bundle(root, bundle)
        print(f"wrote {md_path.relative_to(root)}")
        print(f"wrote {json_path.relative_to(root)}")
    return 0


def _cmd_next(args: argparse.Namespace) -> int:
    root = _project_root()
    action = compute_next_action(root, lane=args.lane or "")
    if args.json:
        print(json.dumps(action.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_next_action(action))
    if args.write:
        path = write_next_action(root, action)
        print(f"wrote {path.relative_to(root)}")
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    root = _project_root()
    decision = str(args.decision).strip(); campaign_id = str(args.campaign_id).strip()
    authority = str(args.authority_evidence).strip()
    if authority == "external_human_approval":
        print("approval rejected: external_human_approval has no configured independent verifier")
        return 2
    path = root / "decisions/approvals" / f"campaign_{campaign_id}_{decision}.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1, "campaign_id": campaign_id, "decision": decision,
        "reason": args.reason, "breaker_id": args.breaker,
        "expires_after_tasks": int(args.for_tasks),
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision_ref": args.decision_ref, "authority_evidence": authority,
        "authority_scope": {"campaign_continuation_only": decision == "continue", "campaign_stop_only": decision == "stop"},
        "does_not_authorize": ["canonical promotion", "claim upgrade", "release"],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"wrote scoped approval artifact: {_display_rel(path, root)}")
    if not args.commit:
        print("authority not granted: artifact is uncommitted; review it and rerun with --commit")
        return 0
    staged = subprocess.run(["git", "-C", str(root), "diff", "--cached", "--name-only"], text=True, capture_output=True)
    if staged.stdout.strip():
        print("approval commit refused: unrelated staged files exist")
        return 2
    env = dict(os.environ); env["AEROS_ALLOW_PROTECTED_COMMIT"] = "1"
    if subprocess.run(["git", "-C", str(root), "add", str(path.relative_to(root))], env=env).returncode != 0:
        return 2
    commit_args = ["git", "-C", str(root), "commit"]
    if authority == "signed_commit": commit_args.append("-S")
    commit_args.extend(["-m", f"approve campaign {campaign_id} {decision}", "--", str(path.relative_to(root))])
    result = subprocess.run(commit_args, env=env)
    if result.returncode != 0: return result.returncode
    print(f"authority granted at level={authority}; run: aeros campaign {decision} --approval {path.relative_to(root)}")
    return 0


def _cmd_authority_bootstrap(args: argparse.Namespace) -> int:
    """Interactive TOFU ceremony for the first project signer."""
    root = _project_root()
    public_path = Path(args.ssh_public_key).expanduser()
    if not public_path.exists():
        print(f"REFUSED: SSH public key does not exist: {public_path}")
        return 2
    if not sys.stdin.isatty():
        print("REFUSED: authority bootstrap requires an interactive terminal fingerprint comparison.")
        print("This is a TOFU ceremony, not an agent-automatable approval step.")
        return 3
    fingerprint_result = subprocess.run(
        ["ssh-keygen", "-lf", str(public_path), "-E", "sha256"],
        text=True, capture_output=True, timeout=20,
    )
    if fingerprint_result.returncode != 0:
        print("REFUSED: unable to fingerprint SSH public key")
        return 2
    parts = fingerprint_result.stdout.split()
    fingerprint = parts[1] if len(parts) > 1 else ""
    print("AEROS first-signer trust bootstrap (TOFU)")
    print(f"identity:    {args.identity}")
    print(f"principal:   {args.principal}")
    print(f"fingerprint: {fingerprint}")
    print("This records a locally confirmed key; it does not independently prove real-world identity.")
    typed = input("Type the complete fingerprint to trust this key: ").strip()
    from .runtime.authority import bootstrap_ssh_signer
    try:
        policy, confirmed = bootstrap_ssh_signer(
            root, identity=args.identity, principal=args.principal,
            public_key=public_path.read_text(encoding="utf-8"), confirmed_fingerprint=typed,
        )
    except (PermissionError, ValueError) as exc:
        print(f"REFUSED: {exc}")
        return 3
    print(f"wrote bootstrap record: {policy.relative_to(root)} ({confirmed})")
    if not args.commit:
        print("NOT ACTIVE: sign and commit harness/permissions.yml before authority can be consumed.")
        return 0
    committed = subprocess.run(
        ["git", "-C", str(root), "add", "harness/permissions.yml"],
        text=True, capture_output=True,
    )
    if committed.returncode == 0:
        committed = subprocess.run(
            ["git", "-C", str(root), "commit", "-S", "-m", "bootstrap AEROS authority signer"],
            text=True, capture_output=True,
        )
    if committed.returncode != 0:
        print(f"REFUSED: signed bootstrap commit failed: {(committed.stderr or committed.stdout).strip()}")
        return 4
    print("ACTIVE: first signer policy was committed with a signature; later changes require the prior signer.")
    return 0


def _cmd_job(args: argparse.Namespace) -> int:
    from .runtime.research_job import load_research_job, compile_research_job, validate_compilation, write_compiled_job
    root = _project_root(); compiled = compile_research_job(load_research_job(Path(args.file)))
    failures = validate_compilation(compiled)
    if failures: print(json.dumps({"status":"invalid","failures":failures}, indent=2)); return 2
    if args.write:
        for path in write_compiled_job(root, compiled): print(f"wrote {_display_rel(path, root)}")
    else: print(json.dumps(compiled.to_dict(), indent=2))
    return 0


def _cmd_adaptive_checks(args: argparse.Namespace) -> int:
    from .runtime.adaptive_checks import assess_post_action, changed_paths, select_checks
    root = _project_root()
    paths = list(args.changed or []) or changed_paths(root)
    if args.action_exit is None and not args.expected_output:
        report = select_checks(root, paths)
        print(json.dumps(report, indent=2))
        return 0
    report = assess_post_action(
        root,
        paths,
        action_exit_code=args.action_exit,
        expected_outputs=list(args.expected_output or []),
    )
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


def _cmd_migrate(args: argparse.Namespace) -> int:
    from .runtime.devendor import inspect_migration, prepare_package_mode
    root = _project_root()
    if args.migrate_command == "inspect": print(json.dumps(inspect_migration(root), indent=2)); return 0
    config, lock = prepare_package_mode(root, policy_bundle_version=args.policy_bundle_version)
    print(f"wrote {_display_rel(config, root)}\nwrote {_display_rel(lock, root)}")
    print("no vendored runtime files were deleted; run `aeros doctor` from the installed package before removal")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    from .runtime.devendor import doctor_package_mode
    report = doctor_package_mode(_project_root())
    print(json.dumps(report, indent=2) if args.json else f"status: {report['status']}\n" + "\n".join(report.get("failures") or ["package lock matches installed runtime"]))
    return 0 if report["status"] == "PASS" else 1


def _cmd_campaign(args: argparse.Namespace) -> int:
    from .runtime.campaign import assess_campaign, format_campaign_assessment, write_campaign_assessment

    root = _project_root()
    command = getattr(args, "campaign_command", "assess")

    if command == "new":
        from pathlib import Path as _Path
        target = root / (getattr(args, "path", "") or "campaigns/active_campaign.yml")
        if target.exists() and not getattr(args, "force", False):
            print(f"campaign contract already exists: {target.relative_to(root)} (use --force to overwrite)")
            return 1
        template = _Path(__file__).resolve().parents[1] / "templates" / "campaign_contract.yml"
        if not template.is_file():
            print("templates/campaign_contract.yml not found")
            return 1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"wrote {target.relative_to(root)} — edit campaign_id, work_lane, objective_*, task_budget before use")
        return 0

    if command in {"continue", "stop"}:
        from .runtime.campaign import record_campaign_decision
        try:
            rec = record_campaign_decision(
                root,
                decision=command,
                approval_artifact=getattr(args, "approval", "") or "",
            )
        except (PermissionError, ValueError) as exc:
            print(f"campaign {command} rejected: {exc}")
            return 2
        print(f"recorded {command} decision for campaign '{rec['campaign_id']}' at progress {rec['recorded_at_progress']}")
        if command == "continue":
            print(f"  releases breaker '{rec['breaker_id']}' for the next {rec['expires_after_tasks']} task(s), then re-review")
        print("  this is a human decision record; it does not certify scientific validity or approve gates")
        return 0

    report = assess_campaign(
        root,
        contract_path=getattr(args, "contract", "") or None,
        progress_path=getattr(args, "progress", "") or None,
        campaign_id=getattr(args, "campaign_id", "") or "",
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_campaign_assessment(report))
    if getattr(args, "write", False):
        md, js = write_campaign_assessment(root, report)
        print(f"wrote {md.relative_to(root)}")
        print(f"wrote {js.relative_to(root)}")
    return 0


def _cmd_drive(args: argparse.Namespace) -> int:
    from .runtime.drive import build_drive_report, format_drive_report, write_drive_report

    root = _project_root()
    report = build_drive_report(
        root,
        goal=getattr(args, "goal", "auto") or "auto",
        lane=getattr(args, "lane", "") or "",
        execute=bool(getattr(args, "execute", False)),
        job=getattr(args, "job", "") or "",
        source_candidate=getattr(args, "source_candidate", "") or "",
        target=getattr(args, "target", "") or "",
        include_history=not bool(getattr(args, "no_history", False)),
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_drive_report(report))
    if getattr(args, "write", False):
        md, js = write_drive_report(root, report)
        print(f"wrote {md.relative_to(root)}")
        print(f"wrote {js.relative_to(root)}")
    execution = report.get("execution") or {}
    if execution.get("attempted") and execution.get("status") == "fail":
        return 1
    return 0


def _cmd_econ(args: argparse.Namespace) -> int:
    from .runtime.econ_pack import (
        build_literature_radar, build_skill_scorecard, compile_protocol,
        initialize_registries, validate_object_chain, write_literature_radar,
    )
    root = _project_root()
    if args.econ_command == "init":
        payload = {"created_or_present": [str(p.relative_to(root)) for p in initialize_registries(root)]}
    elif args.econ_command == "chain":
        payload = validate_object_chain(root)
    elif args.econ_command == "protocol":
        payload = compile_protocol(args.name, spec_id=args.spec_id)
    elif args.econ_command == "literature-radar":
        payload = build_literature_radar(root)
        if args.write: payload["written_to"] = str(write_literature_radar(root, payload).relative_to(root))
    elif args.econ_command == "skill-scorecard":
        payload = build_skill_scorecard(root)
    else:
        raise SystemExit(f"unknown econ command: {args.econ_command}")
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return 0 if payload.get("status") != "FAIL" else 1


def _cmd_submit(args: argparse.Namespace) -> int:
    if getattr(args, "submit_action", "readiness") == "fact-check":
        from .runtime.grounded_fact_check import build_grounded_fact_check, write_grounded_fact_check
        root = _project_root()
        payload = build_grounded_fact_check(
            root,
            manuscript=args.manuscript,
            allow_network=args.allow_network,
        )
        if args.write:
            payload["written_to"] = write_grounded_fact_check(root, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
        if payload["status"] == "FAIL":
            return 1
        return 2 if payload["status"] == "BLOCKED" else 0
    from .runtime.econ_pack import submission_review_ready
    from .runtime.paper_readiness import assess_paper_readiness
    from .runtime.submission_driver import build_submission_driver
    root = _project_root()
    driver = build_submission_driver(root)
    readiness = assess_paper_readiness(root).to_dict()
    payload = {
        "model": "AEROS-SUBMIT-001", "submission_driver": driver,
        "paper_readiness": readiness,
        "ready_for_human_review": submission_review_ready(driver, readiness),
        "authority": "advisory; mechanical readiness may enter human review but does not approve paper readiness or release",
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return 0 if payload["ready_for_human_review"] else 2


def _cmd_home(args: argparse.Namespace) -> int:
    from .runtime.drive import build_drive_report
    report = build_drive_report(_project_root())
    objective = report.get("chosen_objective") or {}
    print("AEROS\n")
    print("RUN NOW")
    print(f"  {objective.get('objective', 'Inspect project state')}")
    print(f"  command: {objective.get('command', 'aeros drive')}")
    print("\nNEED YOU")
    print("  " + ("Human decision required for the selected action." if objective.get("needs_human") else "No immediate human decision."))
    print("\nPRIMARY COMMANDS")
    print("  aeros drive [--job JOB]   choose/run bounded research work")
    print("  aeros submit              submission/readiness projection")
    print("  aeros --help              advanced/debug commands")
    return 0


def _cmd_claim_vector(args: argparse.Namespace) -> int:
    from .runtime.claim_vector import compile_claim_vector, format_claim_vector

    if args.claim_vector_command == "compile":
        vector = compile_claim_vector(
            claim_id=args.claim_id,
            evidence_status=args.evidence_status,
            identification_level=args.identification_level,
            result_admission_status=args.result_admission_status,
            validation_status=args.validation_status,
        )
        if args.json:
            print(json.dumps(vector.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_claim_vector(vector))
        return 0
    raise SystemExit(f"unknown claim-vector command: {args.claim_vector_command}")


def _cmd_journal(args: argparse.Namespace) -> int:
    from .runtime.sqlite_journal import build_sqlite_journal, format_journal_report

    root = _project_root()
    if args.journal_command == "build":
        output = Path(args.output) if args.output else None
        report = build_sqlite_journal(root, output, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_journal_report(report))
        return 0
    raise SystemExit(f"unknown journal command: {args.journal_command}")


def _cmd_claim_upgrade(args: argparse.Namespace) -> int:
    from .runtime.claim_upgrade import format_claim_upgrade_review, review_claim_upgrade, write_claim_upgrade_review

    root = _project_root()
    if args.claim_upgrade_command == "review":
        review = review_claim_upgrade(
            root,
            claim_id=args.claim_id,
            evidence_status=args.evidence_status,
            identification_level=args.identification_level,
            result_admission_status=args.result_admission_status,
            validation_status=args.validation_status,
        )
        if args.json:
            print(json.dumps(review.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_claim_upgrade_review(review))
        if args.write:
            path = write_claim_upgrade_review(root, review)
            print(f"wrote {path.relative_to(root)}")
        return 0
    raise SystemExit(f"unknown claim-upgrade command: {args.claim_upgrade_command}")


def _cmd_paper_readiness(args: argparse.Namespace) -> int:
    from .runtime.paper_readiness import (
        assess_paper_readiness,
        format_paper_readiness_report,
        write_paper_readiness_report,
    )

    root = _project_root()
    if args.paper_readiness_command == "report":
        report = assess_paper_readiness(root)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_paper_readiness_report(report))
        if args.write:
            path = write_paper_readiness_report(root, report)
            print(f"wrote {path.relative_to(root)}")
        return 0
    raise SystemExit(f"unknown paper-readiness command: {args.paper_readiness_command}")



def _cmd_driver(args: argparse.Namespace) -> int:
    from .runtime.submission_driver import build_submission_driver, format_submission_driver, write_submission_driver

    root = _project_root()
    if args.driver_command == "submission":
        report = build_submission_driver(root)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(format_submission_driver(report))
        if args.write:
            paths = write_submission_driver(root, report)
            for path in paths:
                print(f"wrote {path.relative_to(root)}")
        return 0 if report.get("status") in {"pass", "inactive"} else 1
    print("unknown driver command")
    return 2


def _cmd_stale(args: argparse.Namespace) -> int:
    root = _project_root()
    if args.stale_command == "triage":
        result = triage_stale_tasks(root, stage=args.stage, lane=args.lane or "")
        if args.json:
            print(stale_triage_json(result))
        else:
            print(format_stale_triage(result))
        if args.write and not args.dry_run:
            md_path, json_path = write_stale_triage(root, result)
            print(f"wrote {md_path.relative_to(root)}")
            print(f"wrote {json_path.relative_to(root)}")
        elif args.write and args.dry_run:
            print("dry-run: stale triage artifacts not written")
        return 0
    print("unknown stale command")
    return 2


def _cmd_session(args: argparse.Namespace) -> int:
    from .runtime.session_guard import (
        audit_session,
        format_audit,
        format_session_status,
        load_session,
        start_session,
    )

    root = _project_root()
    if args.session_command == "start":
        path, payload = start_session(
            root,
            lane=args.lane,
            objective=args.objective,
            workflow=args.workflow,
            max_actions=args.max_actions,
            allowed_actions=args.allowed_action or None,
            dry_run=args.dry_run,
        )
        action = "would write" if args.dry_run else "wrote"
        print(f"{action} session contract: {path.relative_to(root)}")
        print(format_session_status(payload))
        return 0
    if args.session_command == "status":
        print(format_session_status(load_session(root)))
        return 0
    if args.session_command == "audit":
        audit = audit_session(root)
        print(format_audit(audit, as_json=args.json))
        return 0 if audit.ok else 1
    print("unknown session command")
    return 2


def _cmd_state_prune(args: argparse.Namespace) -> int:
    root = _project_root()
    state = load_state(root)
    contracts = discover_contracts(root)
    tasks = state.get("tasks", {})
    stale_task_ids = sorted(task_id for task_id in tasks if task_id not in contracts)
    if not stale_task_ids:
        print("no stale task state entries found")
        return 0
    print("stale task state entries:")
    for task_id in stale_task_ids:
        print(f"  - {task_id}")
    if args.dry_run:
        print("dry-run: state not modified")
        return 0
    for task_id in stale_task_ids:
        tasks.pop(task_id, None)
    recompute_candidate_gate(state, _task_gates(contracts))
    save_state(root, state)
    print(f"pruned {len(stale_task_ids)} stale task state entr{'y' if len(stale_task_ids) == 1 else 'ies'}")
    print(f"candidate: {state.get('candidate_stage', '?')} / {state.get('candidate_gate', '?')}")
    return 0


def _append_decision_log(root: Path, decision: dict[str, str]) -> Path:
    path = root / "decisions" / "decision_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "Date",
        "Decision ID",
        "Task ID",
        "Agent Recommendation",
        "Critic Verdict",
        "Human Decision",
        "Rationale",
        "Owner",
        "Follow-up",
    ]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists or path.stat().st_size == 0:
            writer.writeheader()
        decision_id = f"{decision['gate']}-{decision['decision']}-{decision['at']}"
        writer.writerow(
            {
                "Date": decision["at"],
                "Decision ID": decision_id,
                "Task ID": "human_gate",
                "Agent Recommendation": "",
                "Critic Verdict": "",
                "Human Decision": f"{decision['decision']} {decision['gate']}",
                "Rationale": decision.get("note", ""),
                "Owner": decision.get("owner", ""),
                "Follow-up": "",
            }
        )
    return path


def _cmd_state_global(args: argparse.Namespace) -> int:
    root = _project_root()
    path, payload = write_global_state(root, dry_run=args.dry_run)
    action = "would write" if args.dry_run else "wrote"
    print(f"{action} global state: {path.relative_to(root)}")
    print(f"datasets: {len(payload.get('datasets', {}))}")
    print(f"claims: {payload.get('claims', {}).get('count', 0)}")
    print(f"results: {payload.get('results', {}).get('rows', 0)}")
    return 0


def _cmd_readiness(args: argparse.Namespace) -> int:
    from .runtime.readiness import build_readiness_vector, format_readiness_vector

    root = _project_root()
    vector = build_readiness_vector(root)
    if args.json:
        print(json.dumps(vector, indent=2, ensure_ascii=False))
    else:
        print(format_readiness_vector(vector))
    return 0


def _cmd_reconcile(args: argparse.Namespace) -> int:
    from .runtime.reconcile import format_reconcile_report, run_reconcile, write_reconcile_report

    root = _project_root()
    report = run_reconcile(
        root,
        dry_run=args.dry_run,
        timeout_seconds=args.timeout,
        skip_result_index=args.skip_result_index,
        skip_provenance=args.skip_provenance,
        skip_graph=args.skip_graph,
        skip_state=args.skip_state,
        include_context=args.include_context,
    )
    print(format_reconcile_report(report))
    if not args.dry_run and not args.no_report:
        path = write_reconcile_report(root, report)
        print(f"wrote reconcile report: {path.relative_to(root)}")
    return 0 if report.ok else 1


def _cmd_gate_status(args: argparse.Namespace) -> int:
    root = _project_root()
    state = load_state(root)
    print(f"current stage: {state.get('current_stage', '?')}")
    print(f"current gate : {state.get('current_gate', '?')}")
    print(f"gate status  : {state.get('gate_status', 'open')}")
    print(f"candidate   : {state.get('candidate_stage', '?')} / {state.get('candidate_gate', '?')}")
    decisions = state.get("gate_decisions", [])
    if decisions:
        last = decisions[-1]
        print(f"last decision: {last.get('decision')} {last.get('gate')} "
              f"by {last.get('owner') or '?'}")
        if last.get("note"):
            print(f"note         : {last.get('note')}")
    return 0


def _cmd_gate_history(args: argparse.Namespace) -> int:
    root = _project_root()
    state = load_state(root)
    history = state.get("gate_history", [])
    if not history:
        print("no gate history recorded")
        return 0
    limit = args.limit or len(history)
    for row in history[-limit:]:
        print(f"{row.get('at')}  {row.get('stage')}  {row.get('gate')}  "
              f"{row.get('task_id')}  {row.get('reason')}")
    return 0


def _cmd_gate_request(args: argparse.Namespace) -> int:
    """Agent-writable approval REQUEST. Does not grant anything until an approver
    commits the artifact under an approved git identity."""
    root = _project_root()
    artifact = identity.write_approval_request(
        root, gate=args.gate, stage=args.stage,
        requested_by=args.owner or "agent", note=args.note or "",
    )
    print(f"wrote approval request: {artifact.relative_to(root)}")
    print("This is a REQUEST, not a grant. An approver must commit it (see the file).")
    return 0


def _seed_plan_cards(root: Path, gate: str) -> list:
    """Locked anchor cards (cannot be dropped) + agent proposal cards from the
    pending tasks at this gate."""
    from .runtime.plan_deck import Card
    cards: list = []
    anchor_path = root / "discovery" / "anchor.yml"
    if anchor_path.exists():
        data = yaml.safe_load(anchor_path.read_text(encoding="utf-8")) or {}
        anchor = data.get("anchor", data) if isinstance(data, dict) else {}
        for i, comp in enumerate(["topic", "claim_type", "identification", "data"], 1):
            val = str(anchor.get(comp, "")).strip() or "(unset)"
            cards.append(Card(id=f"A{i}", title=f"Anchor: {comp} = {val}", source="intake", locked=True))
    slug = identity.gate_slug(gate)
    try:
        contracts = discover_contracts(root)
        for tid, (contract, _path) in sorted(contracts.items()):
            if identity.gate_slug(contract.gate or "") == slug:
                cards.append(Card(id=tid, title=f"Run task {tid}: {contract.goal[:80]}", source="agent"))
    except Exception:  # noqa: BLE001
        pass
    if not any(c.source == "agent" for c in cards):
        from .runtime.plan_deck import Card as _C
        cards.append(_C(id="P1", title=f"(edit) proposed action for {gate}", source="agent"))
    return cards


def _cmd_gate_plan(args: argparse.Namespace) -> int:
    """PLAN phase: write a proposal deck (text only, no execution)."""
    from .runtime.plan_deck import Deck, write_deck
    root = _project_root()
    deck = Deck(gate=args.gate, stage=args.stage, cards=_seed_plan_cards(root, args.gate))
    path = write_deck(root, deck)
    print(f"wrote plan deck: {path.relative_to(root)}")
    print(f"  {len(deck.cards)} card(s); locked anchor cards cannot be dropped.")
    print("Nothing executed. Edit the deck, then (as approver): git commit it and run:")
    print(f"  aeros gate apply \"{args.gate}\" --stage \"{args.stage}\"")
    return 0


def _cmd_gate_apply(args: argparse.Namespace) -> int:
    """APPLY phase: a committed, valid plan deck grants the gate and lets the loop proceed."""
    from .runtime.plan_deck import deck_path, parse_deck, validate_applied, kept_cards
    root = _project_root()
    path = deck_path(root, args.gate)
    if not path.exists():
        print(f"REFUSED: no plan deck at {path.relative_to(root)}. Run `aeros gate plan` first.")
        return 2

    # 1. Deck must carry authority meeting the gate-apply floor. --force may
    # override scientific criteria, never the authority boundary.
    from .runtime.authority import evaluate_for_action
    authority = evaluate_for_action(root, path, "gate_apply")
    if not authority.granted:
        print(f"REFUSED: plan deck lacks required authority ({authority.reason}).")
        return 3

    # 2. Deck semantics: no dropped locked card, at least one kept card.
    deck = parse_deck(path)
    violations = validate_applied(deck)
    if violations and not args.force:
        print("REFUSED: plan deck is not valid to apply:")
        for v in violations:
            print(f"  - {v}")
        return 2

    # 3. Gate exit criteria still apply.
    checks_dir = root / "checks"
    if not (checks_dir / "check_gate_exit.py").exists():
        checks_dir = Path(__file__).resolve().parents[1] / "checks"
    sys.path.insert(0, str(checks_dir))
    os.environ["AEROS_CHECKS_DIR"] = str(checks_dir)
    try:
        from check_gate_exit import evaluate_through_gate  # noqa: E402
        ok, failures = evaluate_through_gate(args.gate, project_root=str(root))
    except Exception as exc:  # noqa: BLE001
        ok, failures = False, [f"could not evaluate gate criteria: {exc}"]
    if not ok and not args.force:
        print(f"REFUSED: {args.gate} exit criteria are NOT satisfied:")
        for f in failures:
            print(f"  - {f}")
        return 2

    kept = kept_cards(deck)
    note = f"[plan/apply] applied {len(kept)} kept card(s): " + ", ".join(c.id for c in kept)
    state = load_state(root)
    decision = approve_gate(state, stage=args.stage, gate=args.gate,
                            owner=args.owner or "approver", note=note)
    save_state(root, state)
    log_path = _append_decision_log(root, decision)
    print(f"APPLIED {args.gate}: {len(kept)} kept card(s). Gate advanced.")
    print(f"decision log: {log_path.relative_to(root)}")
    return 0


def _cmd_gate_approve(args: argparse.Namespace) -> int:
    root = _project_root()

    # A human gate is a stamp ON TOP of satisfied criteria, not instead of them.
    # Verify the gate's exit criteria before allowing approval.
    checks_dir = root / "checks"
    if not (checks_dir / "check_gate_exit.py").exists():
        checks_dir = Path(__file__).resolve().parents[1] / "checks"
    sys.path.insert(0, str(checks_dir))
    old_checks_dir = os.environ.get("AEROS_CHECKS_DIR")
    os.environ["AEROS_CHECKS_DIR"] = str(checks_dir)
    try:
        from check_gate_exit import evaluate_through_gate  # noqa: E402
        ok, failures = evaluate_through_gate(args.gate, project_root=str(root))
    except Exception as exc:  # noqa: BLE001
        ok, failures = False, [f"could not evaluate gate criteria: {exc}"]
    finally:
        if old_checks_dir is None:
            os.environ.pop("AEROS_CHECKS_DIR", None)
        else:
            os.environ["AEROS_CHECKS_DIR"] = old_checks_dir

    note = args.note or ""
    if not ok:
        if not args.force:
            print(f"REFUSED: {args.gate} exit criteria are NOT satisfied:")
            for f in failures:
                print(f"  - {f}")
            print("\nFix the criteria, or override with --force (the override is logged).")
            return 2
        note = f"[FORCED OVERRIDE despite {len(failures)} unmet criteria] " + note
        print(f"WARNING: forcing approval of {args.gate} despite {len(failures)} unmet criteria:")
        for f in failures:
            print(f"  - {f}")

    # Trust anchor: --force may override unmet criteria but never authority.
    approver_committer = ""
    artifact = identity.approval_artifact_path(root, args.gate)
    from .runtime.authority import evaluate_for_action
    authority = evaluate_for_action(root, artifact, "gate_approval")
    if not authority.granted:
        print(f"REFUSED: {args.gate} lacks required human authority ({authority.reason}).")
        print(f"  Create the request with: aeros gate request \"{args.gate}\"")
        print("  Then have a trusted signer sign and commit the approval artifact.")
        return 3
    approver_committer = authority.actor
    print(f"human authority verified: {authority.verification_method} ({authority.actor})")

    state = load_state(root)
    decision = approve_gate(
        state,
        stage=args.stage,
        gate=args.gate,
        owner=args.owner or approver_committer,
        note=note,
    )
    save_state(root, state)
    log_path = _append_decision_log(root, decision)
    if ok:
        print(f"approved {args.gate} for stage {args.stage} (criteria satisfied)")
    else:
        print(f"FORCE-approved {args.gate} for stage {args.stage} (criteria NOT satisfied — logged)")
    print(f"decision log: {log_path.relative_to(root)}")
    return 0


def _cmd_gate_block(args: argparse.Namespace) -> int:
    root = _project_root()
    state = load_state(root)
    decision = block_gate(
        state,
        stage=args.stage,
        gate=args.gate,
        owner=args.owner or "",
        reason=args.reason or "",
    )
    save_state(root, state)
    log_path = _append_decision_log(root, decision)
    print(f"blocked {args.gate} for stage {args.stage}")
    print(f"decision log: {log_path.relative_to(root)}")
    return 0


def _cmd_gate_packet(args: argparse.Namespace) -> int:
    root = _project_root()
    path = write_decision_packet(root, args.gate, stage=args.stage or "")
    print(f"decision packet: {path.relative_to(root)}")
    return 0


def _cmd_adjudicate(args: argparse.Namespace) -> int:
    root = _project_root()
    result = adjudicate(root)
    path = write_selection(root, result)
    sel = result["selected"]
    print(f"diagnostics: {result['diag_status']}")
    for e in sorted(result["evaluated"], key=lambda x: x["priority"]):
        print(f"  {'✓' if e['viable'] else '✗'} P{e['priority']} {e['id']} "
              f"({e['max_claim']}) — {e['reason']}")
    print(f"selected: {sel['id'] if sel else 'none'}  | "
          f"earned claim ceiling: {result['earned_claim'] or 'none'}")
    if result["ratcheted_from"]:
        print(f"ratcheted down from: {', '.join(result['ratcheted_from'])}")
    if result["diag_status"] != "measured":
        print("NOTE: diagnostics are STUB — no real claim earned until status: measured")
    print(f"wrote {path.relative_to(root)}")
    return 0


def _cmd_pipeline(args: argparse.Namespace) -> int:
    root = _project_root()
    rc = run_pipeline(root, args.stage, dry_run=args.dry_run,
                      task_timeout_override=args.task_timeout,
                      max_retries_override=args.max_retries)
    if rc != 0 or args.dry_run:
        return rc
    # after the stage runs, adjudicate designs and print the feasibility verdict
    print("[pipeline] adjudicating designs against data diagnostics...")
    write_selection(root, adjudicate(root))
    return _cmd_feasibility(args)


def _cmd_iterate(args: argparse.Namespace) -> int:
    root = _project_root()
    return run_iteration(
        root,
        args.stage,
        dry_run=args.dry_run,
        to_next_gate=args.to_next_gate,
        task_timeout_override=args.task_timeout,
        max_retries_override=args.max_retries,
        lane=args.lane,
    )


def _cmd_skills_plan(args: argparse.Namespace) -> int:
    root = _project_root()
    contracts = discover_contracts(root, None if args.stage == "all" else args.stage)
    if not contracts:
        print(f"No task contracts found for stage={args.stage}")
        return 0
    print(f"AEROS Skill Plan (stage={args.stage})")
    print("--------------------------------")
    for task_id in topo_order(contracts):
        contract, _path = contracts[task_id]
        route = skill_route(root, contract)
        print(
            f"- {task_id}: gate={contract.gate or '?'} "
            f"stage={route['inferred_skill_stage'] or 'n/a'} {format_skill_hint(root, contract)}"
        )
    return 0


def _cmd_collect(args: argparse.Namespace) -> int:
    root = _project_root()
    config = resolve_config(
        root,
        provider=args.provider,
        model=args.model,
        max_cost_usd=args.max_cost_usd,
        max_retries=args.max_retries,
        timeout_seconds=args.timeout,
        rate_limit_seconds=args.rate_limit_seconds,
    )
    try:
        return collect_prompt_grid(
            root,
            grid=(root / args.grid),
            out=(root / args.out),
            report=(root / args.report),
            config=config,
            dry_run=args.dry_run,
            max_rows=args.max_rows,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: collection failed: {exc}")
        return 1


def _cmd_action_receipt(args: argparse.Namespace) -> int:
    root = _project_root()
    data_impact = {
        "inventory_changed": args.inventory_changed,
        "source_verified": args.source_verified,
        "data_rows_changed": args.data_rows_changed,
        "coverage_changed": args.coverage_changed,
        "backfill_queue_changed": args.backfill_queue_changed,
        "probe_completed": args.probe_completed,
    }
    research_impact = {
        "claim_ceiling_changed": args.claim_ceiling_changed,
        "gate_candidate_changed": args.gate_candidate_changed,
        "evidence_graph_changed": args.evidence_graph_changed,
        "result_registered": args.result_registered,
    }
    path, _payload, failures = write_action_receipt(root, ActionReceiptArgs(
        action_id=args.action_id,
        action_mode=args.action_mode,
        progress_label=args.progress_label,
        summary=args.summary or "",
        why_this_now=args.why_this_now or "",
        evidence_paths=args.evidence_path or [],
        data_impact=data_impact,
        research_impact=research_impact,
        would_progress_without_this_action=args.would_progress_without_this_action,
        dependency_type=args.dependency_type or "",
        dry_run=args.dry_run,
    ))
    print(("would write" if args.dry_run else "wrote") + f" action receipt: {path.relative_to(root)}")
    if failures:
        print("receipt is not valid:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    return 0


def _cmd_literature(args: argparse.Namespace) -> int:
    root = _project_root()
    if args.literature_command == "status":
        print(format_literature_status(root))
        return 0
    if args.literature_command == "search":
        try:
            return run_literature_search(root, LiteratureSearchArgs(
                source=args.source,
                query=args.query or "",
                limit=args.limit,
                primary_function=args.primary_function,
                dry_run=args.dry_run,
                title=args.title or "",
                authors=args.authors or "",
                year=args.year or "",
                doi=args.doi or "",
                url=args.url or "",
                pdf_url=args.pdf_url or "",
                zotero_base_url=args.zotero_base_url or "http://127.0.0.1:23119",
            ))
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: literature adapter failed: {exc}")
            return 1
    print("unknown literature command")
    return 2


def _cmd_data(args: argparse.Namespace) -> int:
    root = _project_root()
    if args.data_command == "scan":
        return write_data_scan(root, dry_run=args.dry_run)
    if args.data_command == "gaps":
        return write_data_gaps(root, dry_run=args.dry_run)
    if args.data_command == "plan":
        print(format_data_first_plan(root))
        return 0
    if args.data_command == "probe":
        if args.data_probe_command == "official":
            from .runtime.economic_probe import run_official_probe
            try:
                payload = run_official_probe(root, series_id=args.series_id, contract_path=args.contract, api_key_env=args.api_key_env)
            except Exception as exc:
                payload = {"model": "AEROS-OFFICIAL-PROBE-001", "status": "FAIL", "error": str(exc), "next_action": "fix EconomicDataSeries contract, credentials, or official-source access and rerun"}
            print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
            return 0 if payload.get("status") == "PASS" else 2
        if args.data_probe_command == "census":
            from .runtime.census_probe import run_census_probe
            try:
                payload = run_census_probe(root, series_id=args.series_id, contract_path=args.contract, api_key_env=args.api_key_env)
            except Exception as exc:
                payload = {"model": "AEROS-CENSUS-PROBE-001", "status": "FAIL", "error": str(exc), "next_action": "fix Census EconomicDataSeries contract, credentials, or API access and rerun"}
            print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
            return 0 if payload.get("status") == "PASS" else 2
        if args.data_probe_command == "plan":
            return write_probe_plan(root, dry_run=args.dry_run)
        if args.data_probe_command == "run":
            return run_data_probe(root, args.source, limit=args.limit, dry_run=args.dry_run)
        if args.data_probe_command == "report":
            return write_probe_report(root, dry_run=args.dry_run)
    if args.data_command == "backfill":
        return _cmd_data_backfill(args)
    print("unknown data command")
    return 2


def _cmd_data_backfill(args: argparse.Namespace) -> int:
    root = _project_root()
    return run_data_backfill(root, BackfillArgs(
        dry_run=args.dry_run,
        run_local=args.run_local,
        approve=args.approve,
        receipt=args.receipt,
        owner=args.owner or "",
        source_snapshot=args.source_snapshot or "",
        note=args.note or "",
        coverage=args.coverage or "",
        disagreement_log=args.disagreement_log or "",
        human_decision=args.human_decision or "",
    ))



def _cmd_cockpit(args: argparse.Namespace) -> int:
    root = _project_root()
    cockpit = build_cockpit(root, lane=args.lane or "project", check_profile=args.profile)
    if args.json:
        print(json.dumps(cockpit, indent=2, ensure_ascii=False))
    else:
        print(format_cockpit(cockpit))
    if args.write:
        md_path, bundle_path, graph_path, control_tax_path = write_cockpit(root, lane=args.lane or "project", check_profile=args.profile)
        print(f"wrote {md_path.relative_to(root)}")
        print(f"wrote {bundle_path.relative_to(root)}")
        print(f"wrote {graph_path.relative_to(root)}")
        print(f"wrote {control_tax_path.relative_to(root)}")
    return 0


def _cmd_writes(args: argparse.Namespace) -> int:
    root = _project_root()
    if args.writes_command == "audit":
        report = audit_writes(
            root,
            since=args.since or "HEAD",
            declared_writes=args.declared_write or (),
            include_session=not args.no_session,
        )
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_write_audit(report))
        if args.write:
            md_path, json_path = write_write_audit(root, report)
            print(f"wrote {md_path.relative_to(root)}")
            print(f"wrote {json_path.relative_to(root)}")
        return 1 if args.strict and not report.ok else 0
    raise ValueError(f"unknown writes command: {args.writes_command}")

def _cmd_roadmap(args: argparse.Namespace) -> int:
    root = _project_root()
    print(format_roadmap(root))
    return 0


def _cmd_paper_render(args: argparse.Namespace) -> int:
    """Substitute {{name}} number tokens from paper/numbers.yml into a rendered copy."""
    from .runtime.number_injection import load_numbers, render_paper
    root = _project_root()
    src = root / (args.paper or "paper/draft.md")
    if not src.exists():
        print(f"REFUSED: paper source not found: {src.relative_to(root)}")
        return 2
    try:
        numbers = load_numbers(root)
    except ValueError as exc:
        print(f"REFUSED: {exc}")
        return 2
    rendered, unresolved = render_paper(src.read_text(encoding="utf-8"), numbers)
    if unresolved:
        print("REFUSED: unresolved number tokens (add them to paper/numbers.yml):")
        for name in sorted(set(unresolved)):
            print(f"  - {{{{{name}}}}}")
        return 2
    out = src.with_name(src.stem + ".rendered" + src.suffix)
    out.write_text(rendered, encoding="utf-8")
    print(f"rendered -> {out.relative_to(root)} ({len(numbers)} registered number(s))")
    print("Run `aeros check ...` / the gate to confirm every registered value traces to an artifact.")
    return 0


def _cmd_number_drift(args: argparse.Namespace) -> int:
    """Show (or accept) drift of injected numbers vs the lock file."""
    from .runtime.number_drift import (
        compute_drift, format_drift, record_acceptance, write_lock,
    )
    root = _project_root()
    drifts = compute_drift(root)
    moved = [d for d in drifts if d.moved]
    unresolved = [d for d in drifts if d.status == "unresolved"]
    print(format_drift(drifts, only_moved=not args.all))
    if args.update:
        if not args.owner:
            print("REFUSED: --update requires --owner -- a human must sign off on the "
                  "new values (they may invalidate the surrounding prose).")
            return 2
        if moved:
            log = record_acceptance(root, moved, args.owner, args.note or "")
            print(f"recorded {len(moved)} acceptance(s) by {args.owner} -> "
                  f"{log.relative_to(root)}")
        path = write_lock(root)
        print(f"lock updated -> {path.relative_to(root)} ({len(drifts)} cell(s))")
        return 0
    if unresolved:
        return 2
    return 1 if moved else 0


def _cmd_provenance(args: argparse.Namespace) -> int:
    """Sync the provenance layer to the result index (registration <-> provenance)."""
    from .runtime.provenance import sync_provenance
    root = _project_root()
    written, skipped = sync_provenance(root)
    for s in skipped:
        print(f"  skip: {s}")
    print(f"provenance synced: {len(written)} record(s) written to outputs/.provenance/")
    return 2 if skipped else 0


def _cmd_funnel(args: argparse.Namespace) -> int:
    from .runtime.funnel import new_funnel, select_champion
    root = _project_root()
    if args.funnel_command == "new":
        path = new_funnel(root, args.round, args.candidates, criterion=args.criterion or "")
        print(f"wrote funnel: {path.relative_to(root)} ({max(args.candidates, 2)} parallel candidate(s))")
        print("Edit candidates + selection_criterion, then: aeros funnel select ...")
        return 0
    if args.funnel_command == "select":
        path, problems = select_champion(root, args.round, args.champion, args.rationale or "")
        if problems:
            print("REFUSED: cannot select champion:")
            for p in problems:
                print(f"  - {p}")
            return 2
        print(f"champion {args.champion} selected in {path.relative_to(root)}; others pruned.")
        return 0
    print("unknown funnel command")
    return 2


def _cmd_manifest(args: argparse.Namespace) -> int:
    from .runtime.artifact_manifest import build_manifest, verify_manifest
    root = _project_root()
    if args.verify:
        problems = verify_manifest(root)
        if problems:
            print("DRIFT: registered artifacts changed since the manifest:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("OK: all manifested artifacts match their recorded SHA256")
        return 0
    path, n = build_manifest(root)
    print(f"wrote {path.relative_to(root)} ({n} artifact(s) hashed with sha256)")
    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    from .runtime.research_graph import (
        build_graph,
        format_coverage,
        format_impact,
        format_orphans,
        format_support,
        validate_graph,
    )
    root = _project_root()
    if args.graph_command == "build":
        path, graph, warnings = build_graph(root, write=not args.dry_run)
        action = "would write" if args.dry_run else "wrote"
        print(
            f"{action} {path.relative_to(root)} "
            f"({len(graph.get('nodes', []))} node(s), {len(graph.get('edges', []))} derived edge(s), "
            f"{len(graph.get('human_assertions', []))} human assertion(s))"
        )
        problems = validate_graph(root) if not args.dry_run else []
        for warning in warnings:
            print(f"WARNING: {warning}")
        if problems:
            print("WARNING: graph was built, but relationship problems remain:")
            for problem in problems:
                print(f"  - {problem}")
            print("Graph impact is observe-and-flag only; claim/gate status was not changed.")
            return 1
        return 0
    if args.graph_command == "query":
        if args.graph_query == "impact":
            print(format_impact(root, args.target))
            return 0
        if args.graph_query == "support":
            print(format_support(root, args.claim_id))
            return 0
        if args.graph_query == "coverage":
            print(format_coverage(root))
            return 0
        if args.graph_query == "orphans":
            print(format_orphans(root))
            return 0
    print("unknown graph command")
    return 2


def _cmd_feasibility(args: argparse.Namespace) -> int:
    root = _project_root()
    f = feasibility(root)
    print("G1-G3 feasibility (data ready AND variables buildable AND a viable design survives):")
    for g in ("G1", "G2", "G3"):
        ok, reason = f[g]
        print(f"  {'PASS' if ok else 'FAIL'}  {g}  {reason}")
    verdict = "FEASIBLE" if f["feasible"] else "NOT FEASIBLE (as designed)"
    print(f"verdict: {verdict}  | earned claim ceiling: {f['earned_claim'] or 'none'}"
          f"{' (PROVISIONAL — stub data)' if f['diag_status'] != 'measured' else ''}")
    return 0 if f["feasible"] else 1


def _cmd_list_tasks(args: argparse.Namespace) -> int:
    root = _project_root()
    tasks_dir = root / "tasks"
    found = sorted(tasks_dir.rglob("*.yml"))
    if not found:
        print(f"no .yml task contracts under {tasks_dir}")
        return 0
    for path in found:
        rel = path.relative_to(root)
        try:
            c = load_contract(path)
            print(f"{c.task_id:32s} stage={c.stage:12s} checks={len(c.checks)}  ({rel})")
        except Exception as exc:  # noqa: BLE001 - report, do not crash the listing
            print(f"{'(invalid)':32s} {rel}  -> {exc}")
    return 0


def _cmd_mode_recommend(args: argparse.Namespace) -> int:
    from .runtime.execution_mode import format_execution_mode, recommend_execution_mode

    report = recommend_execution_mode(
        _project_root(),
        lane=getattr(args, "lane", "") or "",
        intent=getattr(args, "intent", "") or "",
        mode=getattr(args, "mode", "") or "",
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_execution_mode(report))
    return 0 if report.get("status") in {"PASS", "ADVISORY"} else 1


def _cmd_mode_classify(args: argparse.Namespace) -> int:
    from .runtime.task_mode import format_task_mode, infer_task_mode

    report = infer_task_mode(
        _project_root(),
        task_id=getattr(args, "task_id", "") or "",
        lane=getattr(args, "lane", "") or "",
        intent=getattr(args, "intent", "") or "",
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_task_mode(report))
    return 0 if report.get("status") in {"PASS", "ADVISORY"} else 1


def _cmd_mode_compiled(args: argparse.Namespace) -> int:
    from .runtime.mode_compiler import compiled_mode_map, format_compiled_mode_map

    report = compiled_mode_map(_project_root())
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_compiled_mode_map(report))
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    if getattr(args, "inspect_command", "") == "modes" and getattr(args, "compiled", False):
        return _cmd_mode_compiled(args)
    print("usage: aeros inspect modes --compiled", file=sys.stderr)
    return 2


def _cmd_artifact_stage(args: argparse.Namespace) -> int:
    from .runtime.artifact_stage import format_artifact_stage_report, stage_canonical_artifacts

    report = stage_canonical_artifacts(
        _project_root(),
        apply=bool(getattr(args, "apply", False)),
        canonical=bool(getattr(args, "canonical", False)),
        exclude_raw_staging=bool(getattr(args, "exclude_raw_staging", False)),
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_artifact_stage_report(report))
    return 0 if report.get("status") == "PASS" else 1


def _cmd_improve_harvest(args: argparse.Namespace) -> int:
    from .runtime.improve_harvest import format_harvest, harvest_improvements

    report = harvest_improvements(_project_root(), project_roots=getattr(args, "project", None) or None)
    if getattr(args, "write", False):
        out = _project_root() / "outputs" / "context" / "improvement_harvest.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(format_harvest(report), encoding="utf-8")
        report["written_to"] = out.relative_to(_project_root()).as_posix()
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_harvest(report))
    return 0


def _cmd_sync_doctor(args: argparse.Namespace) -> int:
    from .runtime.sync_doctor import format_sync_doctor, sync_doctor

    report = sync_doctor(
        _project_root(),
        projects=getattr(args, "project", None) or None,
        template_root=getattr(args, "template_root", "") or None,
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_sync_doctor(report))
    return 0 if report.get("status") == "PASS" else 1


def _cmd_task_preflight(args: argparse.Namespace) -> int:
    from .runtime.task_preflight import build_task_preflight, format_task_preflight

    report = build_task_preflight(
        _project_root(),
        task_id=getattr(args, "task_id", "") or "",
        lane=getattr(args, "lane", "") or "",
        intent=getattr(args, "intent", "") or "",
        campaign_id=getattr(args, "campaign_id", "") or "",
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_task_preflight(report))
    return 0


def _cmd_heavy(args: argparse.Namespace) -> int:
    from .runtime.heavy_run import (
        find_heavy_project_root,
        inspect_heavy_job,
        list_heavy_jobs,
        run_heavy_job,
    )

    try:
        root = find_heavy_project_root(Path.cwd())
        if args.heavy_command == "list":
            payload = {"project_root": str(root), "jobs": list_heavy_jobs(root)}
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                for job_id in payload["jobs"]:
                    print(job_id)
            return 0
        result = (
            run_heavy_job(
                root, args.job, dry_run=bool(getattr(args, "dry_run", False))
            )
            if args.heavy_command == "run"
            else inspect_heavy_job(root, args.job)
        )
    except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"{result.status}: {result.job_id} {result.run_key}")
        print(f"  {result.message}")
        if result.pid:
            print(f"  pid: {result.pid}")
        if result.log_path:
            print(f"  log: {result.log_path}")
        print(f"  resume: {result.resume_pack}")
    return 0 if result.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aeros", description="AEROS runtime")
    sub = parser.add_subparsers(dest="command", required=False)


    event = sub.add_parser("event", help="append/replay kernel event log")
    event_sub = event.add_subparsers(dest="event_command", required=True)
    event_append = event_sub.add_parser("append", help="append a content-addressed event")
    event_append.add_argument("--event-type", required=True, help="event type, e.g. preanalysis_plan_committed")
    event_append.add_argument("--action-name", required=True, help="action name associated with the event")
    event_append.add_argument("--input", action="append", default=[], help="input artifact path; may be repeated")
    event_append.add_argument("--output", action="append", default=[], help="output artifact path; may be repeated")
    event_append.add_argument("--evidence", type=float, default=0.0, help="event evidence strength")
    event_append.add_argument("--note", default="", help="event note")
    event_append.add_argument("--require-artifacts", action="store_true",
                              help="fail if any declared input/output artifact does not exist")
    event_append.set_defaults(func=_cmd_event_append)
    event_replay = event_sub.add_parser("replay", help="replay event log and print digest")
    event_replay.set_defaults(func=_cmd_event_replay)

    init = sub.add_parser("init", help="create a minimal AEROS project scaffold")
    init.add_argument("path", help="target project directory")
    init.add_argument("--force", action="store_true", help="overwrite scaffold files if present")
    init.set_defaults(func=_cmd_init)

    start = sub.add_parser("start", help="start a research loop from an idea")
    start.add_argument("--idea", required=True, help="one-sentence idea or research question")
    start.add_argument("--target", default="", help="target AEROS wrapper project; default validation_projects/<slug>")
    start.add_argument("--mode", default="mirror", choices=["mirror", "readonly-audit", "inplace"],
                       help="intake mode; start is a compatibility shortcut for adopt --idea")
    start.add_argument("--dry-run", action="store_true", help="preview intake without writing files")
    start.add_argument("--no-deep", action="store_true", help="disable Codex CLI advisory synthesis")
    start.set_defaults(func=_cmd_start)

    adopt = sub.add_parser("adopt", help="universal research intake from an idea, file, or folder")
    adopt.add_argument("--idea", default="", help="one-sentence idea or research question")
    adopt.add_argument("--from", dest="source", default="", help="source memo/file/folder to adopt")
    adopt.add_argument("--target", default="", help="target AEROS wrapper project; default validation_projects/<slug>")
    adopt.add_argument("--mode", default="mirror", choices=["mirror", "readonly-audit", "inplace"],
                       help="mirror creates a wrapper, readonly-audit writes nothing, inplace writes into source/current project")
    adopt.add_argument("--dry-run", action="store_true", help="preview intake without writing files")
    adopt.add_argument("--no-deep", action="store_true", help="disable Codex CLI advisory synthesis")
    adopt.set_defaults(func=_cmd_adopt)

    run = sub.add_parser("run", help="run a single task contract or bounded controller loop")
    run.add_argument("contract", nargs="?", help="path to a task contract .yml")
    run.add_argument("--until", default="", choices=["", "human-gate", "blocked", "no-progress", "max-steps"],
                     help="run the bounded deterministic controller until this stop condition")
    run.add_argument("--lane", default="",
                     choices=["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"],
                     help="prefer one lane when using --until")
    run.add_argument("--max-steps", type=int, default=3,
                     help="maximum controller steps when using --until")
    run.add_argument("--max-actions", dest="max_steps", type=int,
                     help="alias for --max-steps; maximum controller actions when using --until")
    run.add_argument("--max-wall-time-seconds", type=int, default=300,
                     help="maximum controller wall-clock seconds when using --until")
    run.add_argument("--max-provider-calls", type=int, default=0,
                     help="maximum estimated provider/API calls when using --until; default 0")
    run.add_argument("--max-cost-usd", type=float, default=0.0,
                     help="maximum estimated provider/API cost in USD when using --until; default 0")
    run.add_argument("--no-progress-limit", type=int, default=1,
                     help="stop after this many non-substantive controller steps")
    run.add_argument("--allow-task-runs", action="store_true",
                     help="allow controller to turn iterate dry-runs into real task runs")
    run.add_argument("--json", action="store_true", help="emit controller records as JSON when using --until")
    run.add_argument("--dry-run", action="store_true",
                     help="print the agent prompt/planned checks, or preview controller action when using --until")
    run.add_argument("--max-retries", type=int, default=None,
                     help="override the contract's retry_policy.max_retries")
    run.add_argument("--task-timeout", type=int, default=None,
                     help="override this task's agent/command timeout in seconds")
    run.set_defaults(func=_cmd_run)

    chk = sub.add_parser("check", help="run a contract's checks or a harness profile without calling the agent")
    chk.add_argument("contract", nargs="?", help="path to a task contract .yml")
    chk.add_argument("--profile", default="", help="run a harness profile such as smoke, lane:data, lane:literature, or full")
    chk.add_argument("--timeout", type=int, default=None, help="per-check timeout when using --profile")
    chk.set_defaults(func=_cmd_check)

    recover = sub.add_parser(
        "recover",
        help="mark a manually completed task passed after its checks succeed",
    )
    recover.add_argument("task", help="task_id or path to a task contract .yml")
    recover.add_argument("--check", action="store_true",
                         help="run the task checks and recover only if they pass")
    recover.set_defaults(func=_cmd_recover)

    st = sub.add_parser("status", help="show runtime state (gate, per-task status, budget)")
    st.add_argument("--simple", action="store_true",
                    help="show compressed 5-milestone dashboard instead of full task details")
    st.set_defaults(func=_cmd_status)

    roadmap = sub.add_parser("roadmap", help="show compressed 5-milestone roadmap")
    roadmap.set_defaults(func=_cmd_roadmap)

    readiness = sub.add_parser("readiness", help="show derived project readiness vector")
    readiness.add_argument("--json", action="store_true", help="emit machine-readable readiness JSON")
    readiness.set_defaults(func=_cmd_readiness)

    driver = sub.add_parser("driver", help="research-driver recommendations for submission and paper risk")
    driver_sub = driver.add_subparsers(dest="driver_command", required=True)
    driver_submission = driver_sub.add_parser("submission", help="prioritize manuscript citation faithfulness and wrapper literature sync")
    driver_submission.add_argument("--write", action="store_true", help="write audits/submission_driver/* reports")
    driver_submission.add_argument("--json", action="store_true", help="emit machine-readable driver report")
    driver_submission.set_defaults(func=_cmd_driver)

    context_p = sub.add_parser("context", help="show a compact source-anchored context bundle")
    context_p.add_argument("--lane", default="project", choices=["project", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"], help="context lane to focus")
    context_p.add_argument("--brief", action="store_true", help="emit a shorter context bundle")
    context_p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    context_p.add_argument("--write", action="store_true", help="write CONTEXT_BUNDLE.md and outputs/context/context_bundle.json")
    context_p.add_argument("--stale", action="store_true", help="only report whether the written context bundle is stale")
    context_p.set_defaults(func=_cmd_context)

    cockpit_p = sub.add_parser("cockpit", help="show one compact context + next-action + fast-check dashboard")
    cockpit_p.add_argument("--lane", default="project", choices=["project", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"], help="cockpit lane to focus")
    cockpit_p.add_argument("--profile", default="smoke", help="fast check profile to display")
    cockpit_p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    cockpit_p.add_argument("--write", action="store_true", help="write cockpit, context bundle, and context graph artifacts")
    cockpit_p.set_defaults(func=_cmd_cockpit)


    writes = sub.add_parser("writes", help="audit observed worktree writes against declared/protected boundaries")
    writes_sub = writes.add_subparsers(dest="writes_command", required=True)
    writes_audit = writes_sub.add_parser("audit", help="dry-run observed writes vs declared/protected paths")
    writes_audit.add_argument("--since", default="HEAD", help="git ref to compare against; default HEAD")
    writes_audit.add_argument("--declared-write", action="append", default=[], help="declared write root/path; may be repeated")
    writes_audit.add_argument("--no-session", action="store_true", help="do not read SESSION_CONTRACT.yml allowed prefixes")
    writes_audit.add_argument("--strict", action="store_true", help="return nonzero if protected or undeclared writes are observed")
    writes_audit.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    writes_audit.add_argument("--write", action="store_true", help="write outputs/context/writes_audit.md and .json")
    writes_audit.set_defaults(func=_cmd_writes)

    next_p = sub.add_parser("next", help="show the deterministic next recommended action")
    next_p.add_argument("--lane", default="",
                        choices=["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"],
                        help="prefer the next action for one work lane")
    next_p.add_argument("--write", action="store_true", help="write NEXT_ACTION.md")
    next_p.add_argument("--json", action="store_true", help="emit machine-readable next action with full ActionSpec")
    next_p.set_defaults(func=_cmd_next)

    approve = sub.add_parser("approve", help="create scoped authority evidence; plain confirmation is not human proof")
    approve.add_argument("--campaign-id", required=True); approve.add_argument("--decision", required=True, choices=["continue", "stop"])
    approve.add_argument("--reason", required=True); approve.add_argument("--breaker", default="all"); approve.add_argument("--for-tasks", type=int, default=1)
    approve.add_argument("--decision-ref", required=True)
    approve.add_argument("--authority-evidence", choices=["local_authorship", "signed_commit", "external_human_approval"], default="local_authorship")
    approve.add_argument("--commit", action="store_true", help="commit only this approval; signed_commit uses git commit -S")
    approve.set_defaults(func=_cmd_approve)

    authority = sub.add_parser("authority", help="manage cryptographic human-authority trust anchors")
    authority_sub = authority.add_subparsers(dest="authority_command", required=True)
    authority_bootstrap = authority_sub.add_parser("bootstrap", help="interactively bind the first trusted SSH signer (TOFU)")
    authority_bootstrap.add_argument("--identity", required=True, help="existing approver_identity to bind")
    authority_bootstrap.add_argument("--principal", required=True, help="SSH signing principal, usually an email")
    authority_bootstrap.add_argument("--ssh-public-key", required=True, help="path to the public key")
    authority_bootstrap.add_argument("--commit", action="store_true", help="create the required signed policy commit")
    authority_bootstrap.set_defaults(func=_cmd_authority_bootstrap)

    job = sub.add_parser("job", help="compile ResearchJob into TaskContract, ActionSpec, and ExecutionEnvelope")
    job_sub = job.add_subparsers(dest="job_command", required=True); job_compile = job_sub.add_parser("compile")
    job_compile.add_argument("--file", required=True); job_compile.add_argument("--write", action="store_true"); job_compile.set_defaults(func=_cmd_job)

    heavy = sub.add_parser(
        "heavy",
        help="single-flight execution and cache reuse for declared expensive jobs",
    )
    heavy_sub = heavy.add_subparsers(dest="heavy_command", required=True)
    heavy_list = heavy_sub.add_parser("list", help="list project-declared heavy jobs")
    heavy_list.add_argument("--json", action="store_true")
    heavy_list.set_defaults(func=_cmd_heavy)
    heavy_status = heavy_sub.add_parser(
        "status", help="inspect RunKey, lease, cache, and retry status"
    )
    heavy_status.add_argument("--job", required=True)
    heavy_status.add_argument("--json", action="store_true")
    heavy_status.set_defaults(func=_cmd_heavy)
    heavy_run = heavy_sub.add_parser(
        "run", help="run once, attach, reuse, or stop at plateau"
    )
    heavy_run.add_argument("--job", required=True)
    heavy_run.add_argument("--dry-run", action="store_true")
    heavy_run.add_argument("--json", action="store_true")
    heavy_run.set_defaults(func=_cmd_heavy)

    adaptive = sub.add_parser("checks", help="select change-aware checks from observed writes")
    adaptive_sub = adaptive.add_subparsers(dest="adaptive_command", required=True); adaptive_select = adaptive_sub.add_parser("select")
    adaptive_select.add_argument("--changed", action="append", default=[])
    adaptive_select.add_argument("--action-exit", type=int, default=None, help="observed action exit code for fail-closed post-action assessment")
    adaptive_select.add_argument("--expected-output", action="append", default=[], help="project-relative expected artifact; repeat for multiple outputs")
    adaptive_select.set_defaults(func=_cmd_adaptive_checks)

    migrate = sub.add_parser("migrate", help="prepare or inspect package-mode migration without deleting vendored files")
    migrate_sub = migrate.add_subparsers(dest="migrate_command", required=True)
    migrate_inspect = migrate_sub.add_parser("inspect"); migrate_inspect.set_defaults(func=_cmd_migrate)
    migrate_prepare = migrate_sub.add_parser("prepare"); migrate_prepare.add_argument("--policy-bundle-version", default="aeros-policy-v1"); migrate_prepare.set_defaults(func=_cmd_migrate)
    doctor = sub.add_parser("doctor", help="validate installed package against .aeros/project.yml and aeros.lock")
    doctor.add_argument("--json", action="store_true"); doctor.set_defaults(func=_cmd_doctor)

    campaign = sub.add_parser("campaign", help="assess repeated-loop campaign contracts and marginal-yield breakers")
    campaign_sub = campaign.add_subparsers(dest="campaign_command", required=True)
    campaign_assess = campaign_sub.add_parser("assess", help="assess active campaign contract without executing work")
    campaign_assess.add_argument("--contract", default="", help="campaign contract path, default campaigns/active_campaign.yml")
    campaign_assess.add_argument("--progress", default="", help="campaign progress CSV path, default campaigns/campaign_progress.csv")
    campaign_assess.add_argument("--campaign-id", default="", help="only assess when this identity matches the active campaign")
    campaign_assess.add_argument("--write", action="store_true", help="write outputs/campaign/campaign_assessment.md and .json")
    campaign_assess.add_argument("--json", action="store_true", help="emit machine-readable campaign assessment")
    campaign_assess.set_defaults(func=_cmd_campaign)
    campaign_new = campaign_sub.add_parser("new", help="scaffold a campaign contract from the template")
    campaign_new.add_argument("--path", default="", help="target path, default campaigns/active_campaign.yml")
    campaign_new.add_argument("--force", action="store_true", help="overwrite an existing campaign contract")
    campaign_new.set_defaults(func=_cmd_campaign)
    campaign_continue = campaign_sub.add_parser("continue", help="record a human decision to continue past a tripped breaker for a bounded number of tasks")
    campaign_continue.add_argument("--approval", required=True, help="committed human approval YAML; decision parameters are read from this artifact")
    campaign_continue.set_defaults(func=_cmd_campaign)
    campaign_stop = campaign_sub.add_parser("stop", help="record a human decision to halt the campaign")
    campaign_stop.add_argument("--approval", required=True, help="committed human approval YAML; decision parameters are read from this artifact")
    campaign_stop.set_defaults(func=_cmd_campaign)

    drive_p = sub.add_parser("drive", help="choose and optionally execute one useful safe next objective")
    drive_p.add_argument("--goal", default="auto", choices=["auto", "capture", "broad-capture", "promote", "source-promotion", "literature", "fulltext", "citation-risk", "submission", "data-probe", "probe"], help="optional objective override")
    drive_p.add_argument("--lane", default="", choices=["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"], help="optional lane preference for auto mode")
    drive_p.add_argument("--execute", action="store_true", help="execute only allowlisted read-only/dry-run commands")
    drive_p.add_argument("--write", action="store_true", help="write outputs/context/drive_packet.md and .json")
    drive_p.add_argument("--json", action="store_true", help="emit machine-readable drive packet")
    drive_p.add_argument("--job", default="", choices=["", "find_data", "probe_data", "run_specification", "diagnose_design", "read_literature", "bind_or_reproduce_paper"], help="run one economics-native drive job")
    drive_p.add_argument("--source-candidate", default="", help="project-relative input artifact for an executable ResearchJob")
    drive_p.add_argument("--target", default="", help="registered target ID, such as a specification ID")
    drive_p.add_argument("--no-history", action="store_true", help="skip optional local ai-hist prior-session lookup")
    drive_p.set_defaults(func=_cmd_drive)

    submit_p = sub.add_parser("submit", help="assess readiness or source-ground manuscript citations without granting release")
    submit_p.add_argument("submit_action", nargs="?", default="readiness", choices=["readiness", "fact-check"])
    submit_p.add_argument("--manuscript", default="", help="project-relative manuscript path for fact-check; defaults to discovered manuscripts")
    submit_p.add_argument("--allow-network", action="store_true", help="allow bounded retrieval from credential-free public HTTPS sources")
    submit_p.add_argument("--write", action="store_true", help="write fact-check report and unresolved human-review queue")
    submit_p.add_argument("--json", action="store_true")
    submit_p.set_defaults(func=_cmd_submit)

    econ = sub.add_parser("econ", help="advanced economics object-chain, protocol, radar, and skill projections")
    econ_sub = econ.add_subparsers(dest="econ_command", required=True)
    econ_init = econ_sub.add_parser("init"); econ_init.add_argument("--json", action="store_true"); econ_init.set_defaults(func=_cmd_econ)
    econ_chain = econ_sub.add_parser("chain"); econ_chain.add_argument("--json", action="store_true"); econ_chain.set_defaults(func=_cmd_econ)
    econ_protocol = econ_sub.add_parser("protocol"); econ_protocol.add_argument("--name", required=True, choices=["iv", "did", "rd", "panel", "synthetic_control", "econ:iv", "econ:did", "econ:rd", "econ:panel", "econ:synthetic_control"]); econ_protocol.add_argument("--spec-id", default=""); econ_protocol.add_argument("--json", action="store_true"); econ_protocol.set_defaults(func=_cmd_econ)
    econ_radar = econ_sub.add_parser("literature-radar"); econ_radar.add_argument("--write", action="store_true"); econ_radar.add_argument("--json", action="store_true"); econ_radar.set_defaults(func=_cmd_econ)
    econ_skills = econ_sub.add_parser("skill-scorecard"); econ_skills.add_argument("--json", action="store_true"); econ_skills.set_defaults(func=_cmd_econ)

    session = sub.add_parser("session", help="start/status/audit a lane-scoped chat session")
    session_sub = session.add_subparsers(dest="session_command", required=True)
    session_start = session_sub.add_parser("start", help="write SESSION_CONTRACT.yml for one lane-scoped work session")
    session_start.add_argument("--lane", required=True,
                               choices=["data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"],
                               help="active lane for this session")
    session_start.add_argument("--objective", required=True, help="one concrete objective for this session")
    session_start.add_argument("--workflow", default="", help="optional workflow preset, e.g. recapture_source_pool")
    session_start.add_argument("--max-actions", type=int, default=2, help="maximum intended actions before stopping")
    session_start.add_argument("--allowed-action", action="append", default=[], help="allowed action phrase; may be repeated")
    session_start.add_argument("--dry-run", action="store_true", help="preview the session contract without writing")
    session_start.set_defaults(func=_cmd_session)
    session_status = session_sub.add_parser("status", help="show active SESSION_CONTRACT.yml")
    session_status.set_defaults(func=_cmd_session)
    session_audit = session_sub.add_parser("audit", help="audit changed files against active session scope")
    session_audit.add_argument("--json", action="store_true", help="emit machine-readable audit JSON")
    session_audit.set_defaults(func=_cmd_session)

    skills = sub.add_parser("skills", help="inspect AEROS skill routing")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_plan = skills_sub.add_parser("plan", help="show recommended/allowed skills by task")
    skills_plan.add_argument("--stage", default="all", choices=["all", "discovery", "execution"],
                             help="task stage to inspect (default: all)")
    skills_plan.set_defaults(func=_cmd_skills_plan)

    sync = sub.add_parser("sync", help="inspect framework sync status for downstream projects")
    sync_sub = sync.add_subparsers(dest="sync_command", required=True)
    sync_doctor_p = sync_sub.add_parser("doctor", help="report missing/outdated AEROS capabilities in projects")
    sync_doctor_p.add_argument("--project", action="append", default=[], help="project root to inspect; may be repeated")
    sync_doctor_p.add_argument("--template-root", default="", help="template root to compare against")
    sync_doctor_p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    sync_doctor_p.set_defaults(func=_cmd_sync_doctor)

    task = sub.add_parser("task", help="task utilities")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_preflight = task_sub.add_parser("preflight", help="emit task start guardrail packet")
    task_preflight.add_argument("--task-id", default="", help="task id to inspect")
    task_preflight.add_argument("--lane", default="", choices=["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"], help="task lane")
    task_preflight.add_argument("--intent", default="", help="short description of intended work")
    task_preflight.add_argument("--campaign-id", default="", help="campaign identity for an ActionSpec/preflight without a task contract")
    task_preflight.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    task_preflight.set_defaults(func=_cmd_task_preflight)



    literature = sub.add_parser("literature", help="literature discovery adapters and status")
    literature_sub = literature.add_subparsers(dest="literature_command", required=True)
    literature_status = literature_sub.add_parser("status", help="show literature discovery/extraction counts")
    literature_status.set_defaults(func=_cmd_literature)
    literature_search = literature_sub.add_parser("search", help="search/import literature metadata into registry/queues")
    literature_search.add_argument("--source", required=True, choices=["openalex", "manual", "zotero"], help="metadata source adapter")
    literature_search.add_argument("--query", default="", help="search query for source adapters such as OpenAlex or Zotero")
    literature_search.add_argument("--limit", type=int, default=20, help="maximum candidates to fetch/import")
    literature_search.add_argument("--primary-function", default="idea-inspiring", choices=["idea-inspiring", "gap-verification", "method-identification", "data-measurement", "background-institutional", "theory-mechanism"], help="initial literature function label for candidates")
    literature_search.add_argument("--title", default="", help="manual import title")
    literature_search.add_argument("--authors", default="", help="manual import authors")
    literature_search.add_argument("--year", default="", help="manual import year")
    literature_search.add_argument("--doi", default="", help="manual import DOI")
    literature_search.add_argument("--url", default="", help="manual import URL/OpenAlex ID")
    literature_search.add_argument("--pdf-url", default="", help="manual import PDF URL")
    literature_search.add_argument("--zotero-base-url", default="http://127.0.0.1:23119", help="Zotero local API base URL")
    literature_search.add_argument("--dry-run", action="store_true", help="preview registry/search-log changes without writing")
    literature_search.set_defaults(func=_cmd_literature)

    action = sub.add_parser("action", help="write/validate action progress receipts")
    action_sub = action.add_subparsers(dest="action_command", required=True)
    action_receipt = action_sub.add_parser("receipt", help="write an action receipt classifying this run")
    action_receipt.add_argument("--action-id", required=True, help="stable action id, e.g. D002_probe_2026_06_16")
    action_receipt.add_argument("--action-mode", required=True, choices=["data_progress", "data_backfill", "data_probe", "data_validation", "harness_triage", "literature_progress", "claim_audit", "writing", "cleanup"])
    action_receipt.add_argument("--progress-label", required=True, choices=["substantive_research_progress", "mechanical_hygiene", "blocked_queue_preparation", "source_discovery_attempt", "documentation_repair"])
    action_receipt.add_argument("--why-this-now", required=True, help="why this was the next action")
    action_receipt.add_argument("--summary", required=True, help="short honest summary of what changed")
    action_receipt.add_argument("--evidence-path", action="append", default=[], help="artifact proving this action, relative to project root")
    action_receipt.add_argument("--dependency-type", required=True, choices=["enabling", "validating", "cosmetic", "blocking_resolution"], help="counterfactual role of this action")
    action_receipt.add_argument("--would-progress-without-this-action", action="store_true", help="mark true only if the project would have progressed anyway")
    for flag in ["inventory-changed", "source-verified", "data-rows-changed", "coverage-changed", "backfill-queue-changed", "probe-completed", "claim-ceiling-changed", "gate-candidate-changed", "evidence-graph-changed", "result-registered"]:
        action_receipt.add_argument("--" + flag, action="store_true")
    action_receipt.add_argument("--dry-run", action="store_true", help="validate without writing")
    action_receipt.set_defaults(func=_cmd_action_receipt)

    delta = sub.add_parser("delta", help="append/list incremental evidence deltas")
    delta_sub = delta.add_subparsers(dest="delta_command", required=True)
    delta_append = delta_sub.add_parser("append", help="append one lane evidence delta")
    delta_append.add_argument("--lane", required=True,
                              choices=["data", "literature", "analysis", "claim", "writing", "compliance", "harness"],
                              help="work lane this delta belongs to")
    delta_append.add_argument("--summary", required=True, help="short description of what evidence changed")
    delta_append.add_argument("--artifact-added", action="append", default=[],
                              help="artifact path added by this delta")
    delta_append.add_argument("--artifact-updated", action="append", default=[],
                              help="artifact path updated by this delta")
    delta_append.add_argument("--coverage-delta", action="append", default=[],
                              help="coverage delta as key=value; repeatable")
    delta_append.add_argument("--judgment-implication", action="append", default=[],
                              help="implication for design/claim/paper judgment; repeatable")
    delta_append.add_argument("--remaining-gap", action="append", default=[],
                              help="remaining gap after this delta; repeatable")
    delta_append.add_argument("--next-best-increment", required=True,
                              help="next best evidence increment for this lane")
    delta_append.add_argument("--sufficiency", required=True,
                              choices=["insufficient", "inventory_started", "minimum_viable", "expanding", "locked_for_current_analysis", "reopened", "blocked"],
                              help="current sufficiency for this lane/purpose")
    delta_append.add_argument("--task-id", default="", help="task id that produced this delta")
    delta_append.add_argument("--run-ref", default="", help="run report, receipt, or external reference")
    delta_append.add_argument("--dry-run", action="store_true", help="validate without writing")
    delta_append.set_defaults(func=_cmd_delta)
    delta_list = delta_sub.add_parser("list", help="list recent evidence deltas")
    delta_list.add_argument("--lane", default="",
                            choices=["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"],
                            help="filter by lane")
    delta_list.add_argument("--limit", type=int, default=20, help="number of recent records to show")
    delta_list.set_defaults(func=_cmd_delta)

    manifest_p = sub.add_parser("manifest",
                                help="snapshot/verify SHA256 of registered result artifacts")
    manifest_p.add_argument("--verify", action="store_true",
                            help="verify current artifacts against the manifest (detect drift)")
    manifest_p.set_defaults(func=_cmd_manifest)

    paper = sub.add_parser("paper", help="paper utilities (number injection)")
    paper_sub = paper.add_subparsers(dest="paper_command", required=True)
    paper_render = paper_sub.add_parser(
        "render", help="substitute {{name}} number tokens from paper/numbers.yml")
    paper_render.add_argument("--paper", default="", help="paper source (default paper/draft.md)")
    paper_render.set_defaults(func=_cmd_paper_render)

    paper_ci = sub.add_parser("paper-ci", help="Paper CI utilities (result registry, tracing, consistency)")
    paper_ci_sub = paper_ci.add_subparsers(dest="paper_ci_command", required=True)
    paper_ci_register = paper_ci_sub.add_parser(
        "register-result",
        help="register a result-born estimation record from adapter JSON",
    )
    paper_ci_register.add_argument("--record", required=True, help="path to adapter JSON record")
    paper_ci_register.add_argument("--dry-run", action="store_true", help="validate without writing registry")
    paper_ci_register.set_defaults(func=_cmd_paper_ci)
    paper_ci_sync = paper_ci_sub.add_parser(
        "sync-result-index",
        help="derive evidence/result_index.csv rows from evidence/result_registry.csv",
    )
    paper_ci_sync.add_argument("--dry-run", action="store_true", help="show target without writing result_index")
    paper_ci_sync.add_argument("--no-provenance", action="store_true", help="do not also sync outputs/.provenance JSON")
    paper_ci_sync.set_defaults(func=_cmd_paper_ci)
    paper_ci_schema = paper_ci_sub.add_parser("schema", help="show Phase 0 adapter/registry schema")
    paper_ci_schema.set_defaults(func=_cmd_paper_ci)

    number = sub.add_parser("number", help="injected-number tools (drift vs lock)")
    number_sub = number.add_subparsers(dest="number_command", required=True)
    number_drift = number_sub.add_parser(
        "drift", help="report injected numbers whose source cell moved vs paper/numbers.lock.yml")
    number_drift.add_argument("--update", action="store_true",
                              help="accept current values: rewrite the lock (requires --owner)")
    number_drift.add_argument("--owner", default="",
                              help="human accepting the moved numbers (required with --update)")
    number_drift.add_argument("--note", default="",
                              help="why the moved numbers are acceptable")
    number_drift.add_argument("--all", action="store_true",
                              help="show unchanged entries too, not just moved")
    number_drift.set_defaults(func=_cmd_number_drift)

    provenance_p = sub.add_parser(
        "provenance", help="keep the provenance layer in sync with the result index")
    provenance_sub = provenance_p.add_subparsers(dest="provenance_command", required=True)
    provenance_sync = provenance_sub.add_parser(
        "sync", help="write a provenance JSON per registered result (sha256 from disk)")
    provenance_sync.set_defaults(func=_cmd_provenance)

    graph = sub.add_parser("graph", help="build and query the derived research graph")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)
    graph_build = graph_sub.add_parser("build", help="rebuild evidence/research_graph.yml")
    graph_build.add_argument("--dry-run", action="store_true",
                             help="show the graph size without writing research_graph.yml")
    graph_build.set_defaults(func=_cmd_graph)
    graph_query = graph_sub.add_parser("query", help="query graph impact/support/coverage/orphans")
    graph_query_sub = graph_query.add_subparsers(dest="graph_query", required=True)
    graph_impact = graph_query_sub.add_parser(
        "impact", help="show claims/sections that may need review after an artifact/result changes")
    graph_impact.add_argument("target", help="artifact path, result/evidence/provenance id, or graph node id")
    graph_impact.set_defaults(func=_cmd_graph)
    graph_support = graph_query_sub.add_parser(
        "support", help="show the evidence/result/artifact/provenance chain for a claim")
    graph_support.add_argument("claim_id", help="claim id, e.g. C001")
    graph_support.set_defaults(func=_cmd_graph)
    graph_coverage = graph_query_sub.add_parser(
        "coverage", help="show uncovered human-asserted research questions/subquestions")
    graph_coverage.set_defaults(func=_cmd_graph)
    graph_orphans = graph_query_sub.add_parser(
        "orphans", help="show advisory orphan results/artifacts and unsupported active claims")
    graph_orphans.set_defaults(func=_cmd_graph)

    funnel = sub.add_parser("funnel",
                            help="two-layer funnel: parallel candidates -> champion")
    funnel_sub = funnel.add_subparsers(dest="funnel_command", required=True)
    funnel_new = funnel_sub.add_parser("new", help="scaffold N parallel candidates for a round")
    funnel_new.add_argument("round", help="round name, e.g. findings or design")
    funnel_new.add_argument("--candidates", type=int, default=3, help="number of parallel candidates")
    funnel_new.add_argument("--criterion", default="", help="selection criterion, stated up front")
    funnel_new.set_defaults(func=_cmd_funnel)
    funnel_sel = funnel_sub.add_parser("select", help="record the champion; prune the rest")
    funnel_sel.add_argument("round", help="round name")
    funnel_sel.add_argument("--champion", required=True, help="candidate id to crown")
    funnel_sel.add_argument("--rationale", default="", help="why this champion (not significance alone)")
    funnel_sel.set_defaults(func=_cmd_funnel)


    stale = sub.add_parser("stale", help="inspect stale task impact without running agents")
    stale_sub = stale.add_subparsers(dest="stale_command", required=True)
    stale_triage = stale_sub.add_parser("triage", help="classify stale tasks as rerun_required, revalidate_free, or suppress_as_irrelevant")
    stale_triage.add_argument("--stage", default="discovery", choices=["discovery", "execution", "all"], help="stage to inspect")
    stale_triage.add_argument("--lane", default="", choices=["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"], help="optional lane focus")
    stale_triage.add_argument("--dry-run", action="store_true", help="do not write triage artifacts")
    stale_triage.add_argument("--write", action="store_true", help="write outputs/context/stale_triage.md and .json")
    stale_triage.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    stale_triage.set_defaults(func=_cmd_stale)

    claim_vector = sub.add_parser("claim-vector", help="compile advisory claim language boundaries")
    claim_vector_sub = claim_vector.add_subparsers(dest="claim_vector_command", required=True)
    claim_vector_compile = claim_vector_sub.add_parser("compile", help="compile allowed/forbidden claim language")
    claim_vector_compile.add_argument("--claim-id", required=True, help="claim id or candidate claim id")
    claim_vector_compile.add_argument(
        "--evidence-status",
        default="none",
        choices=["none", "candidate_support", "admitted_support", "contradicts"],
        help="current evidence status",
    )
    claim_vector_compile.add_argument(
        "--identification-level",
        default="none",
        choices=["none", "descriptive", "associational", "causal"],
        help="current identification level",
    )
    claim_vector_compile.add_argument(
        "--result-admission-status",
        default="not_admitted",
        choices=["not_admitted", "needs_review", "human_admitted", "rejected"],
        help="ResultAdmission status",
    )
    claim_vector_compile.add_argument(
        "--validation-status",
        default="unvalidated",
        choices=["unvalidated", "validated", "robust"],
        help="validation/robustness status",
    )
    claim_vector_compile.add_argument("--json", action="store_true", help="emit machine-readable ClaimVector JSON")
    claim_vector_compile.set_defaults(func=_cmd_claim_vector)

    claim_upgrade = sub.add_parser("claim-upgrade", help="generate human-gated claim upgrade review packets")
    claim_upgrade_sub = claim_upgrade.add_subparsers(dest="claim_upgrade_command", required=True)
    claim_upgrade_review = claim_upgrade_sub.add_parser("review", help="review whether a claim may be proposed for human upgrade")
    claim_upgrade_review.add_argument("--claim-id", required=True, help="claim id or candidate claim id")
    claim_upgrade_review.add_argument("--evidence-status", default="none", choices=["none", "candidate_support", "admitted_support", "contradicts"])
    claim_upgrade_review.add_argument("--identification-level", default="none", choices=["none", "descriptive", "associational", "causal"])
    claim_upgrade_review.add_argument("--result-admission-status", default="not_admitted", choices=["not_admitted", "needs_review", "human_admitted", "rejected"])
    claim_upgrade_review.add_argument("--validation-status", default="unvalidated", choices=["unvalidated", "validated", "robust"])
    claim_upgrade_review.add_argument("--write", action="store_true", help="write decisions/claim_upgrade/<claim>_upgrade_review.md")
    claim_upgrade_review.add_argument("--json", action="store_true", help="emit machine-readable review JSON")
    claim_upgrade_review.set_defaults(func=_cmd_claim_upgrade)

    paper_readiness = sub.add_parser("paper-readiness", help="generate human-gated paper-readiness report packets")
    paper_readiness_sub = paper_readiness.add_subparsers(dest="paper_readiness_command", required=True)
    paper_readiness_report = paper_readiness_sub.add_parser("report", help="aggregate readiness signals for human paper review")
    paper_readiness_report.add_argument("--write", action="store_true", help="write decisions/paper_readiness/paper_readiness_report.md")
    paper_readiness_report.add_argument("--json", action="store_true", help="emit machine-readable paper-readiness report JSON")
    paper_readiness_report.set_defaults(func=_cmd_paper_readiness)

    journal = sub.add_parser("journal", help="build derived SQLite journal indexes")
    journal_sub = journal.add_subparsers(dest="journal_command", required=True)
    journal_build = journal_sub.add_parser("build", help="build disposable SQLite journal from source files")
    journal_build.add_argument("--output", default="", help="output sqlite path; default outputs/journal/aeros_journal.sqlite")
    journal_build.add_argument("--dry-run", action="store_true", help="summarize source counts without writing sqlite")
    journal_build.add_argument("--json", action="store_true", help="emit machine-readable journal build report")
    journal_build.set_defaults(func=_cmd_journal)

    reconcile = sub.add_parser(
        "reconcile",
        help="sync derived provenance/graph/state indexes after a real pipeline run",
    )
    reconcile.add_argument("--dry-run", action="store_true",
                           help="show the reconcile plan without writing derived indexes")
    reconcile.add_argument("--timeout", type=int, default=120,
                           help="per-step timeout in seconds")
    reconcile.add_argument("--skip-result-index", action="store_true",
                           help="do not derive result_index from result_registry")
    reconcile.add_argument("--skip-provenance", action="store_true",
                           help="do not run provenance sync")
    reconcile.add_argument("--skip-graph", action="store_true",
                           help="do not rebuild evidence/research_graph.yml")
    reconcile.add_argument("--skip-state", action="store_true",
                           help="do not rebuild aeros/state/global_state.yml")
    reconcile.add_argument("--include-context", action="store_true",
                           help="also refresh CONTEXT_BUNDLE.md and outputs/context/context_bundle.json")
    reconcile.add_argument("--no-report", action="store_true",
                           help="do not write outputs/logs/aeros_reconcile_*.md")
    reconcile.set_defaults(func=_cmd_reconcile)

    state_parser = sub.add_parser("state", help="inspect or clean runtime state")
    state_sub = state_parser.add_subparsers(dest="state_command", required=True)
    state_global = state_sub.add_parser("global", help="build the derived global state index")
    state_global.add_argument("--dry-run", action="store_true", help="show global state summary without writing")
    state_global.set_defaults(func=_cmd_state_global)

    state_prune = state_sub.add_parser(
        "prune",
        help="remove task state entries whose contracts no longer exist",
    )
    state_prune.add_argument("--dry-run", action="store_true",
                             help="show stale entries without modifying aeros_state.yml")
    state_prune.set_defaults(func=_cmd_state_prune)

    gate = sub.add_parser("gate", help="inspect or record human gate decisions")
    gate_sub = gate.add_subparsers(dest="gate_command", required=True)

    gate_status = gate_sub.add_parser("status", help="show current gate status")
    gate_status.set_defaults(func=_cmd_gate_status)

    gate_history = gate_sub.add_parser("history", help="show gate movement history")
    gate_history.add_argument("--limit", type=int, default=20, help="number of entries to show")
    gate_history.set_defaults(func=_cmd_gate_history)

    gate_approve = gate_sub.add_parser("approve", help="record a human gate approval")
    gate_approve.add_argument("gate", help="gate to approve, e.g. G3")
    gate_approve.add_argument("--stage", default="discovery", help="stage name")
    gate_approve.add_argument("--owner", default="", help="human owner / approver")
    gate_approve.add_argument("--note", default="", help="approval rationale")
    gate_approve.add_argument("--force", action="store_true",
                              help="approve even if gate exit criteria are unmet (override is logged)")
    gate_approve.set_defaults(func=_cmd_gate_approve)

    gate_plan = gate_sub.add_parser(
        "plan", help="PLAN: write a proposal deck (text only, no execution)")
    gate_plan.add_argument("gate", help="gate to plan, e.g. G3")
    gate_plan.add_argument("--stage", default="discovery", help="stage name")
    gate_plan.set_defaults(func=_cmd_gate_plan)

    gate_apply = gate_sub.add_parser(
        "apply", help="APPLY: a committed, valid plan deck grants the gate")
    gate_apply.add_argument("gate", help="gate to apply, e.g. G3")
    gate_apply.add_argument("--stage", default="discovery", help="stage name")
    gate_apply.add_argument("--owner", default="", help="approver")
    gate_apply.add_argument("--force", action="store_true",
                            help="apply even if deck/criteria checks fail (override is logged)")
    gate_apply.set_defaults(func=_cmd_gate_apply)

    gate_request = gate_sub.add_parser(
        "request", help="write an approval REQUEST artifact (agent may do this; does not grant)")
    gate_request.add_argument("gate", help="gate to request, e.g. G3")
    gate_request.add_argument("--stage", default="discovery", help="stage name")
    gate_request.add_argument("--owner", default="", help="requester")
    gate_request.add_argument("--note", default="", help="evidence summary for the approver")
    gate_request.set_defaults(func=_cmd_gate_request)

    gate_block = gate_sub.add_parser("block", help="record a human gate block")
    gate_block.add_argument("gate", help="gate to block, e.g. G6")
    gate_block.add_argument("--stage", default="execution", help="stage name")
    gate_block.add_argument("--owner", default="", help="human owner / blocker")
    gate_block.add_argument("--reason", default="", help="blocking rationale")
    gate_block.set_defaults(func=_cmd_gate_block)

    gate_packet = gate_sub.add_parser("packet", help="write a human gate decision packet")
    gate_packet.add_argument("gate", help="gate to summarize, e.g. G3")
    gate_packet.add_argument("--stage", default="", help="stage name for the packet")
    gate_packet.set_defaults(func=_cmd_gate_packet)

    lt = sub.add_parser("list-tasks", help="list .yml task contracts in the project")
    lt.set_defaults(func=_cmd_list_tasks)

    adj = sub.add_parser("adjudicate", help="adjudicate design options against data diagnostics (earn the claim)")
    adj.set_defaults(func=_cmd_adjudicate)

    feas = sub.add_parser("feasibility", help="G1-G3 feasibility verdict (data + variables + viable design)")
    feas.set_defaults(func=_cmd_feasibility)

    pipe = sub.add_parser("pipeline", help="run a stage's tasks in dependency order, then adjudicate + feasibility")
    pipe.add_argument("--stage", default="discovery", help="stage to run (default: discovery)")
    pipe.add_argument("--dry-run", action="store_true", help="show the ordered plan; do not run agents")
    pipe.add_argument("--task-timeout", type=int, default=None,
                      help="override each task's agent/command timeout in seconds")
    pipe.add_argument("--max-retries", type=int, default=None,
                      help="override each task's retry_policy.max_retries")
    pipe.set_defaults(func=_cmd_pipeline)

    collect = sub.add_parser("collect", help="collect AI outputs from an approved prompt grid")
    collect.add_argument("--grid", default="outputs/audit_runs/expanded_prompt_grid.csv",
                         help="prompt grid CSV relative to project root")
    collect.add_argument("--out", default="outputs/audit_runs/expanded_ai_outputs.jsonl",
                         help="output JSONL path relative to project root")
    collect.add_argument("--report", default="audits/expanded_collection_run_report.md",
                         help="collection run report path relative to project root")
    collect.add_argument("--provider", default=None,
                         choices=["mock", "openai", "claude-cli", "claude", "codex-cli", "codex"],
                         help="collection provider; default from project_manifest.yml")
    collect.add_argument("--model", default=None, help="provider model; default from project_manifest.yml")
    collect.add_argument("--max-cost-usd", type=float, default=None,
                         help="collection cost cap; 0 means no positive cap")
    collect.add_argument("--max-retries", type=int, default=None,
                         help="per-row provider retry count")
    collect.add_argument("--timeout", type=int, default=None,
                         help="provider request timeout in seconds")
    collect.add_argument("--rate-limit-seconds", type=float, default=None,
                         help="sleep between provider calls")
    collect.add_argument("--max-rows", type=int, default=None,
                         help="optional row limit for smoke collection")
    collect.add_argument("--dry-run", action="store_true",
                         help="print collection plan without provider calls or writes")
    collect.set_defaults(func=_cmd_collect)

    data = sub.add_parser("data", help="data audit and backfill orchestration")
    data_sub = data.add_subparsers(dest="data_command", required=True)
    data_scan = data_sub.add_parser("scan", help="scan local data/code/output artifacts and write data/data_state.yml")
    data_scan.add_argument("--dry-run", action="store_true", help="show scan summary without writing files")
    data_scan.set_defaults(func=_cmd_data)
    data_gaps = data_sub.add_parser("gaps", help="detect data readiness gaps and write data/data_gap_plan.yml")
    data_gaps.add_argument("--dry-run", action="store_true", help="show gaps without writing files")
    data_gaps.set_defaults(func=_cmd_data)
    data_plan = data_sub.add_parser("plan", help="show data-first next actions without writing files")
    data_plan.set_defaults(func=_cmd_data)

    data_probe = data_sub.add_parser("probe", help="small-sample data probe before full collection")
    data_probe_sub = data_probe.add_subparsers(dest="data_probe_command", required=True)
    data_probe_plan = data_probe_sub.add_parser("plan", help="plan small probes from discovery/data_inventory.csv")
    data_probe_plan.add_argument("--dry-run", action="store_true", help="show probe plan without writing")
    data_probe_plan.set_defaults(func=_cmd_data)
    data_probe_run = data_probe_sub.add_parser("run", help="run a local-file sample probe for one data source")
    data_probe_run.add_argument("--source", required=True, help="data_id or dataset_name from discovery/data_inventory.csv")
    data_probe_run.add_argument("--limit", type=int, default=25, help="sample row limit")
    data_probe_run.add_argument("--dry-run", action="store_true", help="show what would run without writing")
    data_probe_run.set_defaults(func=_cmd_data)
    data_probe_report = data_probe_sub.add_parser("report", help="summarize completed probe metadata")
    data_probe_report.add_argument("--dry-run", action="store_true", help="show report summary without writing")
    data_probe_report.set_defaults(func=_cmd_data)
    data_probe_census = data_probe_sub.add_parser("census", help="run bounded Census API probe from EconomicDataSeries in DataContract")
    data_probe_census.add_argument("--series-id", default="auto")
    data_probe_census.add_argument("--contract", default="docs/data_contract.yml")
    data_probe_census.add_argument("--api-key-env", default="CENSUS_API_KEY")
    data_probe_census.add_argument("--json", action="store_true")
    data_probe_census.set_defaults(func=_cmd_data)
    data_probe_official = data_probe_sub.add_parser("official", help="run bounded Census or FRED probe from EconomicDataSeries")
    data_probe_official.add_argument("--series-id", default="auto")
    data_probe_official.add_argument("--contract", default="docs/data_contract.yml")
    data_probe_official.add_argument("--api-key-env", default="CENSUS_API_KEY")
    data_probe_official.add_argument("--json", action="store_true")
    data_probe_official.set_defaults(func=_cmd_data)

    data_backfill = data_sub.add_parser("backfill", help="build and optionally run a data backfill queue")
    data_backfill.add_argument("--dry-run", action="store_true",
                               help="show queue plan without writing files or running commands")
    data_backfill.add_argument("--run-local", action="store_true",
                               help="run queue items that are auto_rerunnable and have explicit run_command")
    data_backfill.add_argument("--approve", default="",
                               help="approve a blocked queue item by task_id or data_id; does not run without run_command")
    data_backfill.add_argument("--receipt", default="",
                               help="write a human review receipt for a queue item by task_id or data_id")
    data_backfill.add_argument("--owner", default="", help="human owner for approval or receipt")
    data_backfill.add_argument("--source-snapshot", default="", help="source snapshot/date/path reviewed by human")
    data_backfill.add_argument("--note", default="", help="approval or receipt note")
    data_backfill.add_argument("--coverage", default="", help="coverage reviewed for receipt")
    data_backfill.add_argument("--disagreement-log", default="", help="disagreement/ambiguity log for receipt")
    data_backfill.add_argument("--human-decision", default="", help="human decision recorded in receipt")
    data_backfill.set_defaults(func=_cmd_data)

    iterate = sub.add_parser("iterate", help="run the research controller until the next human gate")
    iterate.add_argument("--stage", default="discovery", choices=["discovery", "execution"],
                         help="stage to iterate (default: discovery)")
    iterate.add_argument("--lane", default="",
                         choices=["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"],
                         help="restrict iterate to one work lane; prevents cross-lane drift")
    iterate.add_argument("--dry-run", action="store_true",
                         help="show the controller plan; do not run tasks or write packets")
    iterate.add_argument("--to-next-gate", action="store_true",
                         help="stop at the next gate after the current approved gate instead of the stage's highest gate")
    iterate.add_argument("--task-timeout", type=int, default=None,
                         help="override each task's agent/command timeout in seconds")
    iterate.add_argument("--max-retries", type=int, default=None,
                         help="override each task's retry_policy.max_retries")
    iterate.set_defaults(func=_cmd_iterate)

    inspect_p = sub.add_parser("inspect", help="read-only inspection views")
    inspect_sub = inspect_p.add_subparsers(dest="inspect_command", required=True)
    inspect_modes_p = inspect_sub.add_parser("modes", help="inspect compiled mode/control surfaces")
    inspect_modes_p.add_argument("--compiled", action="store_true", required=True, help="show read-only five-field compiled mode map")
    inspect_modes_p.add_argument("--json", action="store_true")
    inspect_modes_p.set_defaults(func=_cmd_inspect)

    mode_p = sub.add_parser("mode", help="recommend right-sized execution mode")
    mode_sub = mode_p.add_subparsers(dest="mode_command", required=True)
    mode_recommend_p = mode_sub.add_parser("recommend", help="recommend smoke/probe/source/release/API/waiting mode")
    mode_recommend_p.add_argument("--lane", default="", help="Optional active lane, e.g. data/literature/writing")
    mode_recommend_p.add_argument("--intent", default="", help="Short description of what you are about to do")
    mode_recommend_p.add_argument(
        "--mode",
        default="",
        choices=[
            "",
            "smoke_test",
            "bounded_probe",
            "broad_capture",
            "source_capture",
            "paper_release",
            "expensive_api_run",
            "waiting_on_external_input",
        ],
        help="Explicit mode override to validate and display",
    )
    mode_recommend_p.add_argument("--json", action="store_true")
    mode_recommend_p.set_defaults(func=_cmd_mode_recommend)
    mode_classify_p = mode_sub.add_parser("classify", help="classify task workflow preset before work starts")
    mode_classify_p.add_argument("--task-id", default="", help="Optional AEROS task_id to classify")
    mode_classify_p.add_argument("--lane", default="", help="Optional active lane")
    mode_classify_p.add_argument("--intent", default="", help="Short description of intended work")
    mode_classify_p.add_argument("--json", action="store_true")
    mode_classify_p.set_defaults(func=_cmd_mode_classify)
    mode_compiled_p = mode_sub.add_parser("compiled", help="show read-only five-field compiled mode map")
    mode_compiled_p.add_argument("--json", action="store_true")
    mode_compiled_p.set_defaults(func=_cmd_mode_compiled)

    artifact_p = sub.add_parser("artifact", help="artifact selection helpers")
    artifact_sub = artifact_p.add_subparsers(dest="artifact_command", required=True)
    artifact_stage_p = artifact_sub.add_parser("stage", help="select canonical artifacts while excluding raw staging")
    artifact_stage_p.add_argument("--canonical", action="store_true", help="Required: select canonical outputs only")
    artifact_stage_p.add_argument("--exclude-raw-staging", action="store_true", help="Required: keep raw/staging captures unstaged")
    artifact_stage_p.add_argument("--apply", action="store_true", help="Actually run git add for selected canonical paths")
    artifact_stage_p.add_argument("--json", action="store_true")
    artifact_stage_p.set_defaults(func=_cmd_artifact_stage)

    improve_p = sub.add_parser("improve", help="framework improvement helpers")
    improve_sub = improve_p.add_subparsers(dest="improve_command", required=True)
    improve_harvest_p = improve_sub.add_parser("harvest", help="harvest improvement candidates from local run artifacts")
    improve_harvest_p.add_argument("--project", action="append", default=[], help="project root to include in sync/version harvest; may be repeated")
    improve_harvest_p.add_argument("--write", action="store_true", help="Write outputs/context/improvement_harvest.md")
    improve_harvest_p.add_argument("--json", action="store_true")
    improve_harvest_p.set_defaults(func=_cmd_improve_harvest)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        return _cmd_home(args)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
