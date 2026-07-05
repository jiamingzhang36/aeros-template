"""Completion receipts: machine-checkable proof before a task may be passed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

import yaml

from .contract import Contract

RECEIPT_DIR = Path("agent_runs/completion_receipts")
PROGRESS_DOMAINS = {"research", "runtime", "governance"}
RUNTIME_LOG_PREFIXES = ("agent_runs", "outputs/logs", "outputs/context")
STAGING_ARTIFACT_PREFIXES = (
    "work/",
    "audits/",
    "quality_reports/",
    "source_snapshots/",
    "data/backfill/",
    "output/tex/",
    "outputs/tex/",
    "discovery/literature/missing_fulltext_queue",
    "discovery/literature/source_promotion_queue",
)


@dataclass(frozen=True)
class CompletionReceipt:
    path: Path
    passed: bool
    failures: list[str]
    payload: dict[str, Any]


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


def _exists(root: Path, rel: str) -> bool:
    return bool(rel) and (root / rel).exists()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_record(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    record: dict[str, Any] = {
        "path": rel,
        "exists": path.exists(),
        "type": "missing",
        "sha256": "",
        "bytes": 0,
    }
    if path.is_file():
        record.update({
            "type": "file",
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        })
    elif path.is_dir():
        # Keep directory evidence lightweight: existence + direct child count.
        # Detailed directory lineage belongs in artifact/provenance manifests.
        record.update({
            "type": "directory",
            "entries": len(list(path.iterdir())),
        })
    return record


def _receipt_path(project_root: Path, task_id: str) -> Path:
    return project_root / RECEIPT_DIR / f"{task_id}_completion_receipt.yml"


def latest_run_report(project_root: Path, task_id: str) -> str:
    reports = sorted((project_root / "agent_runs").glob(f"{task_id}_*.md"))
    reports = [p for p in reports if p.parent.name != "completion_receipts"]
    return _rel(project_root, reports[-1]) if reports else ""


def _check_rows(check_results: list[Any] | None) -> tuple[list[str], list[str], list[str]]:
    required: list[str] = []
    passed: list[str] = []
    failed: list[str] = []
    for item in check_results or []:
        name = str(getattr(item, "name", "") or "")
        ok = bool(getattr(item, "passed", False))
        if not name:
            continue
        required.append(name)
        (passed if ok else failed).append(name)
    return required, passed, failed


def _check_attestations(check_results: list[Any] | None) -> list[dict[str, Any]]:
    attestations: list[dict[str, Any]] = []
    for item in check_results or []:
        name = str(getattr(item, "name", "") or "")
        if not name:
            continue
        attestations.append({
            "name": name,
            "passed": bool(getattr(item, "passed", False)),
            "command": list(getattr(item, "command", []) or []),
            "exit_code": int(getattr(item, "exit_code", 0 if getattr(item, "passed", False) else 1)),
            "elapsed_seconds": float(getattr(item, "elapsed_seconds", 0.0) or 0.0),
        })
    return attestations


def _check_key(name: str) -> str:
    """Normalize check names for comparisons.

    Contracts often name the script file (``check_foo.py``), while structured
    check output reports the logical check id (``check_foo``).
    """
    value = str(name or "").strip()
    return value[:-3] if value.endswith(".py") else value


def _same_check_set(left: list[str], right: list[str]) -> bool:
    return sorted(_check_key(item) for item in left) == sorted(_check_key(item) for item in right)


def _is_runtime_log(rel: str) -> bool:
    value = str(rel or "").strip().rstrip("/")
    return any(value == prefix.rstrip("/") or value.startswith(prefix.rstrip("/") + "/") for prefix in RUNTIME_LOG_PREFIXES)


def _is_staging_artifact(rel: str) -> bool:
    value = str(rel or "").strip()
    return any(value == prefix.rstrip("/") or value.startswith(prefix) for prefix in STAGING_ARTIFACT_PREFIXES)


def progress_domain_for(work_lane: str, *, authority_status: str = "") -> str:
    lane = str(work_lane or "").strip().lower()
    authority = str(authority_status or "").strip().lower()
    if authority in {"human_decision_recorded", "human_decision_required"}:
        return "governance"
    if lane in {"harness", "runtime"}:
        return "runtime"
    return "research"


def write_completion_receipt(
    project_root: Path,
    contract: Contract,
    *,
    mode: str,
    check_results: list[Any] | None,
    run_report_path: Path | str | None = None,
    skill_receipt_path: Path | str | None = None,
    open_issues: list[str] | None = None,
    human_decision_needed: bool = False,
    input_fingerprint: str = "",
    output_fingerprint: str = "",
    dependency_fingerprint: str = "",
) -> CompletionReceipt:
    """Write a completion receipt and return whether it justifies passed status."""
    required, checks_passed, checks_failed = _check_rows(check_results)
    expected = [str(p) for p in contract.allowed_outputs]
    found = [p for p in expected if _exists(project_root, p)]
    missing_outputs = [p for p in expected if not _exists(project_root, p) and p != "agent_runs"]
    output_records = [_artifact_record(project_root, p) for p in expected]
    staging_outputs = [
        row for row in output_records
        if row.get("exists")
        and not _is_runtime_log(str(row.get("path", "")))
        and _is_staging_artifact(str(row.get("path", "")))
    ]
    substantive_outputs = [
        row for row in output_records
        if row.get("exists")
        and not _is_runtime_log(str(row.get("path", "")))
        and not _is_staging_artifact(str(row.get("path", "")))
    ]
    progress_outputs = substantive_outputs or staging_outputs
    report_rel = _rel(project_root, run_report_path) or latest_run_report(project_root, contract.task_id)
    receipt_required = contract.evidence_receipt_required
    evidence_receipt_exists = _exists(project_root, contract.receipt_path) if receipt_required else False
    issues = list(open_issues or [])
    failures: list[str] = []

    if not _same_check_set(required, contract.checks):
        failures.append("receipt check list does not match task contract checks")
    if checks_failed:
        failures.append("one or more required checks failed")
    if not progress_outputs:
        failures.append("no allowed output artifact exists outside runtime logs")
    if mode == "agent_run" and not report_rel:
        failures.append("agent run completion requires a run report")
    if receipt_required and not evidence_receipt_exists:
        failures.append(f"required evidence receipt missing: {contract.receipt_path}")
    if contract.automation_class == "approval_required" and contract.gate_status.startswith("blocked_"):
        failures.append(f"task is blocked: {contract.automation_class}/{contract.gate_status}")
    if human_decision_needed:
        failures.append("human decision needed")
    if issues:
        failures.append("open issues remain")

    verdict = "fail" if failures else "pass"
    if substantive_outputs:
        progress_class = "substantive"
        progress_label = "SUBSTANTIVE_PRODUCED"
    elif staging_outputs:
        progress_class = "routing"
        progress_label = "ROUTE_READY"
    else:
        progress_class = "none"
        progress_label = "CHECK_PASS"
    verification_level = "checks_passed_with_artifact_hashes" if verdict == "pass" else "failed_attestation"
    authority_status = "human_decision_required" if human_decision_needed else "no_new_authority"
    progress_domain = progress_domain_for(contract.work_lane, authority_status=authority_status)
    payload = {
        "version": 5,
        "task_id": contract.task_id,
        "generated_at": _now(),
        "completion_mode": mode,
        "claimed_status": "passed",
        "declared_outcome": "complete",
        "outcome_kind": "complete",
        "contract_status": "passed" if verdict == "pass" else "failed",
        "verification_level": verification_level,
        "progress_domain": progress_domain,
        "progress_class": progress_class,
        "progress_label": progress_label,
        "authority_status": authority_status,
        "work_lane": contract.work_lane,
        "contract_path": _rel(project_root, contract.path) if contract.path else "",
        "automation_class": contract.automation_class,
        "gate_status": contract.gate_status,
        "run_report_path": report_rel,
        "skill_invocation_receipt_path": _rel(project_root, skill_receipt_path),
        "allowed_outputs_expected": expected,
        "allowed_outputs_found": found,
        "allowed_outputs_missing": missing_outputs,
        "actual_outputs": output_records,
        "staging_artifact_paths": [str(row.get("path", "")) for row in staging_outputs],
        "substantive_evidence_paths": [str(row.get("path", "")) for row in substantive_outputs],
        "checks_required": list(contract.checks),
        "checks_run": required,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "check_attestations": _check_attestations(check_results),
        "evidence_receipt_required": receipt_required,
        "evidence_receipt_path": contract.receipt_path,
        "evidence_receipt_exists": evidence_receipt_exists,
        "evidence_delta_ref": "",
        "substantive_progress": bool(substantive_outputs),
        "protected_definition_change_declared": False,
        "claim_change_declared": False,
        "human_decision_needed": bool(human_decision_needed),
        "open_issues": issues,
        "does_not_prove": [
            "scientific validity",
            "identification quality",
            "claim support",
            "human gate approval",
        ],
        "input_fingerprint": input_fingerprint,
        "output_fingerprint": output_fingerprint,
        "dependency_fingerprint": dependency_fingerprint,
        "completion_verdict": verdict,
        "failures": failures,
    }
    path = _receipt_path(project_root, contract.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return CompletionReceipt(path=path, passed=verdict == "pass", failures=failures, payload=payload)


def validate_completion_receipts(project_root: Path, contracts: dict[str, tuple[Contract, Path]], state: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    tasks = state.get("tasks", {}) or {}
    for task_id, entry in sorted(tasks.items()):
        if entry.get("status") != "passed":
            continue
        if task_id not in contracts:
            failures.append(f"{task_id}: passed in state but task contract is missing")
            continue
        contract, _path = contracts[task_id]
        path = _receipt_path(project_root, task_id)
        if not path.exists():
            failures.append(f"{task_id}: passed but missing completion receipt ({_rel(project_root, path)})")
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            failures.append(f"{task_id}: completion receipt is unreadable ({exc})")
            continue
        if payload.get("completion_verdict") != "pass":
            failures.append(f"{task_id}: completion receipt verdict is not pass")
        if payload.get("task_id") != task_id:
            failures.append(f"{task_id}: completion receipt task_id mismatch")
        if int(payload.get("version") or 1) < 2:
            failures.append(f"{task_id}: completion receipt is legacy version <2; rerun recover --check or revalidate")
        if payload.get("declared_outcome") != "complete":
            failures.append(f"{task_id}: completion receipt declared_outcome is not complete")
        if int(payload.get("version") or 1) >= 3:
            if payload.get("outcome_kind") != "complete":
                failures.append(f"{task_id}: completion receipt outcome_kind is not complete")
            if payload.get("contract_status") != "passed":
                failures.append(f"{task_id}: completion receipt contract_status is not passed")
            if payload.get("verification_level") not in {"checks_passed_with_artifact_hashes", "checks_passed"}:
                failures.append(f"{task_id}: completion receipt verification_level is not sufficient")
            staging_paths = list(payload.get("staging_artifact_paths") or [])
            substantive_paths = list(payload.get("substantive_evidence_paths") or [])
            if payload.get("progress_class") != "substantive":
                if int(payload.get("version") or 1) >= 5 and payload.get("progress_class") == "routing" and staging_paths and not substantive_paths:
                    pass
                else:
                    failures.append(f"{task_id}: completion receipt progress_class is not substantive or staging-routing")
            if payload.get("progress_label") not in {"SUBSTANTIVE_PRODUCED", "SUBSTANTIVE_DONE", "CAPTURE_LOGGED", "ROUTE_READY"}:
                failures.append(f"{task_id}: completion receipt progress_label is not an allowed completion label")
            if not payload.get("authority_status"):
                failures.append(f"{task_id}: completion receipt authority_status missing")
        if int(payload.get("version") or 1) >= 4:
            if payload.get("progress_domain") not in PROGRESS_DOMAINS:
                failures.append(f"{task_id}: completion receipt progress_domain is invalid")
        if int(payload.get("version") or 1) >= 5:
            if not isinstance(payload.get("staging_artifact_paths"), list):
                failures.append(f"{task_id}: completion receipt staging_artifact_paths is missing or invalid")
            if not isinstance(payload.get("substantive_evidence_paths"), list):
                failures.append(f"{task_id}: completion receipt substantive_evidence_paths is missing or invalid")
        if payload.get("work_lane") != contract.work_lane:
            failures.append(f"{task_id}: completion receipt work_lane does not match contract")
        if not _same_check_set(list(payload.get("checks_required") or []), list(contract.checks)):
            failures.append(f"{task_id}: completion receipt checks do not match contract")
        if not _same_check_set(list(payload.get("checks_run") or []), list(contract.checks)):
            failures.append(f"{task_id}: completion receipt does not record all required checks")
        if payload.get("checks_failed"):
            failures.append(f"{task_id}: completion receipt records failed checks")
        actual_outputs = list(payload.get("actual_outputs") or [])
        staging_outputs = [
            row for row in actual_outputs
            if row.get("exists")
            and not _is_runtime_log(str(row.get("path", "")))
            and _is_staging_artifact(str(row.get("path", "")))
        ]
        substantive_outputs = [
            row for row in actual_outputs
            if row.get("exists")
            and not _is_runtime_log(str(row.get("path", "")))
            and not _is_staging_artifact(str(row.get("path", "")))
        ]
        progress_outputs = substantive_outputs or staging_outputs
        if not progress_outputs:
            failures.append(f"{task_id}: completion receipt has no allowed output artifact outside runtime logs")
        for row in progress_outputs:
            if row.get("type") == "file" and not row.get("sha256"):
                failures.append(f"{task_id}: file output lacks sha256: {row.get('path')}")
        check_attestations = list(payload.get("check_attestations") or [])
        if len(check_attestations) != len(contract.checks):
            failures.append(f"{task_id}: completion receipt lacks check attestations")
        for row in check_attestations:
            if not row.get("command"):
                failures.append(f"{task_id}: check attestation missing command for {row.get('name')}")
            if row.get("exit_code") not in (0,):
                failures.append(f"{task_id}: check attestation records nonzero exit for {row.get('name')}")
        if not payload.get("does_not_prove"):
            failures.append(f"{task_id}: completion receipt missing does_not_prove boundary")
        if contract.evidence_receipt_required and not payload.get("evidence_receipt_exists"):
            failures.append(f"{task_id}: required evidence receipt missing in completion receipt")
        if contract.automation_class == "approval_required" and contract.gate_status.startswith("blocked_"):
            failures.append(f"{task_id}: blocked approval-required task cannot be passed")
        for key in ("input_fingerprint", "output_fingerprint", "dependency_fingerprint"):
            expected = entry.get(key, "")
            if expected and payload.get(key) != expected:
                failures.append(f"{task_id}: completion receipt {key} does not match runtime state")
    return failures
