"""Evaluation-first, authority-aware executable research rubrics.

An ExecutableRubric is a project contract, not a second research-state store.
It makes the evidence artifacts and satisfaction conditions for a bounded
ResearchJob explicit before work is treated as complete. Agent-generated
rubrics start as candidates; only a signed, scoped human approval can freeze
their scientific content for execution/verification.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml

from .authority import evaluate_for_action


POLICY = "AEROS-EXECUTABLE-RUBRIC-001"
FREEZE_FIELDS = (
    "unit_of_observation",
    "population",
    "required_fields",
    "join_keys",
    "minimum_coverage",
    "maximum_missingness",
    "probe_success_condition",
)


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path must remain inside the project: {path}") from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _missing_freeze_fields(values: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in FREEZE_FIELDS:
        value = values.get(field)
        present = bool(value) if isinstance(value, list) else bool(str(value or "").strip())
        if not present:
            missing.append(field)
    return missing


def _scientific_content_hash(rubric: dict[str, Any]) -> str:
    """Hash scientific content while excluding approval/projection metadata."""
    payload = deepcopy(rubric)
    payload.pop("status", None)
    payload.pop("scientific_freeze", None)
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def default_rubric_path(root: Path, job_id: str) -> Path:
    return root / "contracts" / "rubrics" / f"{_slug(job_id)}.yml"


def rubric_skeleton_for_job(job: Any) -> dict[str, Any]:
    """Compile the generic, agent-proposed portion of one ResearchJob rubric."""
    if str(getattr(job, "job_type", "")) != "data_probe":
        raise ValueError("ExecutableRubric v1 supports ResearchJob job_type=data_probe only")
    job_id = str(getattr(job, "job_id", "")).strip()
    target = str(getattr(job, "target", "")).strip()
    source = str(getattr(job, "source_candidate", "")).strip()
    objective = str(getattr(job, "objective", "")).strip()
    if not all((job_id, target, source, objective)):
        raise ValueError("ResearchJob must include job_id, target, source_candidate, and objective")
    artifact = f"audits/data_probe/{_slug(job_id)}.json"
    return {
        "version": 1,
        "policy": POLICY,
        "rubric_id": f"RUBRIC-{job_id}",
        "status": "candidate",
        "research_job": {"job_id": job_id, "job_type": "data_probe", "target": target, "source_candidate": source, "objective": objective},
        "scientific_freeze": {
            "state": "agent_proposed",
            "authority": "agent_proposed",
            "required_fields": list(FREEZE_FIELDS),
            "values": {},
            "missing_required_fields": list(FREEZE_FIELDS),
            "does_not_prove": ["that a human has accepted the scientific rubric", "data fitness, identification validity, claim support, or paper readiness"],
        },
        "criteria": [
            {
                "criterion_id": "human_frozen_probe_contract",
                "atomic_scientific_goal": "Define the unit, population, source fields, join keys, and success threshold before treating a probe as informative.",
                "required_analysis": "Human review and freeze of the data-probe scientific contract.",
                "required_evidence_artifacts": [],
                "satisfaction_condition": "All required freeze fields are explicit and a signed scoped approval binds this exact rubric content.",
                "verification": {"type": "signed_rubric_freeze"},
                "authority": "human_frozen",
            },
            {
                "criterion_id": "bounded_source_profile",
                "atomic_scientific_goal": "Observe the proposed source on a bounded sample without collecting or admitting production data.",
                "required_analysis": "Compute source identity, columns, and bounded row count.",
                "required_evidence_artifacts": [artifact],
                "satisfaction_condition": "The probe identifies the declared source and target, has a current source hash, observes at least one row, and covers frozen required fields.",
                "verification": {"type": "data_probe_artifact", "artifact": artifact},
                "authority": "machine_verify",
            },
            {
                "criterion_id": "probe_boundary_preserved",
                "atomic_scientific_goal": "Keep probe evidence below canonical, result, claim, and paper authority surfaces.",
                "required_analysis": "Check the probe's explicit non-claim boundary.",
                "required_evidence_artifacts": [artifact],
                "satisfaction_condition": "Artifact status is probe_observed and its does_not_prove list preserves canonical-admission and claim-support boundaries.",
                "verification": {"type": "probe_boundary", "artifact": artifact},
                "authority": "machine_verify",
            },
        ],
        "does_not_prove": ["scientific truth", "data fitness or representativeness beyond the bounded probe", "identification validity", "canonical data/result admission", "claim, gate, paper, or release approval"],
    }


def draft_executable_rubric(root: Path, job: Any) -> dict[str, Any]:
    """Ground a candidate probe rubric in visible DataContract fields only."""
    rubric = rubric_skeleton_for_job(job)
    contract = _load_yaml(root / "docs" / "data_contract.yml")
    data = contract.get("estimand_data_contract") or {}
    data = data if isinstance(data, dict) else {}
    values = {
        "unit_of_observation": str(data.get("unit_of_observation") or "").strip(),
        "population": str(data.get("population") or data.get("target_population") or "").strip(),
        "required_fields": _as_list(data.get("required_fields") or data.get("required_variables")),
        "join_keys": _as_list(data.get("join_keys") or data.get("linkage_keys")),
        "minimum_coverage": str(data.get("minimum_coverage") or "").strip(),
        "maximum_missingness": str(data.get("maximum_missingness") or "").strip(),
        "probe_success_condition": str(data.get("probe_success_condition") or "").strip(),
    }
    freeze = rubric["scientific_freeze"]
    freeze["values"] = values
    freeze["missing_required_fields"] = _missing_freeze_fields(values)
    return rubric


def validate_executable_rubric(rubric: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in ("version", "policy", "rubric_id", "status", "research_job", "scientific_freeze", "criteria"):
        if key not in rubric:
            failures.append(f"missing {key}")
    if rubric.get("policy") != POLICY:
        failures.append(f"policy must equal {POLICY}")
    if rubric.get("status") not in {"candidate", "human_frozen"}:
        failures.append("status must be candidate or human_frozen")
    job = rubric.get("research_job") or {}
    if not isinstance(job, dict) or job.get("job_type") != "data_probe":
        failures.append("v1 rubric must bind a data_probe ResearchJob")
    freeze = rubric.get("scientific_freeze") or {}
    if not isinstance(freeze, dict):
        failures.append("scientific_freeze must be a mapping")
    else:
        if [str(item) for item in freeze.get("required_fields") or []] != list(FREEZE_FIELDS):
            failures.append("scientific_freeze required_fields must use the v1 data-probe freeze set")
        if not isinstance(freeze.get("values"), dict):
            failures.append("scientific_freeze values must be a mapping")
    criteria = rubric.get("criteria") or []
    ids = [str(item.get("criterion_id") or "") for item in criteria if isinstance(item, dict)]
    if set(ids) != {"human_frozen_probe_contract", "bounded_source_profile", "probe_boundary_preserved"}:
        failures.append("criteria must contain the three v1 probe criteria exactly once")
    return failures


def load_executable_rubric(root: Path, path: str | Path) -> tuple[Path, dict[str, Any]]:
    candidate = Path(path)
    candidate = candidate if candidate.is_absolute() else root / candidate
    rel = _rel(root, candidate)
    if not candidate.is_file():
        raise FileNotFoundError(f"executable rubric is missing: {rel}")
    data = _load_yaml(candidate)
    failures = validate_executable_rubric(data)
    if failures:
        raise ValueError("invalid executable rubric: " + "; ".join(failures))
    return candidate, data


def write_executable_rubric(root: Path, rubric: dict[str, Any], path: str | Path | None = None) -> Path:
    job = rubric.get("research_job") or {}
    target = Path(path) if path else default_rubric_path(root, str(job.get("job_id") or "rubric"))
    target = target if target.is_absolute() else root / target
    _rel(root, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(rubric, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return target


def freeze_executable_rubric(root: Path, rubric_path: str | Path, approval_path: str | Path) -> dict[str, Any]:
    """Freeze exact candidate content only with existing signed authority evidence."""
    path, rubric = load_executable_rubric(root, rubric_path)
    if rubric.get("status") != "candidate":
        return {"status": "REFUSED", "reason": "only candidate rubrics may be frozen", "rubric_path": _rel(root, path)}
    freeze = rubric.get("scientific_freeze") or {}
    missing = _missing_freeze_fields(dict(freeze.get("values") or {}))
    if missing:
        return {"status": "REFUSED", "reason": f"cannot freeze while fields are missing: {', '.join(missing)}", "rubric_path": _rel(root, path)}
    approval = Path(approval_path)
    approval = approval if approval.is_absolute() else root / approval
    try:
        approval_rel = _rel(root, approval)
    except ValueError as exc:
        return {"status": "REFUSED", "reason": str(exc), "rubric_path": _rel(root, path)}
    approval_data = _load_yaml(approval)
    content_hash = _scientific_content_hash(rubric)
    scope = approval_data.get("authority_scope") or {}
    semantic_errors: list[str] = []
    if approval_data.get("rubric_id") != rubric.get("rubric_id"):
        semantic_errors.append("approval rubric_id does not match")
    if approval_data.get("decision") != "freeze_executable_rubric":
        semantic_errors.append("approval decision must be freeze_executable_rubric")
    if approval_data.get("rubric_content_sha256") != content_hash:
        semantic_errors.append("approval rubric_content_sha256 does not bind the candidate content")
    if not isinstance(scope, dict) or scope.get("executable_rubric_freeze_only") is not True:
        semantic_errors.append("approval must be scoped to executable_rubric_freeze_only")
    evidence = evaluate_for_action(root, approval, "rubric_freeze")
    if semantic_errors or not evidence.granted:
        reasons = list(semantic_errors)
        if not evidence.granted:
            reasons.append(evidence.reason)
        return {"status": "REFUSED", "reason": "; ".join(reasons), "rubric_path": _rel(root, path), "authority_evidence": evidence.to_dict()}
    frozen = deepcopy(rubric)
    frozen["status"] = "human_frozen"
    frozen["scientific_freeze"].update({
        "state": "human_frozen", "authority": "signed_human_approval", "approval_ref": approval_rel,
        "frozen_candidate_sha256": content_hash, "approval_evidence": evidence.to_dict(),
    })
    write_executable_rubric(root, frozen, path)
    return {"status": "FROZEN", "rubric_path": _rel(root, path), "authority_evidence": evidence.to_dict()}


def _verify_probe_criteria(root: Path, rubric: dict[str, Any]) -> list[dict[str, Any]]:
    job = rubric["research_job"]
    criteria = {str(item["criterion_id"]): item for item in rubric["criteria"]}
    artifact_rel = str((criteria["bounded_source_profile"].get("verification") or {}).get("artifact") or "")
    artifact = root / artifact_rel
    rows: list[dict[str, Any]] = [{"criterion_id": "human_frozen_probe_contract", "status": "verified", "reason": "signed scope/content binding and required frozen fields passed before criterion evaluation", "evidence_artifacts": []}]
    if not artifact.is_file():
        rows.extend([
            {"criterion_id": "bounded_source_profile", "status": "unmet", "reason": f"missing probe artifact: {artifact_rel}", "evidence_artifacts": [artifact_rel]},
            {"criterion_id": "probe_boundary_preserved", "status": "unmet", "reason": "probe artifact is missing", "evidence_artifacts": [artifact_rel]},
        ])
        return rows
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except Exception as exc:
        rows.extend([
            {"criterion_id": "bounded_source_profile", "status": "unmet", "reason": f"probe artifact is not valid JSON: {exc}", "evidence_artifacts": [artifact_rel]},
            {"criterion_id": "probe_boundary_preserved", "status": "unmet", "reason": "probe artifact is not parseable", "evidence_artifacts": [artifact_rel]},
        ])
        return rows
    reasons: list[str] = []
    source_rel = str(job.get("source_candidate") or "")
    if payload.get("source") != source_rel:
        reasons.append("probe source does not match frozen ResearchJob source_candidate")
    if payload.get("target") != job.get("target"):
        reasons.append("probe target does not match frozen ResearchJob target")
    source = root / source_rel
    if not source.is_file():
        reasons.append("frozen source_candidate is missing")
    elif payload.get("source_sha256") != sha256(source.read_bytes()).hexdigest():
        reasons.append("probe source_sha256 is stale or does not match the source")
    if int(payload.get("rows_observed") or 0) <= 0:
        reasons.append("probe observed no usable rows")
    required = set(_as_list((rubric.get("scientific_freeze") or {}).get("values", {}).get("required_fields")))
    missing_columns = sorted(required - {str(value) for value in payload.get("columns_observed") or []})
    if missing_columns:
        reasons.append("probe is missing frozen required_fields: " + ", ".join(missing_columns))
    rows.append({"criterion_id": "bounded_source_profile", "status": "verified" if not reasons else "unmet", "reason": "bounded source profile matches the frozen contract" if not reasons else "; ".join(reasons), "evidence_artifacts": [artifact_rel]})
    boundary: list[str] = []
    if payload.get("status") != "probe_observed":
        boundary.append("probe status must be probe_observed")
    if not {"canonical admission", "claim support"} <= {str(item) for item in payload.get("does_not_prove") or []}:
        boundary.append("probe does_not_prove must preserve canonical-admission and claim-support boundaries")
    rows.append({"criterion_id": "probe_boundary_preserved", "status": "verified" if not boundary else "unmet", "reason": "probe remains below canonical/claim authority" if not boundary else "; ".join(boundary), "evidence_artifacts": [artifact_rel]})
    return rows


def verify_executable_rubric(root: Path, rubric_path: str | Path) -> dict[str, Any]:
    path, rubric = load_executable_rubric(root, rubric_path)
    base = {
        "version": 1, "policy": POLICY, "rubric_id": rubric["rubric_id"], "rubric_path": _rel(root, path),
        "scientific_content_sha256": _scientific_content_hash(rubric),
        "does_not_prove": ["scientific truth", "data fitness or identification validity", "canonical admission", "claim support", "gate, paper, or release approval"],
    }
    freeze = rubric.get("scientific_freeze") or {}
    if rubric.get("status") != "human_frozen":
        return {**base, "status": "BLOCKED", "reason": "rubric is candidate-only; signed human freeze is required before verification", "criteria": [], "unmet_criteria": ["human_frozen_probe_contract"], "next_action": "Review and freeze the candidate rubric with scoped signed authority evidence."}
    missing = _missing_freeze_fields(dict(freeze.get("values") or {}))
    if missing:
        return {**base, "status": "BLOCKED", "reason": "frozen rubric is missing required fields: " + ", ".join(missing), "criteria": [], "unmet_criteria": ["human_frozen_probe_contract"], "next_action": "Repair the frozen contract through a new signed rubric-freeze approval."}
    expected_hash = str(freeze.get("frozen_candidate_sha256") or "")
    if expected_hash != _scientific_content_hash(rubric):
        return {**base, "status": "BLOCKED", "reason": "frozen scientific content differs from the signed candidate hash", "criteria": [], "unmet_criteria": ["human_frozen_probe_contract"], "next_action": "Do not execute; create a new signed approval for the changed rubric content."}
    approval_ref = str(freeze.get("approval_ref") or "")
    evidence = evaluate_for_action(root, root / approval_ref, "rubric_freeze") if approval_ref else None
    if evidence is None or not evidence.granted:
        reason = evidence.reason if evidence is not None else "frozen rubric has no approval_ref"
        return {**base, "status": "BLOCKED", "reason": "rubric freeze authority is not valid: " + reason, "criteria": [], "unmet_criteria": ["human_frozen_probe_contract"], "next_action": "Restore a valid signed, scoped rubric-freeze approval.", "authority_evidence": evidence.to_dict() if evidence else {}}
    rows = _verify_probe_criteria(root, rubric)
    unmet = [row["criterion_id"] for row in rows if row["status"] != "verified"]
    return {**base, "status": "PASS" if not unmet else "FAIL", "reason": "all frozen criteria verified" if not unmet else "one or more frozen criteria are unmet", "criteria": rows, "unmet_criteria": unmet, "next_action": "No unmet rubric criterion remains; a separate human decision is required for promotion." if not unmet else f"Address unmet rubric criterion(s): {', '.join(unmet)}.", "authority_evidence": evidence.to_dict()}


def write_verification_report(root: Path, report: dict[str, Any]) -> Path:
    target = root / "audits" / "executable_rubrics" / f"{_slug(str(report.get('rubric_id') or 'rubric'))}_verification.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def active_rubric_issue(root: Path) -> dict[str, Any] | None:
    """Return frozen-but-unmet rubrics only; candidates do not hijack Drive."""
    directory = root / "contracts" / "rubrics"
    if not directory.is_dir():
        return None
    for path in sorted(directory.glob("*.yml")):
        if _load_yaml(path).get("status") != "human_frozen":
            continue
        try:
            report = verify_executable_rubric(root, path)
        except (OSError, ValueError) as exc:
            return {"rubric_path": _rel(root, path), "status": "BLOCKED", "reason": str(exc), "unmet_criteria": ["rubric_parse"]}
        if report.get("status") != "PASS":
            return report
    return None
