"""Load and validate an AEROS task contract (YAML)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REQUIRED_KEYS = ("task_id", "stage", "checks", "allowed_outputs")


@dataclass
class Contract:
    task_id: str
    stage: str
    gate: str
    goal: str
    inputs: list[str]
    allowed_outputs: list[str]
    forbidden_actions: list[str]
    checks: list[str]
    output_contract: dict[str, Any]
    max_retries: int
    escalate_if: list[str]
    max_agent_calls: int
    max_dollars: float
    prompt_template_file: str
    correction_scopes: list[str]
    raw: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None


def load_contract(path: str | Path) -> Contract:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"contract not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"contract is not a mapping: {path}")

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"contract {path} missing required keys: {missing}")

    retry = data.get("retry_policy", {}) or {}
    budget = data.get("budget", {}) or {}
    return Contract(
        task_id=str(data["task_id"]),
        stage=str(data["stage"]),
        gate=str(data.get("gate", "") or ""),
        goal=str(data.get("goal", "")).strip(),
        inputs=list(data.get("inputs", []) or []),
        allowed_outputs=list(data["allowed_outputs"]),
        forbidden_actions=list(data.get("forbidden_actions", []) or []),
        checks=list(data["checks"]),
        output_contract=dict(data.get("output_contract", {}) or {}),
        max_retries=int(retry.get("max_retries", 1)),
        escalate_if=list(data.get("escalate_if", []) or []),
        max_agent_calls=int(budget.get("max_agent_calls", 3)),
        max_dollars=float(budget.get("max_dollars", 5.0)),
        prompt_template_file=str(data.get("prompt_template_file", "") or ""),
        correction_scopes=list(data.get("correction_scopes", []) or [])
        or ["all", str(data.get("stage", ""))],
        raw=data,
        path=path,
    )
