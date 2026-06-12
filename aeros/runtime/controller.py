"""AEROS research controller: choose the next automated iteration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from . import state as state_mod
from .adjudicate import adjudicate, write_selection
from .decision_packet import write_decision_packet
from .kernel import (
    _stale_reason,
    _active_gate_ranks,
    _contract_block_reason,
    _task_gates,
    discover_contracts,
    run_pipeline,
    topo_order,
)

print = partial(print, flush=True)


@dataclass(frozen=True)
class IterateStep:
    task_id: str
    gate: str
    status: str
    action: str
    stale_reason: str = ""


@dataclass(frozen=True)
class IteratePlan:
    stage: str
    target_gate: str
    steps: list[IterateStep]
    can_run: bool
    mode: str = "stage-gate"
    reason: str = ""


def _highest_gate(contracts: dict, default: str = "G0") -> str:
    best = default
    for contract, _path in contracts.values():
        gate = contract.gate or ""
        if state_mod._gate_rank(gate) > state_mod._gate_rank(best):
            best = gate
    return best


def _execution_allowed(state: dict) -> bool:
    # Execution is allowed once a human has approved the G3 (design/claim) gate.
    # Check the gate HISTORY, not just the latest gate_status: once execution
    # begins, the pipeline auto-advances mechanical gates and flips gate_status
    # to "auto_advanced", which must not retroactively revoke the standing G3
    # approval on a later run.
    g3_rank = state_mod._gate_rank("G3")
    for entry in state.get("gate_history", []) or []:
        if (str(entry.get("reason", "")).strip() == "human_approved"
                and state_mod._gate_rank(str(entry.get("gate", "G0"))) >= g3_rank):
            return True
    return (
        state.get("gate_status") in {"approved", "blocked"}
        and state_mod._gate_rank(str(state.get("current_gate", "G0"))) >= g3_rank
    )


def _next_gate_after(current_gate: str, contracts: dict) -> str:
    current_rank = state_mod._gate_rank(current_gate)
    candidates = sorted(
        {
            contract.gate
            for contract, _path in contracts.values()
            if contract.gate and state_mod._gate_rank(contract.gate) > current_rank
        },
        key=state_mod._gate_rank,
    )
    return candidates[0] if candidates else _highest_gate(contracts)


def _contracts_through_gate(contracts: dict, target_gate: str) -> dict:
    target_rank = state_mod._gate_rank(target_gate)
    return {
        task_id: record
        for task_id, record in contracts.items()
        if state_mod._gate_rank(record[0].gate or "") <= target_rank
    }


def _with_dependency_closure(selected: dict, all_contracts: dict) -> dict:
    """Include dependencies even when their gate is beyond the target gate.

    Some discovery artifacts are logically upstream even if their human gate is
    later (for example, variable construction can depend on design options).
    A next-gate run should not execute a task with missing prerequisites.
    """
    out = dict(selected)
    changed = True
    while changed:
        changed = False
        for contract, _path in list(out.values()):
            for dep in contract.depends_on:
                if dep in all_contracts and dep not in out:
                    out[dep] = all_contracts[dep]
                    changed = True
    return out


def build_iterate_plan(
    project_root: Path,
    stage: str = "discovery",
    *,
    to_next_gate: bool = False,
) -> IteratePlan:
    state = state_mod.load_state(project_root)
    contracts = discover_contracts(project_root, stage)
    all_contracts = discover_contracts(project_root)
    mode = "next-gate" if to_next_gate else "stage-gate"
    if not contracts:
        return IteratePlan(stage=stage, target_gate="G0", steps=[], can_run=False,
                           mode=mode,
                           reason=f"no task contracts for stage {stage!r}")

    if stage == "execution" and not _execution_allowed(state):
        return IteratePlan(stage=stage, target_gate="G3", steps=[], can_run=False,
                           mode=mode,
                           reason="execution requires human-approved G3")

    if stage == "execution":
        from .kernel import _foundation_ok
        ok_foundation, unmet = _foundation_ok(project_root)
        if not ok_foundation:
            reason = ("execution blocked: discovery-foundation gate(s) G0-G3 not met — "
                      + "; ".join(u.split(":", 1)[0] if ":" in u else u for u in unmet[:4]))
            return IteratePlan(stage=stage, target_gate="G3", steps=[], can_run=False,
                               mode=mode, reason=reason)

    target_gate = (
        _next_gate_after(str(state.get("current_gate", "G0")), contracts)
        if to_next_gate else _highest_gate(contracts)
    )
    if to_next_gate:
        runnable_contracts = _with_dependency_closure(
            _contracts_through_gate(contracts, target_gate),
            all_contracts,
        )
    else:
        runnable_contracts = contracts
    active_ranks = _active_gate_ranks(project_root)
    if active_ranks is not None:
        runnable_contracts = {
            task_id: record
            for task_id, record in runnable_contracts.items()
            if state_mod._gate_rank(record[0].gate or "") in active_ranks
        }
        runnable_contracts = _with_dependency_closure(runnable_contracts, all_contracts)
    probe_state = deepcopy(state)
    steps: list[IterateStep] = []
    for task_id in topo_order(runnable_contracts):
        contract, _path = runnable_contracts[task_id]
        entry = state_mod.task_entry(probe_state, task_id)
        status = str(entry.get("status", "pending"))
        stale = ""
        action = "run"
        blocked_reason = _contract_block_reason(contract)
        if blocked_reason:
            action = "blocked"
            stale = blocked_reason
            steps.append(IterateStep(
                task_id=task_id,
                gate=contract.gate or "?",
                status=status,
                action=action,
                stale_reason=stale,
            ))
            continue
        if status == "passed":
            stale = _stale_reason(probe_state, contract, project_root, all_contracts)
            action = "rerun" if stale else "skip"
        elif status in {"running", "stale", "escalated", "failed", "dry_run"}:
            action = "run"
        steps.append(IterateStep(
            task_id=task_id,
            gate=contract.gate or "?",
            status=status,
            action=action,
            stale_reason=stale,
        ))
    return IteratePlan(stage=stage, target_gate=target_gate, steps=steps, can_run=True, mode=mode)


def format_iterate_plan(plan: IteratePlan) -> str:
    lines = [
        f"[iterate] stage: {plan.stage}",
        f"[iterate] mode: {plan.mode}",
        f"[iterate] target gate: {plan.target_gate}",
    ]
    if not plan.can_run:
        lines.append(f"[iterate] cannot run: {plan.reason}")
        return "\n".join(lines)
    if not plan.steps:
        lines.append("[iterate] no tasks planned")
        return "\n".join(lines)
    lines.append("[iterate] task plan:")
    for step in plan.steps:
        stale = f" ({step.stale_reason})" if step.stale_reason else ""
        lines.append(
            f"  - {step.task_id:32s} gate={step.gate:3s} status={step.status:10s} action={step.action}{stale}"
        )
    lines.append(f"[iterate] will stop for human packet at {plan.target_gate}")
    return "\n".join(lines)


def run_iteration(
    project_root: Path,
    stage: str = "discovery",
    *,
    dry_run: bool = False,
    to_next_gate: bool = False,
    task_timeout_override: int | None = None,
    max_retries_override: int | None = None,
) -> int:
    plan = build_iterate_plan(project_root, stage, to_next_gate=to_next_gate)
    print(format_iterate_plan(plan))
    if not plan.can_run:
        if dry_run:
            return 2
        packet = write_decision_packet(project_root, plan.target_gate, stage=stage)
        print(f"[iterate] decision packet -> {packet.relative_to(project_root)}")
        return 2
    if dry_run:
        return 0

    rc = run_pipeline(
        project_root,
        stage,
        dry_run=False,
        stop_gate=plan.target_gate if to_next_gate else None,
        task_timeout_override=task_timeout_override,
        max_retries_override=max_retries_override,
    )
    if rc != 0:
        packet = write_decision_packet(project_root, plan.target_gate, stage=stage)
        print(f"[iterate] stopped; decision packet -> {packet.relative_to(project_root)}")
        return rc

    if stage == "discovery":
        write_selection(project_root, adjudicate(project_root))

    packet = write_decision_packet(project_root, plan.target_gate, stage=stage)
    print(f"[iterate] stopped for human gate; decision packet -> {packet.relative_to(project_root)}")
    print("[iterate] no gate was approved automatically")
    return 0
