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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(project_root: Path) -> Path:
    return project_root / STATE_FILENAME


def load_state(project_root: Path) -> dict[str, Any]:
    path = state_path(project_root)
    if not path.exists():
        return {"current_gate": "G0", "tasks": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("tasks", {})
    return data


def save_state(project_root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    state_path(project_root).write_text(
        yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def task_entry(state: dict[str, Any], task_id: str) -> dict[str, Any]:
    return state["tasks"].setdefault(
        task_id, {"status": "pending", "agent_calls_used": 0, "attempts": 0}
    )


def budget_remaining(state: dict[str, Any], task_id: str, max_calls: int) -> int:
    return max_calls - int(task_entry(state, task_id).get("agent_calls_used", 0))


def record_agent_call(state: dict[str, Any], task_id: str) -> None:
    entry = task_entry(state, task_id)
    entry["agent_calls_used"] = int(entry.get("agent_calls_used", 0)) + 1
    entry["attempts"] = int(entry.get("attempts", 0)) + 1
    entry["last_call"] = _now()


def set_status(state: dict[str, Any], task_id: str, status: str) -> None:
    task_entry(state, task_id)["status"] = status
