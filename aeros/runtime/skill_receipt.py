"""Skill invocation receipts: audit external skill use under AEROS rules."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .contract import Contract

RECEIPT_DIR = Path("agent_runs/skill_invocations")
SKILL_MAP = Path("harness/skill_map_core.yml")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(root: Path, path: Path | str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


@lru_cache(maxsize=16)
def load_core_skill_map(project_root: Path) -> dict[str, dict[str, Any]]:
    """Load the immutable per-process skill registry once per project root.

    Validation may inspect hundreds of task contracts. Re-parsing the same
    registry for every contract adds cost without adding evidence; each AEROS
    command is a fresh process, so process-local caching cannot hide changes
    between runs.
    """
    path = project_root / SKILL_MAP
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    skills = data.get("skills", {}) if isinstance(data, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for raw in skills.values():
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name", "")).strip()
        if name:
            out[name] = raw
    return out


def receipt_path(project_root: Path, task_id: str) -> Path:
    return project_root / RECEIPT_DIR / f"{task_id}_skill_invocations.yml"


def write_skill_invocation_receipt(
    project_root: Path,
    contract: Contract,
    *,
    skills_used: list[str],
    run_report_path: Path | str | None = None,
    skill_waivers: list[dict[str, Any]] | None = None,
) -> Path:
    """Write an audit receipt for the skills declared by the runtime report.

    This does not call skills. It records whether any declared skill is known to
    AEROS and whether it is allowed by the task contract.
    """
    skill_map = load_core_skill_map(project_root)
    allowed = set(str(s).strip() for s in (contract.raw.get("allowed_skills") or []) if str(s).strip())
    recommended = sorted(str(s).strip() for s in (contract.raw.get("recommended_skills") or []) if str(s).strip())
    try:
        from .skill_obligation import infer_skill_obligations, obligation_classes, required_skill_classes_for_profile

        obligations = sorted(infer_skill_obligations(project_root, contract))
        required_classes = sorted(required_skill_classes_for_profile(project_root, contract))
        classes = obligation_classes(project_root)
        for cls in required_classes:
            allowed.update(str(skill).strip() for skill in (classes.get(cls, {}).get("skills") or []) if str(skill).strip())
    except Exception:
        obligations = sorted(str(s).strip() for s in (contract.raw.get("skill_obligations") or []) if str(s).strip())
        required_classes = sorted(str(s).strip() for s in (contract.raw.get("required_skill_classes") or []) if str(s).strip())
    waivers = [w for w in (skill_waivers or contract.raw.get("skill_waivers") or []) if isinstance(w, dict)]
    records: list[dict[str, Any]] = []
    for name in sorted({s for s in skills_used if s and s != "none" and s != "n/a"}):
        meta = skill_map.get(name, {})
        records.append({
            "skill_name": name,
            "known_to_aeros": bool(meta),
            "allowed_by_contract": name in allowed,
            "source": meta.get("source", ""),
            "tier": meta.get("tier", ""),
            "use_status": meta.get("use_status", ""),
            "aeros_stage": meta.get("aeros_stage", ""),
            "human_gate_required": bool(meta.get("human_gate_required", False)),
            "aeros_constraints": meta.get("aeros_constraints", []),
        })
    too_many_dynamic_skills = len(records) > 3
    missing_skill_decision = bool(required_classes and not records and not waivers)
    payload = {
        "version": 1,
        "task_id": contract.task_id,
        "generated_at": _now(),
        "contract_path": _rel(project_root, contract.path),
        "run_report_path": _rel(project_root, run_report_path),
        "allowed_skills": sorted(allowed),
        "recommended_skills": recommended,
        "required_skill_classes": required_classes,
        "skill_obligations": obligations,
        "skill_waivers": waivers,
        "skills_used": [r["skill_name"] for r in records],
        "invocations": records,
        "missing_skill_decision": missing_skill_decision,
        "max_dynamic_skills": 3,
        "too_many_dynamic_skills": too_many_dynamic_skills,
        "verdict": "fail" if missing_skill_decision or too_many_dynamic_skills or any(not r["known_to_aeros"] or not r["allowed_by_contract"] for r in records) else "pass",
    }
    path = receipt_path(project_root, contract.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def build_skill_use_attestation(
    project_root: Path,
    contract: Contract,
    *,
    skill_receipt_path: Path | str | None = None,
) -> dict[str, Any]:
    """Enforce use-or-waive only for explicitly required skill classes."""
    skill_map = load_core_skill_map(project_root)
    try:
        from .skill_obligation import infer_skill_obligations, obligation_classes, required_skill_classes_for_profile

        obligations = sorted(set(infer_skill_obligations(project_root, contract)))
        required_classes = sorted(set(required_skill_classes_for_profile(project_root, contract)))
        class_specs = obligation_classes(project_root)
    except Exception:
        obligations = sorted(str(s).strip() for s in (contract.raw.get("skill_obligations") or []) if str(s).strip())
        required_classes = sorted({str(s).strip() for s in (contract.raw.get("required_skill_classes") or []) if str(s).strip()})
        class_specs = {}
    recommended = sorted(str(s).strip() for s in (contract.raw.get("recommended_skills") or []) if str(s).strip())
    allowed = sorted(str(s).strip() for s in (contract.raw.get("allowed_skills") or []) if str(s).strip())
    contract_waivers = [w for w in (contract.raw.get("skill_waivers") or []) if isinstance(w, dict)]
    receipt_rel = _rel(project_root, skill_receipt_path)
    receipt_payload: dict[str, Any] = {}
    receipt_present = False
    if skill_receipt_path:
        path = Path(skill_receipt_path)
        if not path.is_absolute():
            path = project_root / path
        if path.exists():
            receipt_present = True
            try:
                loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if isinstance(loaded, dict):
                    receipt_payload = loaded
            except yaml.YAMLError:
                receipt_payload = {"verdict": "fail", "unreadable": True}
    skills_used = sorted(str(s).strip() for s in (receipt_payload.get("skills_used") or []) if str(s).strip())
    receipt_waivers = [w for w in (receipt_payload.get("skill_waivers") or []) if isinstance(w, dict)]
    waivers = receipt_waivers or contract_waivers
    waiver_classes = {
        str(w.get("skill_class", "")).strip()
        for w in waivers
        if isinstance(w, dict) and str(w.get("skill_class", "")).strip()
    }
    used_stages = {
        str(skill_map.get(name, {}).get("aeros_stage", "")).strip()
        for name in skills_used
        if str(skill_map.get(name, {}).get("aeros_stage", "")).strip()
    }
    used_classes = {
        cls for cls, spec in class_specs.items()
        if set(str(skill) for skill in (spec.get("skills") or [])) & set(skills_used)
    }
    failures: list[str] = []
    use_or_waive_required = bool(required_classes)
    missing_classes = sorted(
        cls for cls in required_classes
        if cls not in waiver_classes and "all" not in waiver_classes and cls not in skills_used and cls not in used_stages and cls not in used_classes
    )
    if use_or_waive_required and not receipt_present and not waivers:
        failures.append("skill use-or-waive decision is required but no skill receipt or waiver is recorded")
    if receipt_payload.get("unreadable"):
        failures.append("skill invocation receipt is unreadable")
    if receipt_payload.get("verdict") == "fail":
        failures.append("skill invocation receipt verdict is fail")
    if receipt_payload.get("missing_skill_decision"):
        failures.append("skill invocation receipt reports a missing skill decision")
    if receipt_payload.get("too_many_dynamic_skills") or len(skills_used) > 3:
        failures.append("skill invocation exceeds the dynamic maximum of three skills")
    for cls in missing_classes:
        failures.append(f"required skill class {cls!r} has neither invocation nor waiver")
    verdict = "not_required"
    if use_or_waive_required:
        verdict = "fail" if failures else "pass"
    return {
        "version": 1,
        "requirement": "required_class_use_or_waive_else_optional",
        "use_or_waive_required": use_or_waive_required,
        "receipt_path": receipt_rel,
        "receipt_present": receipt_present,
        "required_skill_classes": required_classes,
        "recommended_skills": recommended,
        "allowed_skills": allowed,
        "skills_used": skills_used,
        "used_skill_classes": sorted(used_stages | used_classes),
        "skill_waivers": waivers,
        "waiver_classes": sorted(waiver_classes),
        "missing_skill_classes": missing_classes,
        "missing_skill_decision": bool(failures) if use_or_waive_required else False,
        "verdict": verdict,
        "failures": failures,
        "does_not_prove": [
            "that the skill advice was correct",
            "that the agent followed the skill perfectly",
            "that research claims are supported",
            "that a human gate is approved",
        ],
    }


def validate_skill_invocations(project_root: Path, contracts: dict[str, tuple[Contract, Path]]) -> list[str]:
    failures: list[str] = []
    skill_map = load_core_skill_map(project_root)
    from .skill_router import validate_skill_contracts

    failures.extend(validate_skill_contracts(project_root, contracts))
    for task_id, (contract, _path) in sorted(contracts.items()):
        path = receipt_path(project_root, task_id)
        if not path.exists():
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            failures.append(f"{task_id}: skill invocation receipt unreadable ({exc})")
            continue
        allowed = set(str(s).strip() for s in (contract.raw.get("allowed_skills") or []) if str(s).strip())
        recommended = set(str(s).strip() for s in (contract.raw.get("recommended_skills") or []) if str(s).strip())
        required_classes = set(str(s).strip() for s in (contract.raw.get("required_skill_classes") or []) if str(s).strip())
        waivers = payload.get("skill_waivers") or []
        waiver_classes = {str(w.get("skill_class", "")).strip() for w in waivers if isinstance(w, dict)}
        if payload.get("task_id") != task_id:
            failures.append(f"{task_id}: skill invocation receipt task_id mismatch")
        for name in payload.get("skills_used") or []:
            if name not in skill_map:
                failures.append(f"{task_id}: skill {name!r} is not in harness/skill_map_core.yml")
            if name not in allowed:
                failures.append(f"{task_id}: skill {name!r} is not allowed by task contract")
        if payload.get("verdict") == "fail":
            failures.append(f"{task_id}: skill invocation receipt verdict is fail")
        if payload.get("missing_skill_decision"):
            failures.append(f"{task_id}: skill obligation/recommendation has neither invocation nor explicit waiver")
        if required_classes:
            used = set(payload.get("skills_used") or [])
            used_stages = {str(skill_map.get(name, {}).get("aeros_stage", "")).strip() for name in used}
            try:
                from .skill_obligation import obligation_classes

                class_specs = obligation_classes(project_root)
            except Exception:
                class_specs = {}
            used_classes = {
                cls for cls, spec in class_specs.items()
                if set(str(skill) for skill in (spec.get("skills") or [])) & used
            }
            missing = sorted(
                cls for cls in required_classes
                if cls not in waiver_classes
                and cls not in used
                and cls not in used_stages
                and cls not in used_classes
            )
            for cls in missing:
                failures.append(f"{task_id}: required skill class {cls!r} has neither invocation nor waiver")
        if recommended and not payload.get("skills_used") and not waivers:
            failures.append(f"{task_id}: recommended skills declared but no invocation or waiver recorded")
    return failures
