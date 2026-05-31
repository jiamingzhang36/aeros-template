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
import sys
from pathlib import Path

from .runtime.adjudicate import adjudicate, feasibility, write_selection
from .runtime.checks import run_checks
from .runtime.contract import load_contract
from .runtime.init_project import init_project
from .runtime.kernel import find_project_root, run_pipeline, run_task
from .runtime.state import approve_gate, block_gate, load_state, save_state


def _project_root() -> Path:
    return find_project_root(Path.cwd())


def _cmd_run(args: argparse.Namespace) -> int:
    return run_task(args.contract, dry_run=args.dry_run,
                    max_retries_override=args.max_retries)


def _cmd_init(args: argparse.Namespace) -> int:
    root = init_project(args.path, force=args.force)
    print(f"initialized AEROS project at {root}")
    return 0


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


def _cmd_status(args: argparse.Namespace) -> int:
    root = _project_root()
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


def _cmd_gate_approve(args: argparse.Namespace) -> int:
    root = _project_root()

    # A human gate is a stamp ON TOP of satisfied criteria, not instead of them.
    # Verify the gate's exit criteria before allowing approval.
    sys.path.insert(0, str(root / "checks"))
    try:
        from check_gate_exit import evaluate_through_gate  # noqa: E402
        ok, failures = evaluate_through_gate(args.gate, project_root=str(root))
    except Exception as exc:  # noqa: BLE001
        ok, failures = False, [f"could not evaluate gate criteria: {exc}"]

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

    state = load_state(root)
    decision = approve_gate(
        state,
        stage=args.stage,
        gate=args.gate,
        owner=args.owner or "",
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
    rc = run_pipeline(root, args.stage, dry_run=args.dry_run)
    if rc != 0 or args.dry_run:
        return rc
    # after the stage runs, adjudicate designs and print the feasibility verdict
    print("[pipeline] adjudicating designs against data diagnostics...")
    write_selection(root, adjudicate(root))
    return _cmd_feasibility(args)


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

    run = sub.add_parser("run", help="run a single task contract through the agent loop")
    run.add_argument("contract", help="path to a task contract .yml")
    run.add_argument("--dry-run", action="store_true",
                     help="print the agent prompt and planned checks; do not call the agent")
    run.add_argument("--max-retries", type=int, default=None,
                     help="override the contract's retry_policy.max_retries")
    run.set_defaults(func=_cmd_run)

    chk = sub.add_parser("check", help="run a contract's checks without calling the agent")
    chk.add_argument("contract", help="path to a task contract .yml")
    chk.set_defaults(func=_cmd_check)

    st = sub.add_parser("status", help="show runtime state (gate, per-task status, budget)")
    st.set_defaults(func=_cmd_status)

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

    gate_block = gate_sub.add_parser("block", help="record a human gate block")
    gate_block.add_argument("gate", help="gate to block, e.g. G6")
    gate_block.add_argument("--stage", default="execution", help="stage name")
    gate_block.add_argument("--owner", default="", help="human owner / blocker")
    gate_block.add_argument("--reason", default="", help="blocking rationale")
    gate_block.set_defaults(func=_cmd_gate_block)

    lt = sub.add_parser("list-tasks", help="list .yml task contracts in the project")
    lt.set_defaults(func=_cmd_list_tasks)

    adj = sub.add_parser("adjudicate", help="adjudicate design options against data diagnostics (earn the claim)")
    adj.set_defaults(func=_cmd_adjudicate)

    feas = sub.add_parser("feasibility", help="G1-G3 feasibility verdict (data + variables + viable design)")
    feas.set_defaults(func=_cmd_feasibility)

    pipe = sub.add_parser("pipeline", help="run a stage's tasks in dependency order, then adjudicate + feasibility")
    pipe.add_argument("--stage", default="discovery", help="stage to run (default: discovery)")
    pipe.add_argument("--dry-run", action="store_true", help="show the ordered plan; do not run agents")
    pipe.set_defaults(func=_cmd_pipeline)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
