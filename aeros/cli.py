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
import os
import sys
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

import yaml

from .runtime.adjudicate import adjudicate, feasibility, write_selection
from .runtime.adoption import AdoptionArgs, run_adoption
from .runtime.checks import run_checks
from .runtime.collection import collect_prompt_grid, resolve_config
from .runtime.contract import load_contract
from .runtime.controller import run_iteration
from .runtime import identity
from .runtime.data_backfill import BackfillArgs, run_data_backfill
from .runtime.decision_packet import write_decision_packet
from .runtime.init_project import init_project
from .runtime.kernel import find_project_root, run_pipeline, run_task
from .runtime.kernel import _record_task_fingerprints, _task_gates, discover_contracts
from .runtime.milestones import format_roadmap, format_simple_status
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


def _cmd_run(args: argparse.Namespace) -> int:
    return run_task(args.contract, dry_run=args.dry_run,
                    max_retries_override=args.max_retries,
                    task_timeout_override=args.task_timeout)


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
    contract = load_contract(args.contract)
    root = find_project_root(Path(args.contract).resolve())
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

    state = load_state(root)
    set_status(state, contract.task_id, "passed")
    all_contracts = discover_contracts(root)
    _record_task_fingerprints(state, contract, root, all_contracts)
    recompute_candidate_gate(state, _task_gates(all_contracts))
    record_run_summary(state, contract.task_id, calls=0, cost_usd=0.0)
    save_state(root, state)
    print(f"recovered {contract.task_id} from {Path(path).relative_to(root)}")
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

    # 1. Deck must be committed by an approver (same trust anchor as approve).
    if identity.enforcement_enabled(root):
        granted, reason = identity.approved_by_human(path, root)
        if not granted and not args.force:
            print(f"REFUSED: plan deck is not human-granted ({reason}).")
            print(f"  An approver must commit {path.relative_to(root)} under an approved git identity.")
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

    # Trust anchor: the agent can REQUEST approval but cannot GRANT it. A grant
    # only counts when the approval artifact is committed by an approver_identity
    # (see harness/permissions.yml). The agent, committing under agent_identity,
    # physically cannot produce a passing artifact.
    approver_committer = ""
    if identity.enforcement_enabled(root):
        artifact = identity.approval_artifact_path(root, args.gate)
        granted, reason = identity.approved_by_human(artifact, root)
        if not granted:
            if not args.force:
                print(f"REFUSED: {args.gate} is not human-granted ({reason}).")
                print(f"  An approver must review and commit {artifact.relative_to(root)} "
                      f"under an approved git identity.")
                print(f"  Create the request with:  aeros gate request \"{args.gate}\"")
                print("  Then (as the human):       git add <artifact> && git commit")
                print("  Override with --force (logged) only if you accept the audit trail gap.")
                return 3
            note = f"[FORCED past human-grant anchor: {reason}] " + note
            print(f"WARNING: forcing approval without a committed human grant: {reason}")
        else:
            approver_committer = reason.replace("approved by ", "")
            print(f"human grant verified: {reason}")

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
    )


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


def _cmd_roadmap(args: argparse.Namespace) -> int:
    root = _project_root()
    print(format_roadmap(root))
    return 0


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aeros", description="AEROS runtime")
    sub = parser.add_subparsers(dest="command", required=True)

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

    run = sub.add_parser("run", help="run a single task contract through the agent loop")
    run.add_argument("contract", help="path to a task contract .yml")
    run.add_argument("--dry-run", action="store_true",
                     help="print the agent prompt and planned checks; do not call the agent")
    run.add_argument("--max-retries", type=int, default=None,
                     help="override the contract's retry_policy.max_retries")
    run.add_argument("--task-timeout", type=int, default=None,
                     help="override this task's agent/command timeout in seconds")
    run.set_defaults(func=_cmd_run)

    chk = sub.add_parser("check", help="run a contract's checks without calling the agent")
    chk.add_argument("contract", help="path to a task contract .yml")
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

    state_parser = sub.add_parser("state", help="inspect or clean runtime state")
    state_sub = state_parser.add_subparsers(dest="state_command", required=True)
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
    data_backfill.set_defaults(func=_cmd_data_backfill)

    iterate = sub.add_parser("iterate", help="run the research controller until the next human gate")
    iterate.add_argument("--stage", default="discovery", choices=["discovery", "execution"],
                         help="stage to iterate (default: discovery)")
    iterate.add_argument("--dry-run", action="store_true",
                         help="show the controller plan; do not run tasks or write packets")
    iterate.add_argument("--to-next-gate", action="store_true",
                         help="stop at the next gate after the current approved gate instead of the stage's highest gate")
    iterate.add_argument("--task-timeout", type=int, default=None,
                         help="override each task's agent/command timeout in seconds")
    iterate.add_argument("--max-retries", type=int, default=None,
                         help="override each task's retry_policy.max_retries")
    iterate.set_defaults(func=_cmd_iterate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
