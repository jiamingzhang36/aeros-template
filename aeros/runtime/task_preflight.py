"""Task start preflight packet.

This is the small packet an agent should read before doing project work. It is
deterministic and advisory: it selects guardrails, not scientific conclusions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from .contract import Contract
from .output_intent import contract_output_intents
from .skill_obligation import infer_skill_obligations, obligation_classes
from .source_capture_permission import classify_source_capture_permission
from .task_mode import infer_task_mode, load_contract_by_id


DEFAULT_MUST_NOT_TOUCH = [
    "data/raw/",
    "docs/protected_definitions.yml",
    "evidence/claim_registry.md",
    "decisions/decision_log.csv",
]

DOES_NOT_PROVE = [
    "that the task has run",
    "that the route is scientifically optimal",
    "that outputs are admissible evidence",
    "that a gate is approved",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _route_status(root: Path, intent: str) -> str:
    text = intent.lower()
    if any(token in text for token in ("negative seed", "fraud", "violation", "litigation", "complaint")):
        return "negative_seed_first"
    if any(token in text for token in ("base universe", "registry", "official registry")):
        return "base_universe_first"
    data = _load_yaml(root / "discovery" / "route_decision.yml")
    for key in ("selected_route", "recommended_route", "current_route", "route"):
        value = str(data.get(key, "")).strip()
        if value:
            return value
    return "pending"


def _workflow_allowed_prefixes(root: Path, workflow: str) -> list[str]:
    data = _load_yaml(root / "harness" / "session_scope.yml")
    presets = data.get("workflow_presets") or {}
    preset = presets.get(workflow) if isinstance(presets, dict) else {}
    if not isinstance(preset, dict):
        return []
    out: list[str] = []
    for key in ("allowed_prefixes", "allowed_paths", "allowed_outputs"):
        value = preset.get(key)
        if isinstance(value, list):
            out.extend(str(item) for item in value if str(item).strip())
    return sorted(dict.fromkeys(out))


def _skill_obligations_from_text(root: Path, lane: str, intent: str) -> list[str]:
    blob = f"{lane} {intent}".lower()
    out: list[str] = []
    for cls, spec in obligation_classes(root).items():
        if any(str(token).lower() in blob for token in spec.get("triggers", [])):
            out.append(cls)
    return out


def _contract_allowed_to_touch(contract: Contract | None) -> list[str]:
    if not contract:
        return []
    return sorted(dict.fromkeys(contract.allowed_outputs))


def build_task_preflight(root: Path, *, task_id: str = "", lane: str = "", intent: str = "") -> dict[str, Any]:
    contract = load_contract_by_id(root, task_id)
    mode = infer_task_mode(root, task_id=task_id, lane=lane, intent=intent)
    workflow = str(mode.get("workflow_preset", "") or "")
    contract_intents = contract_output_intents(contract) if contract else {}
    output_intents: Any = contract_intents or list(mode.get("allowed_output_intents") or [])
    obligations = infer_skill_obligations(root, contract) if contract else _skill_obligations_from_text(root, lane, intent)
    allowed = _contract_allowed_to_touch(contract) or _workflow_allowed_prefixes(root, workflow)
    if not allowed:
        allowed = ["agent_runs/", "audits/", "outputs/context/", "work/"]
    must_not_touch = list(DEFAULT_MUST_NOT_TOUCH)
    if mode.get("task_mode") == "claim_audit":
        must_not_touch = [p for p in must_not_touch if p != "evidence/claim_registry.md"]
    permission = classify_source_capture_permission(
        root,
        lane=lane or (contract.work_lane if contract else ""),
        task_mode=str(mode.get("task_mode", "")),
        intent=intent,
        output_intents=output_intents,
        allowed_to_touch=allowed,
    )
    return {
        "status": "ADVISORY",
        "task_id": task_id,
        "lane": lane or (contract.work_lane if contract else ""),
        "intent": intent,
        "task_mode": mode.get("task_mode"),
        "route": _route_status(root, intent),
        "workflow_preset": workflow,
        "execution_mode": mode.get("execution_mode"),
        "skill_obligations": obligations,
        "output_intents": output_intents,
        "source_capture_permission": permission,
        "allowed_to_touch": allowed,
        "must_not_touch": must_not_touch,
        "stop_before_work_if": [
            "route is pending and task is route-sensitive",
            "skill obligations cannot be used or waived",
            "intended outputs do not fit allowed output intents",
            "planned writes touch must_not_touch paths",
        ],
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_task_preflight(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Task Start Preflight",
        "",
        f"status: {report.get('status')}",
        f"task_mode: {report.get('task_mode')}",
        f"route: {report.get('route')}",
        f"workflow_preset: {report.get('workflow_preset')}",
        f"execution_mode: {report.get('execution_mode')}",
        f"source_capture_permission: {(report.get('source_capture_permission') or {}).get('approval_required')}",
        "",
        "skill_obligations:",
    ]
    lines.extend(f"- {item}" for item in report.get("skill_obligations") or [])
    lines.append("output_intents:")
    output_intents = report.get("output_intents")
    if isinstance(output_intents, dict):
        lines.extend(f"- {path}: {intent}" for path, intent in output_intents.items())
    else:
        lines.extend(f"- {item}" for item in output_intents or [])
    lines.append("allowed_to_touch:")
    lines.extend(f"- {item}" for item in report.get("allowed_to_touch") or [])
    lines.append("must_not_touch:")
    lines.extend(f"- {item}" for item in report.get("must_not_touch") or [])
    lines.append("stop_before_work_if:")
    lines.extend(f"- {item}" for item in report.get("stop_before_work_if") or [])
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
