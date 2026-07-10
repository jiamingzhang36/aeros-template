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

from .campaign import assess_campaign
from .contract import Contract
from .output_intent import contract_output_intents
from .owner_decisions import evaluate_owner_decision_rules
from .skill_obligation import infer_skill_obligations, obligation_classes
from .source_capture_permission import classify_source_capture_permission
from .task_mode import infer_task_mode, load_contract_by_id


DEFAULT_MUST_NOT_TOUCH = [
    "data/raw/",
    "data/intermediate/",
    "data/processed/",
    "docs/protected_definitions.yml",
    "evidence/claim_registry.md",
    "paper/",
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


def _suggested_route(intent: str) -> str:
    text = intent.lower()
    if any(token in text for token in ("negative seed", "fraud", "violation", "litigation", "complaint")):
        return "negative_seed_first"
    if any(token in text for token in ("base universe", "registry", "official registry")):
        return "base_universe_first"
    return ""


def _route_status(root: Path, intent: str) -> dict[str, str]:
    data = _load_yaml(root / "discovery" / "route_decision.yml")
    suggested = _suggested_route(intent)
    hypotheses = data.get("route_hypotheses") or {}
    suggested_hypothesis = hypotheses.get(suggested) if isinstance(hypotheses, dict) and suggested else {}
    hypothesis_text = str((suggested_hypothesis or {}).get("hypothesis") or "").strip()
    for key in ("selected_route", "recommended_route", "current_route", "route"):
        value = str(data.get(key, "")).strip()
        if value and value.lower() not in {"pending", "tbd", "none"}:
            selected_hypothesis = hypotheses.get(value) if isinstance(hypotheses, dict) else {}
            return {
                "route": value,
                "route_suggestion": suggested,
                "route_hypothesis": str((selected_hypothesis or {}).get("hypothesis") or hypothesis_text).strip(),
                "decision_status": str(data.get("decision_status", "") or "").strip(),
                "route_source": "route_decision",
            }
    return {
        "route": "pending",
        "route_suggestion": suggested,
        "route_hypothesis": hypothesis_text,
        "decision_status": str(data.get("decision_status", "") or "pending").strip(),
        "route_source": "route_decision_pending" if data else "inferred_suggestion_only",
    }


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


def _skill_use_contract(root: Path, obligations: list[str]) -> dict[str, Any]:
    classes = obligation_classes(root)
    skills_by_class: dict[str, list[str]] = {}
    for cls in obligations:
        skills_by_class[cls] = sorted(str(item) for item in (classes.get(cls, {}).get("skills") or []) if str(item).strip())
    return {
        "use_or_waive_required": bool(obligations),
        "required_skill_classes": sorted(obligations),
        "candidate_skills_by_class": skills_by_class,
        "waiver_required_fields": ["skill_class", "reason", "scope", "progress_label"],
        "completion_receipt_field": "skill_use_attestation",
        "pass_rule": "each required skill class must have a skill invocation receipt or explicit waiver before completion can pass",
        "does_not_prove": [
            "that skill advice is correct",
            "that the agent followed every skill instruction perfectly",
            "that claims, gates, or paper text are approved",
        ],
    }


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
    skill_use_contract = _skill_use_contract(root, obligations)
    allowed = _contract_allowed_to_touch(contract) or _workflow_allowed_prefixes(root, workflow)
    if not allowed:
        allowed = ["agent_runs/", "audits/", "outputs/context/", "work/"]
    must_not_touch = list(DEFAULT_MUST_NOT_TOUCH)
    route = _route_status(root, intent)
    permission = classify_source_capture_permission(
        root,
        lane=lane or (contract.work_lane if contract else ""),
        task_mode=str(mode.get("task_mode", "")),
        intent=intent,
        output_intents=output_intents,
        allowed_to_touch=allowed,
    )
    owner_decisions = evaluate_owner_decision_rules(
        root,
        lane=lane or (contract.work_lane if contract else ""),
        intent=intent,
        task_id=task_id,
    )
    owner_blocks = list(owner_decisions.get("blocks") or [])
    # Marginal-yield / budget / collecting-without-testing circuit breaker.
    # Backward-compatible: with no active campaign contract assess_campaign
    # returns zero breakers, so preflight behaviour is unchanged. When a
    # campaign IS active and a breaker trips, the execution gate blocks — this
    # is the wire from "campaign assess can detect stop" to "preflight enforces
    # stop", so the agent cannot proceed to the next local task on autopilot.
    campaign = assess_campaign(root)
    campaign_breakers = list(campaign.get("breakers") or [])
    stop_reasons = [
        "route is pending and task is route-sensitive",
        "skill obligations cannot be used or waived",
        "intended outputs do not fit allowed output intents",
        "planned writes touch must_not_touch paths",
    ]
    if owner_blocks:
        stop_reasons.insert(0, "owner decision do_not rule matched this task intent")
    if campaign_breakers:
        ids = ", ".join(str(b.get("breaker_id") or "breaker") for b in campaign_breakers)
        stop_reasons.insert(0, f"campaign circuit breaker tripped ({ids}); request a human continue/stop decision")
    return {
        "status": "BLOCKED" if (owner_blocks or campaign_breakers) else "ADVISORY",
        "task_id": task_id,
        "lane": lane or (contract.work_lane if contract else ""),
        "intent": intent,
        "task_mode": mode.get("task_mode"),
        "task_mode_reason": mode.get("reason", ""),
        "route": route.get("route", "pending"),
        "route_suggestion": route.get("route_suggestion", ""),
        "route_hypothesis": route.get("route_hypothesis", ""),
        "decision_status": route.get("decision_status", ""),
        "route_source": route.get("route_source", ""),
        "workflow_preset": workflow,
        "execution_mode": mode.get("execution_mode"),
        "skill_obligations": obligations,
        "skill_use_contract": skill_use_contract,
        "output_intents": output_intents,
        "source_capture_permission": permission,
        "owner_decision_status": owner_decisions.get("status"),
        "owner_decision_blocks": owner_blocks,
        "owner_decision_constraints": owner_decisions.get("constraints") or [],
        "active_owner_decision_count": owner_decisions.get("active_rule_count", 0),
        "campaign_status": campaign.get("status"),
        "campaign_breakers": campaign_breakers,
        "campaign_recommended_action": campaign.get("recommended_action", ""),
        "needs_human_decision": bool(owner_blocks or campaign_breakers),
        "allowed_to_touch": allowed,
        "must_not_touch": must_not_touch,
        "stop_before_work_if": stop_reasons,
        "does_not_prove": DOES_NOT_PROVE + ["that free-form owner rationale has been semantically understood"],
    }


def format_task_preflight(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Task Start Preflight",
        "",
        f"status: {report.get('status')}",
        f"task_mode: {report.get('task_mode')}",
        f"task_mode_reason: {report.get('task_mode_reason')}",
        f"route: {report.get('route')}",
        f"route_suggestion: {report.get('route_suggestion')}",
        f"route_hypothesis: {report.get('route_hypothesis')}",
        f"decision_status: {report.get('decision_status')}",
        f"workflow_preset: {report.get('workflow_preset')}",
        f"execution_mode: {report.get('execution_mode')}",
        f"source_capture_permission: {(report.get('source_capture_permission') or {}).get('approval_required')}",
        f"owner_decision_status: {report.get('owner_decision_status')}",
        "",
        "owner_decision_blocks:",
    ]
    lines.extend(f"- {item.get('decision_id')}: {item.get('pattern')}" for item in report.get("owner_decision_blocks") or [])
    lines.extend([
        "",
        "skill_obligations:",
    ])
    lines.extend(f"- {item}" for item in report.get("skill_obligations") or [])
    skill_use = report.get("skill_use_contract") or {}
    lines.append("skill_use_contract:")
    lines.append(f"- use_or_waive_required: {skill_use.get('use_or_waive_required')}")
    lines.append(f"- pass_rule: {skill_use.get('pass_rule')}")
    candidate_skills = skill_use.get("candidate_skills_by_class") or {}
    if isinstance(candidate_skills, dict):
        for cls, skills in candidate_skills.items():
            lines.append(f"- {cls}: {skills}")
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
