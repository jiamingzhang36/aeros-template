"""Compressed milestone dashboard for AEROS runtime state.

Milestones are a view-only layer. They do not approve gates, skip checks, or
change iteration semantics; they only make the existing G0-G13 machinery easier
to read during day-to-day work.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .controller import build_iterate_plan
from .kernel import discover_contracts
from .state import load_state


DEFAULT_PROFILE = {
    "profiles": {
        "milestone_view": {
            "view_only": True,
            "milestones": [
                {"id": "M1", "name": "Intake & Discovery", "gates": ["G0", "G1", "G2", "G3"]},
                {"id": "M2", "name": "Design & Execution Lock", "gates": ["G4", "G5", "G6"]},
                {"id": "M3", "name": "Claim Discipline", "gates": ["G7", "G8", "G12"]},
                {"id": "M4", "name": "Paper & Replication Package", "gates": ["G9", "G10"]},
                {"id": "M5", "name": "Provider & Compliance Release", "gates": ["G11", "G13"]},
            ],
        }
    }
}


def _gate_rank(gate: str) -> int:
    match = re.match(r"^G(\d+)$", str(gate).split()[0])
    return int(match.group(1)) if match else -1


def _gate_id(gate: str | None) -> str:
    if not gate:
        return "G0"
    match = re.match(r"^(G\d+)", str(gate).strip())
    return match.group(1) if match else str(gate).strip()


def _load_profiles(project_root: Path) -> dict[str, Any]:
    path = project_root / "harness" / "gate_profiles.yml"
    if not path.exists():
        path = Path(__file__).resolve().parents[2] / "harness" / "gate_profiles.yml"
    if not path.exists():
        return DEFAULT_PROFILE
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else DEFAULT_PROFILE


def _milestones(project_root: Path) -> list[dict[str, Any]]:
    profiles = _load_profiles(project_root).get("profiles", {})
    profile = profiles.get("milestone_view", {})
    milestones = profile.get("milestones", [])
    return milestones if isinstance(milestones, list) else DEFAULT_PROFILE["profiles"]["milestone_view"]["milestones"]


def milestone_for_gate(project_root: Path, gate: str | None) -> dict[str, Any]:
    gid = _gate_id(gate)
    rank = _gate_rank(gid)
    milestones = _milestones(project_root)
    for milestone in milestones:
        gates = [str(g) for g in milestone.get("gates", [])]
        if gid in gates:
            return milestone
    ranked = [
        (max((_gate_rank(str(g)) for g in milestone.get("gates", [])), default=-1), milestone)
        for milestone in milestones
    ]
    ranked = [item for item in ranked if item[0] <= rank]
    return max(ranked, key=lambda item: item[0])[1] if ranked else milestones[0]


def _milestone_label(milestone: dict[str, Any]) -> str:
    return f"{milestone.get('id', '?')} {milestone.get('name', '')}".strip()


def _stage_for_simple_status(state: dict[str, Any]) -> str:
    stage = str(state.get("current_stage", "discovery"))
    return stage if stage in {"discovery", "execution"} else "discovery"


def _next_action(project_root: Path, state: dict[str, Any]) -> str:
    status = str(state.get("gate_status", "open"))
    current_gate = _gate_id(state.get("current_gate"))
    candidate_gate = _gate_id(state.get("candidate_gate"))
    if status == "blocked":
        blocked_gate = state.get("blocked_gate") or current_gate
        return f"human gate is blocked at {blocked_gate}; revise artifacts, then record a new gate decision"
    if _gate_rank(candidate_gate) > _gate_rank(current_gate):
        return f"review candidate {candidate_gate}; run `aeros gate packet {candidate_gate}` then approve/block"

    stage = _stage_for_simple_status(state)
    try:
        plan = build_iterate_plan(project_root, stage=stage)
    except Exception as exc:  # noqa: BLE001
        return f"could not build iterate plan: {exc}"
    if not plan.can_run:
        return plan.reason or "no runnable task plan"
    stale = [s for s in plan.steps if s.action == "rerun"]
    runnable = [s for s in plan.steps if s.action == "run"]
    if stale:
        return f"rerun {len(stale)} stale task(s) with `aeros iterate --stage {stage}`"
    if runnable:
        return f"continue automation with `aeros iterate --stage {stage}`"
    return f"all planned {stage} tasks are passed; generate a decision packet or choose the next stage"


def format_simple_status(project_root: Path) -> str:
    state = load_state(project_root)
    current_gate = _gate_id(state.get("current_gate"))
    candidate_gate = _gate_id(state.get("candidate_gate"))
    current_milestone = milestone_for_gate(project_root, current_gate)
    candidate_milestone = milestone_for_gate(project_root, candidate_gate)
    tasks = state.get("tasks", {})
    stale_count = sum(1 for entry in tasks.values() if entry.get("status") == "stale")
    failed_count = sum(1 for entry in tasks.values() if entry.get("status") in {"failed", "escalated"})

    lines = [
        f"project root : {project_root}",
        f"milestone    : {_milestone_label(current_milestone)}",
        f"current gate : {current_gate} / {state.get('gate_status', 'open')}",
        f"candidate   : {candidate_gate} ({_milestone_label(candidate_milestone)})",
        f"tasks        : {len(tasks)} tracked"
    ]
    if stale_count or failed_count:
        lines.append(f"attention    : {stale_count} stale, {failed_count} failed/escalated")
    else:
        lines.append("attention    : none flagged in runtime state")
    lines.append(f"next action  : {_next_action(project_root, state)}")
    return "\n".join(lines)


def format_roadmap(project_root: Path) -> str:
    state = load_state(project_root)
    current_gate = _gate_id(state.get("current_gate"))
    candidate_gate = _gate_id(state.get("candidate_gate"))
    current_rank = _gate_rank(current_gate)
    candidate_rank = _gate_rank(candidate_gate)
    gate_status = str(state.get("gate_status", "open"))
    contracts = discover_contracts(project_root)
    task_counts: dict[str, int] = {}
    passed_counts: dict[str, int] = {}
    tasks = state.get("tasks", {})
    for task_id, (contract, _path) in contracts.items():
        gate = _gate_id(contract.gate)
        task_counts[gate] = task_counts.get(gate, 0) + 1
        if tasks.get(task_id, {}).get("status") == "passed":
            passed_counts[gate] = passed_counts.get(gate, 0) + 1

    lines = [
        "AEROS roadmap (milestone view; internal gates/checks unchanged)",
        f"current: {current_gate} / {gate_status}    candidate: {candidate_gate}",
    ]
    for milestone in _milestones(project_root):
        gates = [_gate_id(str(g)) for g in milestone.get("gates", [])]
        max_rank = max((_gate_rank(g) for g in gates), default=-1)
        if current_gate in gates:
            mark = "CURRENT"
        elif candidate_gate in gates and candidate_rank > current_rank:
            mark = "CANDIDATE"
        elif max_rank <= current_rank and gate_status == "approved":
            mark = "APPROVED"
        elif gate_status == "blocked" and state.get("blocked_gate") in gates:
            mark = "BLOCKED"
        else:
            mark = "PENDING"
        totals = sum(task_counts.get(g, 0) for g in gates)
        passed = sum(passed_counts.get(g, 0) for g in gates)
        progress = f"{passed}/{totals} task(s) passed" if totals else "no task contracts"
        lines.append(
            f"[{mark:9s}] {_milestone_label(milestone):38s} gates={','.join(gates):18s} {progress}"
        )
    return "\n".join(lines)
