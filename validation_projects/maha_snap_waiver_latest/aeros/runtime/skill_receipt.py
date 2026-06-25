"""Skill invocation receipts: audit external skill use under AEROS rules."""
from __future__ import annotations

from datetime import datetime, timezone
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


def load_core_skill_map(project_root: Path) -> dict[str, dict[str, Any]]:
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
    if recommended and not records and not waivers:
        waivers = [{
            "skill_class": "recommended_skills",
            "scope": "mechanical_revalidation",
            "reason": (
                "Runtime wrote this receipt during mechanical revalidation of existing "
                "artifacts; no external skill was invoked."
            ),
            "progress_label": "mechanical_hygiene",
        }]
    payload = {
        "version": 1,
        "task_id": contract.task_id,
        "generated_at": _now(),
        "contract_path": _rel(project_root, contract.path),
        "run_report_path": _rel(project_root, run_report_path),
        "allowed_skills": sorted(allowed),
        "recommended_skills": recommended,
        "required_skill_classes": required_classes,
        "skill_waivers": waivers,
        "skills_used": [r["skill_name"] for r in records],
        "invocations": records,
        "verdict": "fail" if any(not r["known_to_aeros"] or not r["allowed_by_contract"] for r in records) else "pass",
    }
    path = receipt_path(project_root, contract.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


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
        if required_classes:
            used = set(payload.get("skills_used") or [])
            used_stages = {str(skill_map.get(name, {}).get("aeros_stage", "")).strip() for name in used}
            missing = sorted(cls for cls in required_classes if cls not in waiver_classes and cls not in used and cls not in used_stages)
            for cls in missing:
                failures.append(f"{task_id}: required skill class {cls!r} has neither invocation nor waiver")
        if recommended and not payload.get("skills_used") and not waivers:
            failures.append(f"{task_id}: recommended skills declared but no invocation or waiver recorded")
    return failures
