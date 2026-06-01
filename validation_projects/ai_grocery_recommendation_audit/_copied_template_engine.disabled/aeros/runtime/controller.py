"""AEROS research controller: choose the next automated iteration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from . import state as state_mod
from .adjudicate import adjudicate, write_selection
from .decision_packet import write_decision_packet
from .kernel import (
    _stale_reason,
    _task_gates,
    discover_contracts,
    run_pipeline,
    topo_order,
)


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
    return (
        state.get("gate_status") == "approved"
        and state_mod._gate_rank(str(state.get("current_gate", "G0"))) >= state_mod._gate_rank("G3")
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

    target_gate = (
        _next_gate_after(str(state.get("current_gate", "G0")), contracts)
        if to_next_gate else _highest_gate(contracts)
    )
    runnable_contracts = _contracts_through_gate(contracts, target_gate) if to_next_gate else contracts
    probe_state = deepcopy(state)
    steps: list[IterateStep] = []
    for task_id in topo_order(runnable_contracts):
        contract, _path = runnable_contracts[task_id]
        entry = state_mod.task_entry(probe_state, task_id)
        status = str(entry.get("status", "pending"))
        stale = ""
        action = "run"
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

    rc = run_pipeline(project_root, stage, dry_run=False, stop_gate=plan.target_gate if to_next_gate else None)
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
