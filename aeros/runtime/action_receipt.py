"""Action receipts classify what a run actually advanced.

AEROS uses these receipts to prevent harness hygiene or documentation repair
from being reported as substantive data/research progress.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ACTION_DIR = Path("agent_runs/action_receipts")

ACTION_MODES = {
    "data_progress",
    "data_backfill",
    "data_probe",
    "data_validation",
    "harness_triage",
    "literature_progress",
    "claim_audit",
    "writing",
    "cleanup",
}
PROGRESS_LABELS = {
    "substantive_research_progress",
    "mechanical_hygiene",
    "blocked_queue_preparation",
    "documentation_repair",
}
DEPENDENCY_TYPES = {"enabling", "validating", "cosmetic", "blocking_resolution"}
DATA_KEYS = [
    "inventory_changed",
    "source_verified",
    "data_rows_changed",
    "coverage_changed",
    "backfill_queue_changed",
    "probe_completed",
]
RESEARCH_KEYS = [
    "claim_ceiling_changed",
    "gate_candidate_changed",
    "evidence_graph_changed",
    "result_registered",
]


@dataclass(frozen=True)
class ActionReceiptArgs:
    action_id: str
    action_mode: str
    progress_label: str
    summary: str = ""
    why_this_now: str = ""
    evidence_paths: list[str] = field(default_factory=list)
    data_impact: dict[str, bool] = field(default_factory=dict)
    research_impact: dict[str, bool] = field(default_factory=dict)
    would_progress_without_this_action: bool = False
    dependency_type: str = ""
    dry_run: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    out = "_".join(part for part in out.split("_") if part)
    return out or "action"


def receipt_path(project_root: Path, action_id: str) -> Path:
    return project_root / ACTION_DIR / f"{_slug(action_id)}.yml"


def build_payload(args: ActionReceiptArgs) -> dict[str, Any]:
    data = {key: bool(args.data_impact.get(key, False)) for key in DATA_KEYS}
    research = {key: bool(args.research_impact.get(key, False)) for key in RESEARCH_KEYS}
    return {
        "version": 1,
        "policy": "AEROS-ACTION-RECEIPT-001",
        "action_id": args.action_id,
        "generated_at": _now(),
        "action_mode": args.action_mode,
        "honest_progress_label": args.progress_label,
        "why_this_now": args.why_this_now,
        "summary": args.summary,
        "data_impact": data,
        "research_impact": research,
        "evidence_paths": list(args.evidence_paths),
        "causal_attribution": {
            "would_progress_without_this_action": bool(args.would_progress_without_this_action),
            "dependency_type": args.dependency_type,
        },
    }


def validate_payload(payload: dict[str, Any], project_root: Path | None = None) -> list[str]:
    failures: list[str] = []
    action_id = str(payload.get("action_id", "(missing)"))
    mode = str(payload.get("action_mode", "")).strip()
    label = str(payload.get("honest_progress_label", "")).strip()
    data = payload.get("data_impact") or {}
    research = payload.get("research_impact") or {}
    evidence = payload.get("evidence_paths") or []
    causal = payload.get("causal_attribution") or {}
    if mode not in ACTION_MODES:
        failures.append(f"{action_id}: invalid action_mode {mode!r}")
    if label not in PROGRESS_LABELS:
        failures.append(f"{action_id}: invalid honest_progress_label {label!r}")
    if not str(payload.get("why_this_now", "")).strip():
        failures.append(f"{action_id}: missing why_this_now")
    if not str(payload.get("summary", "")).strip():
        failures.append(f"{action_id}: missing summary")
    if not isinstance(data, dict):
        failures.append(f"{action_id}: data_impact must be a mapping")
        data = {}
    if not isinstance(research, dict):
        failures.append(f"{action_id}: research_impact must be a mapping")
        research = {}
    for key in DATA_KEYS:
        if key not in data:
            failures.append(f"{action_id}: data_impact missing {key}")
    for key in RESEARCH_KEYS:
        if key not in research:
            failures.append(f"{action_id}: research_impact missing {key}")
    data_true = any(bool(data.get(key)) for key in DATA_KEYS)
    research_true = any(bool(research.get(key)) for key in RESEARCH_KEYS)
    if mode.startswith("data_") and not data_true:
        failures.append(f"{action_id}: data action_mode requires at least one true data_impact field")
    if label == "substantive_research_progress" and not (data_true or research_true):
        failures.append(f"{action_id}: substantive progress requires data or research impact")
    if label in {"mechanical_hygiene", "documentation_repair"} and (data_true or research_true):
        failures.append(f"{action_id}: hygiene/documentation label should not claim data/research impact")
    if not isinstance(causal, dict):
        failures.append(f"{action_id}: causal_attribution must be a mapping")
        causal = {}
    dep = str(causal.get("dependency_type", "")).strip()
    if dep not in DEPENDENCY_TYPES:
        failures.append(f"{action_id}: invalid causal_attribution.dependency_type {dep!r}")
    if label == "substantive_research_progress" and dep == "cosmetic":
        failures.append(f"{action_id}: substantive progress cannot have cosmetic dependency_type")
    if label in {"mechanical_hygiene", "documentation_repair"} and dep in {"enabling", "validating"}:
        failures.append(f"{action_id}: hygiene/documentation label should not claim enabling/validating causal role")
    if not isinstance(evidence, list):
        failures.append(f"{action_id}: evidence_paths must be a list")
        evidence = []
    if project_root is not None:
        for raw in evidence:
            rel = str(raw).strip()
            if rel and not (project_root / rel).exists():
                failures.append(f"{action_id}: evidence path does not exist: {rel}")
    return failures


def write_action_receipt(project_root: Path, args: ActionReceiptArgs) -> tuple[Path, dict[str, Any], list[str]]:
    payload = build_payload(args)
    failures = validate_payload(payload, project_root)
    path = receipt_path(project_root, args.action_id)
    if not args.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path, payload, failures


def validate_action_receipts(project_root: Path) -> list[str]:
    root = project_root / ACTION_DIR
    if not root.exists():
        return []
    failures: list[str] = []
    for path in sorted(root.glob("*.yml")):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            failures.append(f"{path}: unreadable action receipt ({exc})")
            continue
        if not isinstance(payload, dict):
            failures.append(f"{path}: action receipt must be a mapping")
            continue
        failures.extend(validate_payload(payload, project_root))
    return failures
