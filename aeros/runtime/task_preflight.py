"""Task start preflight packet.

This is the small packet an agent should read before doing project work. It is
deterministic and advisory: it selects guardrails, not scientific conclusions.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from .campaign import (
    assess_campaign,
    infer_campaign_output_classes,
    load_campaign_contract,
    match_campaign_scope,
)
from .contract import Contract
from .current_work import load_current_work_context
from .output_intent import contract_output_intents
from .owner_decisions import evaluate_owner_decision_rules
from .research_risk import compile_research_risk
from .skill_obligation import infer_skill_obligations, obligation_classes
from .source_capture_permission import classify_source_capture_permission
from . import state as state_mod
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


@lru_cache(maxsize=64)
def _load_yaml_cached(path_text: str, mtime_ns: int, size: int) -> dict[str, Any]:
    del mtime_ns, size  # cache-key inputs; file identity remains path_text
    path = Path(path_text)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    stat = path.stat()
    return _load_yaml_cached(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


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


def _nonempty_artifact_exists(root: Path, rel: str) -> bool:
    """Check output presence using directory metadata, never file contents."""
    if not rel or rel == "agent_runs" or rel.startswith("agent_runs/"):
        return True
    try:
        matches = list(root.glob(rel)) if any(ch in rel for ch in "*?[") else [root / rel]
    except (OSError, ValueError):
        return False
    for path in matches:
        try:
            if path.is_file() and path.stat().st_size > 0:
                return True
            if path.is_dir() and any(
                child.is_file() and child.stat().st_size > 0
                for child in path.rglob("*")
            ):
                return True
        except OSError:
            continue
    return False


def _reuse_decision(root: Path, contract: Contract | None) -> dict[str, Any]:
    """Expose prior acceptance before an agent/provider or large-data rerun.

    This is a cheap routing decision. The kernel remains responsible for
    fingerprint freshness and artifact-specific validation.
    """
    base = {
        "status": "NEW_WORK",
        "should_execute": True,
        "recommended_action": "execute the bounded task",
        "identity_source": "runtime state plus output-presence metadata",
        "does_not_prove": [
            "artifact freshness",
            "scientific validity",
            "canonical promotion",
            "claim or gate authority",
        ],
    }
    if not contract:
        return base
    state = state_mod.load_state(root)
    entry = ((state.get("tasks") or {}).get(contract.task_id) or {})
    status = str(entry.get("status") or "")
    semantic_outputs = [
        rel for rel in contract.allowed_outputs
        if rel and rel != "agent_runs" and not rel.startswith("agent_runs/")
    ]
    missing = [rel for rel in semantic_outputs if not _nonempty_artifact_exists(root, rel)]
    if status == "stale":
        return {
            **base,
            "status": "REVALIDATE_FIRST",
            "should_execute": False,
            "missing_outputs": missing,
            "recommended_action": f"python3 -m aeros.cli recover {contract.task_id} --check",
        }
    if status == "passed" and entry.get("output_fingerprint") and not missing:
        return {
            **base,
            "status": "PREVIOUSLY_ACCEPTED",
            "should_execute": False,
            "missing_outputs": [],
            "recommended_action": (
                "reuse accepted artifacts; the kernel will confirm stat guards "
                f"and fingerprints, or run python3 -m aeros.cli recover {contract.task_id} --check"
            ),
        }
    if status == "passed" and missing:
        return {
            **base,
            "status": "RERUN_REQUIRED",
            "missing_outputs": missing,
            "recommended_action": "restore or rerun only the missing declared outputs",
        }
    return base


def _startup_brief(root: Path, *, intent: str, lane: str, reuse_decision: dict[str, Any]) -> dict[str, Any]:
    """Expose the one project-level signal an agent must acknowledge first.

    This is deliberately a derived, read-only projection.  It makes the
    current objective and any deterministic P0 research risk visible before a
    task starts; it neither blocks a user-directed task nor certifies that the
    selected risk is the scientifically best one.
    """
    current_work = load_current_work_context(root)
    risk_report = compile_research_risk(root)
    top_risk = risk_report.get("top_risk") or {}
    priority_order = list(current_work.get("priority_order") or [])
    current_priority = priority_order[0] if priority_order else ""
    risk_severity = str(top_risk.get("severity") or "none")
    attention_required = risk_severity == "p0"
    if top_risk:
        recommended_action = str(top_risk.get("recommended_action") or "Review the top research risk before starting unrelated work.")
        command = str(top_risk.get("command") or "")
        stop_condition = str(top_risk.get("stop_condition") or "Stop after the risk is classified or explicitly deferred by the human.")
        source = str(top_risk.get("source") or "aeros.runtime.research_risk")
    elif not bool(reuse_decision.get("should_execute", True)):
        recommended_action = str(reuse_decision.get("recommended_action") or "Revalidate or reuse accepted artifacts before rerunning.")
        command = str(reuse_decision.get("recommended_action") or "")
        stop_condition = "Stop after reuse or free revalidation is resolved; do not rerun an unchanged task first."
        source = "aeros.runtime.task_preflight.reuse_decision"
    else:
        recommended_action = current_priority or "Proceed with the bounded task intent after reviewing its envelope."
        command = ""
        stop_condition = "Stop at the task preflight boundary before changing lane, canonical state, claims, or human decisions."
        source = str(current_work.get("source_path") or "task_preflight")
    return {
        "status": "ATTENTION_REQUIRED" if attention_required else "READY",
        "intent": intent,
        "current_goal": str(current_work.get("active_goal") or ""),
        "current_deliverable": str(current_work.get("active_deliverable") or ""),
        "current_priority": current_priority,
        "current_lane": str(current_work.get("active_lane") or lane),
        "highest_research_risk": {
            "risk_id": str(top_risk.get("risk_id") or ""),
            "severity": risk_severity,
            "why": str(top_risk.get("why") or ""),
            "outranks": list(top_risk.get("outranks") or []),
        } if top_risk else None,
        "recommended_action": recommended_action,
        "command": command,
        "stop_condition": stop_condition,
        "source": source,
        "must_acknowledge_before_unrelated_work": attention_required,
        "does_not_prove": [
            "that the top risk is the scientifically optimal next action",
            "that a user-directed task is forbidden",
            "that risk resolution approves a gate, claim, paper, or release",
        ],
    }


def build_task_preflight(
    root: Path,
    *,
    task_id: str = "",
    lane: str = "",
    intent: str = "",
    campaign_id: str = "",
) -> dict[str, Any]:
    contract = load_contract_by_id(root, task_id)
    mode = infer_task_mode(root, task_id=task_id, lane=lane, intent=intent, contract=contract)
    workflow = str(mode.get("workflow_preset", "") or "")
    contract_intents = contract_output_intents(contract) if contract else {}
    output_intents: Any = contract_intents or list(mode.get("allowed_output_intents") or [])
    obligations = infer_skill_obligations(root, contract) if contract else _skill_obligations_from_text(root, lane, intent)
    if str(mode.get("task_mode") or "") == "broad_capture":
        explicit_required = bool(contract and contract.raw.get("required_skill_classes"))
        if not explicit_required:
            # Broad capture is intentionally low-governance. Dynamic skills may
            # still be selected by the agent, but lead collection does not
            # manufacture a completion-time use-or-waive obligation.
            obligations = []
    skill_use_contract = _skill_use_contract(root, obligations)
    reuse_decision = _reuse_decision(root, contract)
    allowed = _contract_allowed_to_touch(contract) or _workflow_allowed_prefixes(root, workflow)
    if not allowed:
        allowed = ["agent_runs/", "audits/", "outputs/context/", "work/"]
    bounded_official_probe = (
        (lane or (contract.work_lane if contract else "")) == "data"
        and "bounded official public" in intent.lower()
        and "nonproduction probe" in intent.lower()
    )
    if bounded_official_probe and not contract:
        output_intents = ["probe_only", "audit_note"]
        allowed = ["data/probes/", "outputs/.provenance/", "audits/"]
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
    declared_campaign_id = str(campaign_id or (contract.campaign_id if contract else "") or "").strip()
    effective_lane = lane or (contract.work_lane if contract else "")
    objective_parts = [task_id, intent]
    if contract:
        objective_parts.extend([
            contract.goal,
            " ".join(contract.inputs),
            " ".join(contract.allowed_outputs),
            " ".join(contract.checks),
        ])
    objective_text = " ".join(objective_parts)
    if declared_campaign_id:
        campaign = assess_campaign(root, campaign_id=declared_campaign_id)
        if campaign.get("status") == "CAMPAIGN_MISMATCH":
            active_campaign = load_campaign_contract(root)
            if active_campaign:
                active_id = str(active_campaign.get("campaign_id") or active_campaign.get("id") or "").strip()
                active_assessment = assess_campaign(root, campaign_id=active_id)
                scope = match_campaign_scope(
                    active_campaign, lane=effective_lane, objective_text=objective_text,
                    task_type=str(mode.get("task_mode", "")), output_targets=allowed,
                    inferred_outputs=infer_campaign_output_classes(root),
                )
                active_breakers = list(active_assessment.get("breakers") or [])
                if active_breakers and scope.get("lane_match") and scope.get("scope_match_any"):
                    collision_breaker = {
                        "breaker_id": "campaign_scope_collision",
                        "severity": "block_same_campaign_loop",
                        "reason": "task declares a different campaign_id but matches the stopped active campaign lane/objective markers",
                        "recommended_action": "use the active campaign_id or obtain a human decision that this is a genuinely separate campaign",
                    }
                    campaign = dict(active_assessment)
                    campaign.update({
                        "status": "CAMPAIGN_SCOPE_COLLISION",
                        "campaign_id": declared_campaign_id,
                        "active_campaign_id": active_id,
                        "breakers": [collision_breaker] + active_breakers,
                        "recommended_action": collision_breaker["recommended_action"],
                        "scope_match": scope,
                        "active_campaign_breakers": active_breakers,
                    })
    else:
        active_campaign = load_campaign_contract(root)
        if active_campaign:
            active_id = str(active_campaign.get("campaign_id") or active_campaign.get("id") or "").strip()
            active_assessment = assess_campaign(root, campaign_id=active_id)
            scope = match_campaign_scope(
                active_campaign,
                lane=effective_lane,
                objective_text=objective_text,
                task_type=str(mode.get("task_mode", "")),
                output_targets=allowed,
                inferred_outputs=infer_campaign_output_classes(root),
            )
            active_breakers = list(active_assessment.get("breakers") or [])
            suspected_escape = bool(
                active_breakers
                and scope.get("lane_match")
                and (scope.get("scope_match_any") or scope.get("marker_status") == "missing_fail_closed")
            )
            if suspected_escape:
                escape_breaker = {
                    "breaker_id": "undeclared_campaign_scope",
                    "severity": "block_same_campaign_loop",
                    "reason": (
                        "task omits campaign_id but matches the active campaign on "
                        + ", ".join(
                            dim for dim, on in (
                                ("objective markers", scope.get("objective_match")),
                                ("output targets", scope.get("output_match")),
                                ("task type", scope.get("task_type_match")),
                            ) if on
                        )
                        if scope.get("scope_match_any")
                        else "task omits campaign_id in the active campaign lane and objective markers are missing"
                    ),
                    "recommended_action": "declare the active campaign_id or obtain a human decision that this task is unrelated",
                }
                campaign = dict(active_assessment)
                campaign.update({
                    "status": "UNDECLARED_CAMPAIGN_SCOPE",
                    "campaign_id": "",
                    "active_campaign_id": active_id,
                    "breakers": [escape_breaker] + active_breakers,
                    "recommended_action": escape_breaker["recommended_action"],
                    "scope_match": scope,
                    "active_campaign_breakers": active_breakers,
                })
            else:
                campaign = {
                    "status": "TASK_NOT_IN_CAMPAIGN",
                    "campaign_id": "",
                    "active_campaign_id": active_id,
                    "breakers": [],
                    "active_campaign_breakers": active_breakers,
                    "scope_match": scope,
                    "recommended_action": "continue only if this task is demonstrably unrelated; otherwise declare the active campaign_id",
                }
        else:
            campaign = {
                "status": "NO_ACTIVE_CAMPAIGN",
                "campaign_id": "",
                "active_campaign_id": "",
                "breakers": [],
                "active_campaign_breakers": [],
                "scope_match": {},
                "recommended_action": "continue outside campaign control",
            }
    campaign_breakers = list(campaign.get("breakers") or [])
    startup_brief = _startup_brief(
        root,
        intent=intent,
        lane=effective_lane,
        reuse_decision=reuse_decision,
    )
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
        "reuse_decision": reuse_decision,
        "startup_brief": startup_brief,
        "output_intents": output_intents,
        "source_capture_permission": permission,
        "owner_decision_status": owner_decisions.get("status"),
        "owner_decision_blocks": owner_blocks,
        "owner_decision_constraints": owner_decisions.get("constraints") or [],
        "active_owner_decision_count": owner_decisions.get("active_rule_count", 0),
        "campaign_status": campaign.get("status"),
        "campaign_id": declared_campaign_id,
        "active_campaign_id": campaign.get("active_campaign_id") or campaign.get("campaign_id") or "",
        "campaign_breakers": campaign_breakers,
        "active_campaign_breakers": campaign.get("active_campaign_breakers") or [],
        "campaign_scope_match": campaign.get("scope_match") or {},
        "campaign_recommended_action": campaign.get("recommended_action", ""),
        "needs_human_decision": bool(owner_blocks or campaign_breakers),
        "allowed_to_touch": allowed,
        "must_not_touch": must_not_touch,
        "stop_before_work_if": stop_reasons,
        "does_not_prove": DOES_NOT_PROVE + ["that free-form owner rationale has been semantically understood"],
    }


def format_task_preflight(report: dict[str, Any]) -> str:
    brief = report.get("startup_brief") or {}
    risk = brief.get("highest_research_risk") or {}
    lines = [
        "# AEROS Task Start Preflight",
        "",
        "## Startup Brief",
        f"startup_status: {brief.get('status')}",
        f"current_goal: {brief.get('current_goal')}",
        f"current_deliverable: {brief.get('current_deliverable')}",
        f"current_priority: {brief.get('current_priority')}",
        f"current_lane: {brief.get('current_lane')}",
        f"highest_research_risk: {risk.get('risk_id')}",
        f"highest_risk_severity: {risk.get('severity')}",
        f"highest_risk_why: {risk.get('why')}",
        f"recommended_action: {brief.get('recommended_action')}",
        f"recommended_command: {brief.get('command')}",
        f"startup_stop_condition: {brief.get('stop_condition')}",
        f"must_acknowledge_before_unrelated_work: {brief.get('must_acknowledge_before_unrelated_work')}",
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
        f"campaign_id: {report.get('campaign_id')}",
        f"campaign_status: {report.get('campaign_status')}",
        f"owner_decision_status: {report.get('owner_decision_status')}",
        f"reuse_status: {(report.get('reuse_decision') or {}).get('status')}",
        f"reuse_should_execute: {(report.get('reuse_decision') or {}).get('should_execute')}",
        f"reuse_recommended_action: {(report.get('reuse_decision') or {}).get('recommended_action')}",
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
