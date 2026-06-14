"""Completion receipts: machine-checkable proof before a task may be passed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .contract import Contract

RECEIPT_DIR = Path("agent_runs/completion_receipts")


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


def write_completion_receipt(
    project_root: Path,
    contract: Contract,
    *,
    mode: str,
    check_results: list[Any] | None,
    run_report_path: Path | str | None = None,
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
    report_rel = _rel(project_root, run_report_path) or latest_run_report(project_root, contract.task_id)
    receipt_required = contract.evidence_receipt_required
    evidence_receipt_exists = _exists(project_root, contract.receipt_path) if receipt_required else False
    issues = list(open_issues or [])
    failures: list[str] = []

    if sorted(required) != sorted(contract.checks):
        failures.append("receipt check list does not match task contract checks")
    if checks_failed:
        failures.append("one or more required checks failed")
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
    payload = {
        "version": 1,
        "task_id": contract.task_id,
        "generated_at": _now(),
        "completion_mode": mode,
        "claimed_status": "passed",
        "contract_path": _rel(project_root, contract.path) if contract.path else "",
        "automation_class": contract.automation_class,
        "gate_status": contract.gate_status,
        "run_report_path": report_rel,
        "allowed_outputs_expected": expected,
        "allowed_outputs_found": found,
        "allowed_outputs_missing": missing_outputs,
        "checks_required": list(contract.checks),
        "checks_run": required,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "evidence_receipt_required": receipt_required,
        "evidence_receipt_path": contract.receipt_path,
        "evidence_receipt_exists": evidence_receipt_exists,
        "protected_definition_change_declared": False,
        "claim_change_declared": False,
        "human_decision_needed": bool(human_decision_needed),
        "open_issues": issues,
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
        if sorted(payload.get("checks_required") or []) != sorted(contract.checks):
            failures.append(f"{task_id}: completion receipt checks do not match contract")
        if sorted(payload.get("checks_run") or []) != sorted(contract.checks):
            failures.append(f"{task_id}: completion receipt does not record all required checks")
        if payload.get("checks_failed"):
            failures.append(f"{task_id}: completion receipt records failed checks")
        if contract.evidence_receipt_required and not payload.get("evidence_receipt_exists"):
            failures.append(f"{task_id}: required evidence receipt missing in completion receipt")
        if contract.automation_class == "approval_required" and contract.gate_status.startswith("blocked_"):
            failures.append(f"{task_id}: blocked approval-required task cannot be passed")
        for key in ("input_fingerprint", "output_fingerprint", "dependency_fingerprint"):
            expected = entry.get(key, "")
            if expected and payload.get(key) != expected:
                failures.append(f"{task_id}: completion receipt {key} does not match runtime state")
    return failures
