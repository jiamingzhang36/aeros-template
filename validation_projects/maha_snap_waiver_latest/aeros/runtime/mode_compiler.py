"""Read-only compiled view over AEROS mode/preset surfaces.

This module does not change runtime behavior. It projects the existing
execution-mode and task-mode presets into five orthogonal fields so operators
can reason about AEROS without juggling every policy surface independently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from .execution_mode import DEFAULT_MODES as DEFAULT_EXECUTION_MODES
from .task_mode import DEFAULT_MODES as DEFAULT_TASK_MODES


ARTIFACT_LEVELS = {
    "lead",
    "candidate",
    "staging",
    "canonical_candidate",
    "canonical",
    "result",
    "claim",
    "paper",
    "release",
}

EFFECT_CLASSES = {
    "read_only",
    "local_write",
    "network_read",
    "credentialed_read",
    "external_write",
}

AUTHORITY_SURFACES = {
    "none",
    "route",
    "resource",
    "claim",
    "paper",
    "release",
}

EXECUTION_BUDGETS = {
    "smoke",
    "bounded",
    "expensive",
    "waiting",
}

VERIFICATION_STRENGTHS = {
    "self_reported",
    "harness_observed",
    "machine_validated",
    "human_accepted",
    "externally_reproduced",
}

DOES_NOT_PROVE = [
    "that the preset is scientifically optimal",
    "that a task has run",
    "that a lead or candidate is evidence",
    "that a claim, paper, or release is approved",
]


def _load_policy_modes(root: Path, rel: str, fallback: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    path = root / rel
    if not path.exists() or yaml is None:
        return fallback
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    modes = data.get("modes") if isinstance(data, dict) else None
    if not isinstance(modes, dict):
        return fallback
    out: dict[str, dict[str, Any]] = {}
    for name, spec in modes.items():
        if isinstance(spec, dict):
            out[str(name)] = dict(spec)
    return out or fallback


def _load_yaml_policy(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _artifact_level(task_mode: str, task_spec: dict[str, Any], execution_mode: str) -> str:
    intents = set(task_spec.get("allowed_output_intents") or [])
    if task_mode == "broad_capture" or "lead_queue" in intents:
        return "lead"
    if "candidate_queue" in intents:
        return "candidate"
    if task_mode == "claim_audit":
        return "claim"
    if task_mode == "writing_sync":
        return "paper"
    if task_mode == "submission_readiness" or execution_mode == "paper_release":
        return "release"
    if "canonical_update" in intents:
        return "canonical"
    if "canonical_candidate" in intents:
        return "canonical_candidate"
    if "staging_artifact" in intents or task_mode == "source_capture":
        return "staging"
    return "candidate"


def _effect_class(task_mode: str, execution_mode: str) -> str:
    if execution_mode == "smoke_test":
        return "read_only"
    if execution_mode == "expensive_api_run":
        return "credentialed_read"
    if task_mode in {"broad_capture", "source_capture"} or execution_mode == "source_capture":
        return "network_read"
    if execution_mode == "waiting_on_external_input":
        return "read_only"
    return "local_write"


def _authority_surface(task_mode: str, execution_mode: str) -> str:
    if execution_mode == "expensive_api_run":
        return "resource"
    if execution_mode == "paper_release" or task_mode == "submission_readiness":
        return "release"
    if task_mode == "writing_sync":
        return "paper"
    if task_mode == "claim_audit":
        return "claim"
    if task_mode in {"source_capture", "data_repair", "route_recovery"}:
        return "route"
    return "none"


def _execution_budget(execution_mode: str) -> str:
    if execution_mode == "smoke_test":
        return "smoke"
    if execution_mode == "expensive_api_run":
        return "expensive"
    if execution_mode == "waiting_on_external_input":
        return "waiting"
    return "bounded"


def _verification_strength(artifact_level: str, execution_mode: str, authority_surface: str) -> str:
    if authority_surface in {"claim", "paper", "release"} or execution_mode == "paper_release":
        return "human_accepted"
    if artifact_level in {"canonical", "result"}:
        return "machine_validated"
    if execution_mode == "waiting_on_external_input":
        return "self_reported"
    return "harness_observed"


def _allowed_outputs(task_mode: str, task_spec: dict[str, Any]) -> list[str]:
    workflow = str(task_spec.get("workflow_preset") or "")
    if task_mode == "broad_capture" or workflow == "broad_capture_leads":
        return [
            "work/leads/**",
            "data/backfill/*_lead_queue.csv",
            "data/backfill/*_candidate_queue.csv",
            "audits/broad_capture/**",
            "quality_reports/broad_capture/**",
            "outputs/logs/**",
            "evidence/delta_log.jsonl",
        ]
    if task_mode == "source_capture":
        return ["work/recapture_**", "source_snapshots/**", "audits/source_recapture/**", "quality_reports/source_recapture/**"]
    if task_mode == "writing_sync":
        return ["paper/**", "output/tex/**", "outputs/tex/**", "quality_reports/writing/**", "audits/writing/**"]
    return []


def _forbidden_outputs(task_mode: str, artifact_level: str) -> list[str]:
    common = ["decisions/approvals/**"]
    if artifact_level in {"lead", "candidate", "staging"}:
        return [
            "data/raw/**",
            "data/intermediate/**",
            "data/processed/**",
            "paper/**",
            "evidence/claim_registry.md",
            "replication/**",
            "compliance/**",
            *common,
        ]
    if task_mode == "writing_sync":
        return ["data/raw/**", "evidence/claim_registry.md", *common]
    return common


def compiled_mode_map(root: Path) -> dict[str, Any]:
    task_modes = _load_policy_modes(root, "harness/task_mode_policy.yml", DEFAULT_TASK_MODES)
    execution_modes = _load_policy_modes(root, "harness/execution_mode_policy.yml", DEFAULT_EXECUTION_MODES)
    output_policy = _load_yaml_policy(root, "harness/output_intent_policy.yml")
    source_policy = _load_yaml_policy(root, "harness/source_capture_permission_policy.yml")
    profile_policy = _load_yaml_policy(root, "harness/check_profiles.yml")
    valid_output_intents = set(str(item) for item in (output_policy.get("valid_output_intents") or []))
    check_profiles = set((profile_policy.get("profiles") or {}).keys())
    cross_checks_run = [
        "task_mode_policy.execution_mode -> execution_mode_policy.modes",
        "task_mode_policy.allowed_output_intents -> output_intent_policy.valid_output_intents",
        "execution_mode_policy.check_profile -> check_profiles.profiles",
        "broad_capture/source_capture -> source_capture_permission_policy.tiers",
        "compiled authority/output boundary consistency",
    ]
    contradictions: list[str] = []
    rows: list[dict[str, Any]] = []
    for task_mode, task_spec in sorted(task_modes.items()):
        execution_mode = str(task_spec.get("execution_mode") or "smoke_test")
        execution_spec = dict(execution_modes.get(execution_mode) or {})
        artifact_level = _artifact_level(task_mode, task_spec, execution_mode)
        effect_class = _effect_class(task_mode, execution_mode)
        authority_surface = _authority_surface(task_mode, execution_mode)
        execution_budget = _execution_budget(execution_mode)
        verification_strength = _verification_strength(artifact_level, execution_mode, authority_surface)
        output_intents = list(task_spec.get("allowed_output_intents") or [])
        check_profile = execution_spec.get("check_profile") or execution_spec.get("profile") or ""
        row_contradictions: list[str] = []
        if execution_mode not in execution_modes:
            row_contradictions.append(f"execution_mode {execution_mode!r} missing from execution_mode_policy")
        unknown_intents = sorted(set(str(item) for item in output_intents) - valid_output_intents) if valid_output_intents else []
        if unknown_intents:
            row_contradictions.append("unknown output intents: " + ", ".join(unknown_intents))
        if check_profile and check_profiles and check_profile not in check_profiles:
            row_contradictions.append(f"check_profile {check_profile!r} missing from check_profiles")
        tiers = source_policy.get("tiers") or {}
        if task_mode == "broad_capture" and "green_broad_capture" not in tiers:
            row_contradictions.append("broad_capture lacks green_broad_capture permission tier")
        if task_mode == "source_capture" and "green_public_staging" not in tiers:
            row_contradictions.append("source_capture lacks green_public_staging permission tier")
        if artifact_level in {"lead", "candidate", "staging"} and authority_surface in {"claim", "paper", "release"}:
            row_contradictions.append(f"early artifact_level {artifact_level!r} cannot expose {authority_surface!r} authority")
        if "canonical_update" in output_intents and not execution_spec.get("requires_human_decision", False):
            row_contradictions.append("canonical_update intent requires human-decision execution mode")
        contradictions.extend(f"{task_mode}: {item}" for item in row_contradictions)
        rows.append(
            {
                "preset": task_mode,
                "task_mode": task_mode,
                "workflow_preset": task_spec.get("workflow_preset", ""),
                "execution_mode": execution_mode,
                "artifact_level": artifact_level,
                "effect_class": effect_class,
                "authority_surface": authority_surface,
                "execution_budget": execution_budget,
                "verification_strength": verification_strength,
                "output_intents": output_intents,
                "allowed_outputs": _allowed_outputs(task_mode, task_spec),
                "forbidden_outputs": _forbidden_outputs(task_mode, artifact_level),
                "check_profile": check_profile,
                "requires_human_decision": bool(execution_spec.get("requires_human_decision", False)),
                "contradictions": row_contradictions,
            }
        )
    return {
        "status": "ADVISORY",
        "model": "five_field_compiled_control_model",
        "fields": {
            "artifact_level": sorted(ARTIFACT_LEVELS),
            "effect_class": sorted(EFFECT_CLASSES),
            "authority_surface": sorted(AUTHORITY_SURFACES),
            "execution_budget": sorted(EXECUTION_BUDGETS),
            "verification_strength": sorted(VERIFICATION_STRENGTHS),
        },
        "presets": rows,
        "policy_surfaces": [
            "harness/task_mode_policy.yml",
            "harness/execution_mode_policy.yml",
            "harness/output_intent_policy.yml",
            "harness/source_capture_permission_policy.yml",
            "harness/check_profiles.yml",
        ],
        "cross_checks_run": cross_checks_run,
        "contradictions": contradictions,
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_compiled_mode_map(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Compiled Mode Map",
        "",
        "This is a read-only projection. It does not change runtime behavior.",
        "",
    ]
    for row in report.get("presets") or []:
        lines.extend(
            [
                f"## {row.get('preset')}",
                "",
                f"- artifact_level: {row.get('artifact_level')}",
                f"- effect_class: {row.get('effect_class')}",
                f"- authority_surface: {row.get('authority_surface')}",
                f"- execution_budget: {row.get('execution_budget')}",
                f"- verification_strength: {row.get('verification_strength')}",
                f"- workflow_preset: {row.get('workflow_preset') or 'none'}",
                f"- execution_mode: {row.get('execution_mode')}",
                f"- check_profile: {row.get('check_profile') or 'none'}",
                f"- requires_human_decision: {str(row.get('requires_human_decision')).lower()}",
            ]
        )
        if row.get("output_intents"):
            lines.append("- output_intents: " + ", ".join(row.get("output_intents") or []))
        if row.get("allowed_outputs"):
            lines.append("- allowed_outputs: " + ", ".join(row.get("allowed_outputs") or []))
        if row.get("forbidden_outputs"):
            lines.append("- forbidden_outputs: " + ", ".join(row.get("forbidden_outputs") or []))
        if row.get("contradictions"):
            lines.append("- contradictions: " + "; ".join(row.get("contradictions") or []))
        lines.append("")
    lines.append("cross_checks_run:")
    lines.extend(f"- {item}" for item in report.get("cross_checks_run") or [])
    lines.append("")
    lines.append("contradictions:")
    contradictions = report.get("contradictions") or []
    lines.extend(f"- {item}" for item in contradictions) if contradictions else lines.append("- none")
    lines.append("")
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
