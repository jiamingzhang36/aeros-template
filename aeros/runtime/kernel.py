"""The AEROS runtime loop: contract -> agent -> checks -> retry/escalate -> state."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import state as state_mod
from .agent import build_prompt, run_agent
from .checks import format_feedback, run_checks
from .contract import Contract, load_contract
from .report import AttemptRecord, RunRecord, write_run_report


def find_project_root(start: Path) -> Path:
    """Walk up from a contract path to the dir containing project_manifest.yml."""
    for parent in [start, *start.parents]:
        if (parent / "project_manifest.yml").exists():
            return parent
    raise FileNotFoundError(
        "could not locate project root (no project_manifest.yml above "
        f"{start})"
    )


def _read_inputs(project_root: Path, contract: Contract) -> str:
    blocks: list[str] = []
    for rel in contract.inputs:
        p = project_root / rel
        if p.exists():
            blocks.append(f"--- {rel} ---\n{p.read_text(encoding='utf-8')}")
        else:
            blocks.append(f"--- {rel} (MISSING) ---")
    return "\n\n".join(blocks)


def _escalate(project_root: Path, contract: Contract, feedback: str) -> Path:
    out_dir = project_root / "decisions" / "escalations"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{contract.task_id}.md"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(
        f"# Escalation: {contract.task_id}\n\n"
        f"Raised: {stamp}\n\n"
        f"## Why\nAutomated retries exhausted; checks still failing.\n\n"
        f"## Last check feedback\n\n{feedback or '(no structured feedback)'}\n\n"
        f"## Human options\n- approve (accept current state)\n"
        f"- revise: <instruction>\n- pause\n- drop\n",
        encoding="utf-8",
    )
    return path


def run_task(contract_path: str | Path, *, dry_run: bool = False,
             max_retries_override: int | None = None) -> int:
    contract = load_contract(contract_path)
    project_root = find_project_root(Path(contract_path).resolve())
    state = state_mod.load_state(project_root)
    state_mod.set_status(state, contract.task_id, "running")

    max_retries = (max_retries_override if max_retries_override is not None
                   else contract.max_retries)
    inputs_text = _read_inputs(project_root, contract)
    feedback: str | None = None
    attempts_log: list[AttemptRecord] = []

    def _finish(status: str) -> None:
        """Persist the run report on both pass and escalate."""
        run = RunRecord(
            contract=contract, final_status=status, attempts=attempts_log,
            agent_calls_used=state_mod.task_entry(state, contract.task_id).get(
                "agent_calls_used", 0),
        )
        report_path = write_run_report(project_root, run)
        print(f"[kernel] run report -> {report_path.relative_to(project_root)}")

    for attempt in range(max_retries + 1):
        remaining = state_mod.budget_remaining(state, contract.task_id, contract.max_agent_calls)
        if remaining <= 0:
            print(f"[kernel] budget exhausted ({contract.max_agent_calls} agent calls). Escalating.")
            break

        prompt = build_prompt(contract, inputs_text, feedback)

        if dry_run:
            print("=" * 70)
            print(f"[DRY RUN] task={contract.task_id} attempt={attempt + 1} "
                  f"budget_remaining={remaining}")
            print("=" * 70)
            print(prompt)
            print("=" * 70)
            print(f"[DRY RUN] would run: claude -p <prompt>  (cwd={project_root})")
            print(f"[DRY RUN] would then run checks: {contract.checks}")
            state_mod.set_status(state, contract.task_id, "dry_run")
            state_mod.save_state(project_root, state)
            return 0

        print(f"[kernel] attempt {attempt + 1}/{max_retries + 1}: invoking agent...")
        state_mod.record_agent_call(state, contract.task_id)
        state_mod.save_state(project_root, state)  # persist BEFORE the call (crash-safe)

        result = run_agent(prompt, project_root)
        if not result.ok:
            print(f"[kernel] agent error: {result.error}")
            attempts_log.append(AttemptRecord(
                attempt=attempt + 1, agent_ok=False, agent_error=result.error,
                checks=[], feedback="",
            ))
            feedback = f"Agent invocation failed: {result.error}"
            continue

        passed, results = run_checks(project_root, contract.checks)
        for r in results:
            print(f"[kernel]   check {r.name}: {'PASS' if r.passed else 'FAIL'}")

        attempt_feedback = "" if passed else format_feedback(results)
        attempts_log.append(AttemptRecord(
            attempt=attempt + 1, agent_ok=True, agent_error="",
            checks=[(r.name, r.passed, r.failures) for r in results],
            feedback=attempt_feedback,
        ))

        if passed:
            state_mod.set_status(state, contract.task_id, "passed")
            state_mod.save_state(project_root, state)
            print(f"[kernel] task {contract.task_id} PASSED.")
            _finish("passed")
            return 0

        feedback = attempt_feedback

    path = _escalate(project_root, contract, feedback or "")
    state_mod.set_status(state, contract.task_id, "escalated")
    state_mod.save_state(project_root, state)
    print(f"[kernel] task {contract.task_id} ESCALATED -> {path}")
    _finish("escalated")
    return 2
