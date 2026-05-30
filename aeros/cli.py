"""AEROS runtime CLI.

    aeros run  tasks/discovery/D001_literature_search.yml [--dry-run]
    aeros check tasks/discovery/D001_literature_search.yml
    aeros status
    aeros list-tasks

(Before install you can use `python3 -m aeros.cli ...` identically.)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .runtime.adjudicate import adjudicate, write_selection
from .runtime.checks import run_checks
from .runtime.contract import load_contract
from .runtime.kernel import find_project_root, run_task
from .runtime.state import load_state


def _project_root() -> Path:
    return find_project_root(Path.cwd())


def _cmd_run(args: argparse.Namespace) -> int:
    return run_task(args.contract, dry_run=args.dry_run,
                    max_retries_override=args.max_retries)


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
    print(f"current gate : {state.get('current_gate', '?')}")
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

    lt = sub.add_parser("list-tasks", help="list .yml task contracts in the project")
    lt.set_defaults(func=_cmd_list_tasks)

    adj = sub.add_parser("adjudicate", help="adjudicate design options against data diagnostics (earn the claim)")
    adj.set_defaults(func=_cmd_adjudicate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
