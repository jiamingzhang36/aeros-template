"""Skill routing helpers for AEROS task planning and audit receipts.

The router is advisory: it recommends skills and explains their trust tier,
but it never invokes a skill, approves a gate, or weakens task checks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract import Contract
from .skill_receipt import load_core_skill_map

DATA_SKILL_NAMES = {
    "data-inventory",
    "describe-data",
    "data-codebook",
    "data-quality-checker",
    "data-merge-audit",
    "diagnostics-panel",
    "summary-stats-table",
    "quick-stats",
}


def compile_drive_skill_plan(
    *,
    objective_id: str,
    lane: str,
    task_mode: str,
    top_risk_id: str = "",
    job: str = "",
) -> dict[str, Any]:
    """Compile a bounded, advisory skill workflow plan for ``aeros drive``.

    AEROS can select a relevant SOP, but the host agent or human must actually
    invoke it.  A receipt may record resulting findings and artifact impact; it
    cannot prove that a model followed a skill's instructions.  Broad capture is
    deliberately excluded so early discovery remains cheap.
    """
    context = " ".join([objective_id, lane, task_mode, top_risk_id, job]).lower()
    if task_mode == "broad_capture" or objective_id in {"broad_capture", "capture_efficiency_risk"}:
        return {
            "status": "NO_SKILL_NEEDED",
            "selection_rule": "broad capture remains lightweight until candidate triage or promotion",
            "selected": [],
            "does_not_prove": [
                "that no specialist skill could improve an individual lead",
                "that a lead is admissible evidence or ready for promotion",
            ],
        }

    selected: list[dict[str, str]] = []

    def add(name: str, skill_class: str, workflow: str, reason: str, expected_finding: str) -> None:
        if len(selected) >= 3 or any(item["skill_name"] == name for item in selected):
            return
        selected.append({
            "skill_name": name,
            "skill_class": skill_class,
            "workflow": workflow,
            "reason": reason,
            "expected_finding": expected_finding,
            "artifact_impact_required": "yes",
            "requirement": "advisory_unless_existing_contract_requires_class",
        })

    if any(token in context for token in ("citation", "submission", "manuscript", "paper", "claim")):
        add("academic-research-suite", "literature", "academic-paper/citation-check", "claim-bearing citation or submission risk", "sentence-to-source support, contradiction, or unresolved debt")
        add("bib-manager", "literature", "bibliography verification", "citation identity or mapping risk", "verified citation-key, paper, and version mapping")
        add("pre-submission-audit", "submission_review", "paper readiness audit", "submission-facing risk", "bounded list of blocking manuscript issues")
    elif any(token in context for token in ("literature", "fulltext", "full-text", "evidence recovery")):
        add("academic-research-suite", "literature", "deep-research/literature-review", "literature evidence recovery or synthesis work", "source-bounded extraction or unresolved evidence gap")
        add("bib-manager", "literature", "bibliography verification", "paper identity and working-paper/version control", "deduplicated bibliographic mapping")
    elif any(token in context for token in ("probe_data", "data", "source", "inventory")):
        add("data-inventory", "data_source", "data source inventory", "data probe or source feasibility work", "coverage, unit, and source constraints")
        add("data-quality-checker", "data_source", "bounded data quality review", "candidate data needs a quality decision", "schema, missingness, and duplicate-risk findings")
    elif any(token in context for token in ("specification", "diagnose", "causal", "did", "iv", "rd", "method")):
        add("causal-id-review", "causal_identification", "identification review", "design or identification risk", "assumptions, threats, and claim ceiling")
        add("diagnostics-panel", "causal_identification", "diagnostic plan", "specification diagnostics", "diagnostic obligations and failure modes")
    elif any(token in context for token in ("replication", "reproduce", "code")):
        add("replication-check", "replication", "reproduction audit", "reproducibility risk", "reproducible or blocked exhibit chain")
        add("code-review-econ", "replication", "econometric code review", "analysis-code risk", "concrete code or specification findings")

    return {
        "status": "CANDIDATES" if selected else "NO_SKILL_NEEDED",
        "selection_rule": "deterministic objective/risk mapping; at most three candidate skills",
        "selected": selected,
        "does_not_prove": [
            "that the selected skill was invoked by the host agent",
            "that a skill finding is correct without its cited artifact impact",
            "scientific validity, claim approval, or release authority",
        ],
    }


def _norm_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def infer_skill_stage(contract: Contract) -> str:
    """Map a task contract to the closest skill-stage label.

    This is intentionally heuristic and display-oriented. Formal authority
    remains in the task contract, checks, receipts, and human gates.
    """
    blob = " ".join([
        contract.task_id,
        contract.stage,
        contract.gate,
        contract.goal,
        " ".join(contract.checks),
        " ".join(contract.allowed_outputs),
    ]).lower()

    if "design" in blob or "method_card" in blob or "identification" in blob:
        return "design_formation"
    if "data_inventory" in blob or "data_scout" in blob or "data source" in blob:
        return "data_scouting"
    if "claim" in blob or "ceiling" in blob or "language_constraints" in blob:
        return "writing_revision" if "paper" in blob else "execution_analysis"
    if "paper" in blob or "draft" in blob or "referee" in blob or "revision" in blob:
        return "writing_revision"
    if "replication" in blob or "code_review" in blob or "provenance" in blob:
        return "engineering_maintenance"
    if "literature" in blob or "citation" in blob or "paper_registry" in blob:
        return "literature_discovery"
    if contract.stage == "discovery":
        return "discovery_ideation"
    if contract.stage == "execution":
        return "execution_analysis"
    return ""


def recommended_skills(project_root: Path, contract: Contract) -> list[str]:
    explicit = _norm_list(contract.raw.get("recommended_skills"))
    if explicit:
        return explicit

    skill_map = load_core_skill_map(project_root)
    stage = infer_skill_stage(contract)
    names: list[str] = []
    for name, meta in sorted(skill_map.items()):
        if not bool(meta.get("default_use", False)):
            continue
        if str(meta.get("aeros_stage", "")).strip() != stage:
            continue
        names.append(name)
    return names


def allowed_skills(contract: Contract) -> list[str]:
    return _norm_list(contract.raw.get("allowed_skills"))


def skill_route(project_root: Path, contract: Contract) -> dict[str, Any]:
    skill_map = load_core_skill_map(project_root)
    rec = recommended_skills(project_root, contract)
    allowed = allowed_skills(contract)
    records: list[dict[str, Any]] = []
    for name in rec:
        meta = skill_map.get(name, {})
        records.append({
            "skill_name": name,
            "known_to_aeros": bool(meta),
            "allowed_by_contract": name in allowed,
            "tier": meta.get("tier", ""),
            "source": meta.get("source", ""),
            "aeros_stage": meta.get("aeros_stage", ""),
            "use_status": meta.get("use_status", ""),
            "human_gate_required": bool(meta.get("human_gate_required", False)),
        })
    routed_stages = sorted({
        str(item.get("aeros_stage", "")).strip()
        for item in records
        if str(item.get("aeros_stage", "")).strip()
    })
    return {
        "task_id": contract.task_id,
        "inferred_skill_stage": "+".join(routed_stages) if routed_stages else infer_skill_stage(contract),
        "recommended_skills": rec,
        "allowed_skills": allowed,
        "routes": records,
    }


def format_skill_hint(project_root: Path, contract: Contract) -> str:
    records = skill_route(project_root, contract)["routes"]
    if not records:
        return "skills=none"
    parts: list[str] = []
    for item in records:
        name = item["skill_name"]
        tier = item.get("tier") or "unknown"
        status = "allowed" if item.get("allowed_by_contract") else "not-allowed"
        gate = ",human-gate" if item.get("human_gate_required") else ""
        parts.append(f"{name}[{tier},{status}{gate}]")
    return "skills=" + ",".join(parts)


def validate_skill_contracts(project_root: Path, contracts: dict[str, tuple[Contract, Path]]) -> list[str]:
    """Validate task-level skill declarations, independent of run receipts."""
    failures: list[str] = []
    skill_map = load_core_skill_map(project_root)
    from .skill_obligation import validate_skill_coverage

    failures.extend(validate_skill_coverage(project_root, contracts))
    for task_id, (contract, _path) in sorted(contracts.items()):
        allowed = set(allowed_skills(contract))
        rec = set(recommended_skills(project_root, contract))
        for name in sorted(allowed | rec):
            if name not in skill_map:
                failures.append(f"{task_id}: skill {name!r} is not in harness/skill_map_core.yml")
        for name in sorted(rec - allowed):
            failures.append(f"{task_id}: recommended skill {name!r} is not allowed by task contract")
        required_classes = set(_norm_list(contract.raw.get("required_skill_classes")))
        if infer_skill_stage(contract) == "data_scouting" and "data_source" in required_classes:
            if not (allowed & DATA_SKILL_NAMES):
                failures.append(f"{task_id}: data-lane task has no allowed data skill")
            if not (rec & DATA_SKILL_NAMES):
                failures.append(f"{task_id}: data-lane task has no recommended data skill")
    return failures
