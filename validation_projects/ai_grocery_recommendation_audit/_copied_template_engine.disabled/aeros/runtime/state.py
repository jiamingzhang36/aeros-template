"""Persistent runtime state: task status + agent-call budget.

State lives in aeros_state.yml at the project root so a crash never loses
the record of money/agent-calls already spent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

STATE_FILENAME = "aeros_state.yml"
GATE_ORDER = {f"G{i}": i for i in range(10)}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(project_root: Path) -> Path:
    return project_root / STATE_FILENAME


def load_state(project_root: Path) -> dict[str, Any]:
    path = state_path(project_root)
    if not path.exists():
        return {
            "current_stage": "discovery",
            "current_gate": "G0",
            "gate_status": "open",
            "candidate_stage": "discovery",
            "candidate_gate": "G0",
            "tasks": {},
            "gate_history": [],
            "candidate_gate_history": [],
            "gate_decisions": [],
        }
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("current_stage", "discovery")
    data.setdefault("current_gate", "G0")
    data.setdefault("gate_status", "open")
    data.setdefault("candidate_stage", data.get("current_stage", "discovery"))
    data.setdefault("candidate_gate", data.get("current_gate", "G0"))
    data.setdefault("tasks", {})
    data.setdefault("gate_history", [])
    data.setdefault("candidate_gate_history", [])
    data.setdefault("gate_decisions", [])
    return data


def save_state(project_root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    state_path(project_root).write_text(
        yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def task_entry(state: dict[str, Any], task_id: str) -> dict[str, Any]:
    return state["tasks"].setdefault(
        task_id,
        {"status": "pending", "agent_calls_total": 0, "cost_usd_total": 0.0},
    )


def record_agent_call(state: dict[str, Any], task_id: str, cost_usd: float = 0.0) -> None:
    """Append to the cumulative audit totals. Per-run budget is enforced in the
    kernel against this run's local counters, so re-running a task is never
    blocked by a previous run's spend."""
    entry = task_entry(state, task_id)
    entry["agent_calls_total"] = int(entry.get("agent_calls_total", 0)) + 1
    entry["cost_usd_total"] = round(float(entry.get("cost_usd_total", 0.0)) + cost_usd, 6)
    entry["last_call"] = _now()


def record_run_summary(state: dict[str, Any], task_id: str, *, calls: int,
                       cost_usd: float) -> None:
    """Record the most recent run's per-run spend (what the report shows)."""
    entry = task_entry(state, task_id)
    entry["last_run_calls"] = calls
    entry["last_run_cost_usd"] = round(cost_usd, 6)


def set_status(state: dict[str, Any], task_id: str, status: str) -> None:
    entry = task_entry(state, task_id)
    entry["status"] = status
    if status == "passed":
        # Timestamp used for make-style staleness: a task is stale if any
        # dependency passed more recently than it did.
        entry["passed_at"] = _now()


def recompute_candidate_gate(state: dict[str, Any], task_gates: dict[str, str]) -> str:
    """Derive candidate_gate from currently-passed tasks (can go UP or DOWN).

    candidate = the highest gate whose task is passed. If a task is reset or
    invalidated, the candidate drops accordingly -- fixing the monotonic-only
    bug where a withdrawn design still left the candidate at G3.
    """
    tasks = state.get("tasks", {})
    best = "G0"
    for tid, gate in task_gates.items():
        if not gate:
            continue
        if tasks.get(tid, {}).get("status") == "passed" and _gate_rank(gate) > _gate_rank(best):
            best = gate
    prev = str(state.get("candidate_gate", "G0"))
    state["candidate_gate"] = best
    if best != prev:
        state.setdefault("candidate_gate_history", []).append(
            {"at": _now(), "gate": best, "task_id": "recompute",
             "reason": "derived_from_passed_tasks"}
        )
    return best


def _gate_rank(gate: str) -> int:
    return GATE_ORDER.get(str(gate).split()[0], -1)


def advance_gate(state: dict[str, Any], *, stage: str, gate: str,
                 task_id: str, reason: str) -> None:
    """Record the highest gate suggested by completed task progress.

    This is intentionally not the formal current_gate. Formal gate movement is
    a human/criteria decision and happens through approve_gate().
    """
    if not gate:
        return
    candidate = str(state.get("candidate_gate", state.get("current_gate", "G0")))
    if _gate_rank(gate) < _gate_rank(candidate):
        return
    state["candidate_stage"] = stage
    state["candidate_gate"] = gate
    state.setdefault("candidate_gate_history", []).append(
        {
            "at": _now(),
            "stage": stage,
            "gate": gate,
            "task_id": task_id,
            "reason": reason,
        }
    )


def approve_gate(state: dict[str, Any], *, stage: str, gate: str,
                 owner: str, note: str) -> dict[str, Any]:
    """Record a human approval and advance to the approved gate if needed."""
    decision = {
        "at": _now(),
        "stage": stage,
        "gate": gate,
        "decision": "approve",
        "owner": owner,
        "note": note,
    }
    state["current_stage"] = stage
    state["current_gate"] = gate
    state["gate_status"] = "approved"
    state["candidate_stage"] = stage
    state["candidate_gate"] = gate
    state.setdefault("gate_decisions", []).append(decision)
    state.setdefault("gate_history", []).append(
        {
            "at": decision["at"],
            "stage": stage,
            "gate": gate,
            "task_id": "human_gate",
            "reason": "human_approved",
        }
    )
    return decision


def block_gate(state: dict[str, Any], *, stage: str, gate: str,
               owner: str, reason: str) -> dict[str, Any]:
    """Record a human block without marking the gate approved."""
    decision = {
        "at": _now(),
        "stage": stage,
        "gate": gate,
        "decision": "block",
        "owner": owner,
        "note": reason,
    }
    state["gate_status"] = "blocked"
    state["blocked_stage"] = stage
    state["blocked_gate"] = gate
    state.setdefault("gate_decisions", []).append(decision)
    state.setdefault("gate_history", []).append(
        {
            "at": decision["at"],
            "stage": stage,
            "gate": gate,
            "task_id": "human_gate",
            "reason": "human_blocked",
        }
    )
    return decision
