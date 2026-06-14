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
    automation_class: str
    evidence_receipt_required: bool
    receipt_path: str
    gate_status: str
    goal: str
    inputs: list[str]
    allowed_outputs: list[str]
    forbidden_actions: list[str]
    checks: list[str]
    allowed_skills: list[str]
    recommended_skills: list[str]
    output_contract: dict[str, Any]
    max_retries: int
    escalate_if: list[str]
    max_agent_calls: int
    max_dollars: float
    prompt_template_file: str
    correction_scopes: list[str]
    depends_on: list[str]
    timeout_seconds: int
    run_command: list[str]
    run_cwd: str
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
    run = data.get("run", {}) or {}
    return Contract(
        task_id=str(data["task_id"]),
        stage=str(data["stage"]),
        gate=str(data.get("gate", "") or ""),
        automation_class=str(data.get("automation_class", "auto_rerunnable") or "auto_rerunnable"),
        evidence_receipt_required=bool(data.get("evidence_receipt_required", False)),
        receipt_path=str(data.get("receipt_path", "") or ""),
        gate_status=str(data.get("gate_status", "pending") or "pending"),
        goal=str(data.get("goal", "")).strip(),
        inputs=list(data.get("inputs", []) or []),
        allowed_outputs=list(data["allowed_outputs"]),
        forbidden_actions=list(data.get("forbidden_actions", []) or []),
        checks=list(data["checks"]),
        allowed_skills=list(data.get("allowed_skills", []) or []),
        recommended_skills=list(data.get("recommended_skills", []) or []),
        output_contract=dict(data.get("output_contract", {}) or {}),
        max_retries=int(retry.get("max_retries", 1)),
        escalate_if=list(data.get("escalate_if", []) or []),
        max_agent_calls=int(budget.get("max_agent_calls", 3)),
        max_dollars=float(budget.get("max_dollars", 5.0)),
        prompt_template_file=str(data.get("prompt_template_file", "") or ""),
        correction_scopes=list(data.get("correction_scopes", []) or [])
        or ["all", str(data.get("stage", ""))],
        depends_on=list(data.get("depends_on", []) or []),
        timeout_seconds=int(budget.get("timeout_seconds", 480)),
        run_command=list(run.get("command", []) or []),
        run_cwd=str(run.get("cwd", ".") or "."),
        raw=data,
        path=path,
    )
