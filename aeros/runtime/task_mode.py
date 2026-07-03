"""Task mode classifier for workflow preset selection.

Task modes describe the kind of work about to happen.  They are advisory
guardrail selectors, not execution authority and not evidence admission.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from .contract import Contract, load_contract


POLICY_PATH = Path("harness/task_mode_policy.yml")

DEFAULT_MODES: dict[str, dict[str, Any]] = {
    "general_guardrail": {
        "workflow_preset": "",
        "execution_mode": "bounded_probe",
        "allowed_output_intents": ["audit_note", "probe_only"],
    },
    "source_capture": {
        "workflow_preset": "recapture_source_pool",
        "execution_mode": "source_capture",
        "allowed_output_intents": ["probe_only", "staging_artifact", "audit_note"],
    },
    "data_repair": {
        "workflow_preset": "source_promotion_queue",
        "execution_mode": "bounded_probe",
        "allowed_output_intents": ["probe_only", "canonical_candidate", "audit_note"],
    },
    "claim_audit": {
        "workflow_preset": "claim_audit",
        "execution_mode": "bounded_probe",
        "allowed_output_intents": ["audit_note", "canonical_candidate"],
    },
    "writing_sync": {
        "workflow_preset": "writing_guardrail",
        "execution_mode": "paper_release",
        "allowed_output_intents": ["audit_note", "canonical_candidate", "canonical_update"],
    },
    "submission_readiness": {
        "workflow_preset": "submission_release_preflight",
        "execution_mode": "paper_release",
        "allowed_output_intents": ["audit_note", "canonical_candidate"],
    },
    "route_recovery": {
        "workflow_preset": "source_promotion_queue",
        "execution_mode": "waiting_on_external_input",
        "allowed_output_intents": ["audit_note", "probe_only"],
    },
}


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / POLICY_PATH
    if not path.exists() or yaml is None:
        return {"modes": DEFAULT_MODES}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"modes": DEFAULT_MODES}


def _contract_blob(contract: Contract | None) -> str:
    if not contract:
        return ""
    return " ".join(
        [
            contract.task_id,
            contract.stage,
            contract.gate,
            contract.work_lane,
            contract.goal,
            " ".join(contract.inputs),
            " ".join(contract.allowed_outputs),
            " ".join(contract.checks),
        ]
    )


def load_contract_by_id(root: Path, task_id: str) -> Contract | None:
    if not task_id:
        return None
    for path in sorted((root / "tasks").rglob("*.yml")):
        try:
            contract = load_contract(path)
        except Exception:
            continue
        if contract.task_id == task_id:
            return contract
    return None


def infer_task_mode(root: Path, *, task_id: str = "", lane: str = "", intent: str = "") -> dict[str, Any]:
    contract = load_contract_by_id(root, task_id)
    blob = f"{lane} {intent} {_contract_blob(contract)}".lower()
    if lane == "data":
        mode = "data_repair"
    elif lane == "claim":
        mode = "claim_audit"
    elif lane == "writing":
        mode = "writing_sync"
    else:
        mode = "general_guardrail"
    reason = "defaulted to conservative guardrail from lane/task context"

    if any(token in blob for token in ("wrong route", "route recovery", "negative seed", "base universe", "route_decision")):
        mode, reason = "route_recovery", "route decision or failed route context detected"
    elif any(token in blob for token in ("submit", "submission", "release", "replication package", "preflight")):
        mode, reason = "submission_readiness", "submission/release-facing context detected"
    elif any(token in blob for token in ("paper", "draft", "word", "tex", "writing", "response")):
        mode, reason = "writing_sync", "writing or document synchronization context detected"
    elif any(token in blob for token in ("claim", "ceiling", "registry", "language constraint")):
        mode, reason = "claim_audit", "claim audit or claim-boundary context detected"
    elif any(token in blob for token in ("recapture", "capture", "source snapshot", "chrome", "fulltext", "source_capture")):
        mode, reason = "source_capture", "source capture or recapture context detected"
    elif any(token in blob for token in ("repair", "backfill", "probe", "denominator", "data_inventory", "data_contract")):
        mode, reason = "data_repair", "data repair/probe context detected"

    policy = _load_policy(root)
    modes = policy.get("modes") or DEFAULT_MODES
    spec = dict(modes.get(mode) or DEFAULT_MODES.get(mode) or {})
    return {
        "status": "ADVISORY",
        "task_id": task_id,
        "lane": lane or (contract.work_lane if contract else ""),
        "task_mode": mode,
        "reason": reason,
        "workflow_preset": spec.get("workflow_preset", ""),
        "execution_mode": spec.get("execution_mode", "smoke_test"),
        "allowed_output_intents": list(spec.get("allowed_output_intents") or []),
        "does_not_prove": [
            "that this is the scientifically best workflow",
            "that the task has run",
            "that outputs are admissible evidence",
            "that a gate is approved",
        ],
    }


def format_task_mode(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Task Mode",
        "",
        f"task_mode: {report.get('task_mode')}",
        f"workflow_preset: {report.get('workflow_preset')}",
        f"execution_mode: {report.get('execution_mode')}",
        f"reason: {report.get('reason')}",
        "allowed_output_intents:",
    ]
    lines.extend(f"- {item}" for item in report.get("allowed_output_intents") or [])
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
