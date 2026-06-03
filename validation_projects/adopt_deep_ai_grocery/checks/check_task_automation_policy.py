#!/usr/bin/env python3
"""Validate task automation class, receipt, and approval semantics."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


TASK_DIR = Path("tasks")
ALLOWED_AUTOMATION_CLASSES = {
    "auto_rerunnable",
    "receipt_audited",
    "frozen_evidence",
    "approval_required",
}
ALLOWED_GATE_STATUSES = {
    "pending",
    "done_auto_verified",
    "done_human_verified_with_receipt",
    "done_frozen_evidence_verified",
    "skipped_unverified",
    "needs_receipt_audit",
    "blocked_requires_approval",
    "blocked_missing_credentials",
    "blocked_missing_source_snapshot",
}
RECEIPT_REQUIRED_CLASSES = {"receipt_audited", "frozen_evidence"}
BLOCKED_CLASSES = {"approval_required"}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _receipt_has_required_fields(path: Path) -> list[str]:
    if not path.exists():
        return [f"receipt_path does not exist: {path}"]
    text = path.read_text(encoding="utf-8", errors="ignore")
    missing = []
    for marker in (
        "reviewed_by:",
        "reviewed_at:",
        "source_snapshot:",
        "coverage:",
        "disagreement_log:",
        "human_decision:",
    ):
        if marker not in text:
            missing.append(f"{path}: missing receipt marker {marker}")
    return missing


def main() -> int:
    failures: list[str] = []
    contracts = sorted(TASK_DIR.rglob("*.yml"))
    for path in contracts:
        data = _load(path)
        task_id = str(data.get("task_id", path.name))
        automation_class = str(data.get("automation_class", "")).strip()
        gate_status = str(data.get("gate_status", "")).strip()
        receipt_required = bool(data.get("evidence_receipt_required", False))
        receipt_path = str(data.get("receipt_path", "") or "").strip()

        if automation_class not in ALLOWED_AUTOMATION_CLASSES:
            failures.append(f"{task_id}: invalid or missing automation_class")
        if gate_status not in ALLOWED_GATE_STATUSES:
            failures.append(f"{task_id}: invalid or missing gate_status")
        if gate_status == "skipped":
            failures.append(f"{task_id}: use explicit skipped_unverified/blocked/done status, not skipped")

        if automation_class in RECEIPT_REQUIRED_CLASSES and not receipt_required:
            failures.append(f"{task_id}: {automation_class} must set evidence_receipt_required: true")
        if receipt_required and not receipt_path:
            failures.append(f"{task_id}: receipt required but receipt_path is empty")
        if automation_class in BLOCKED_CLASSES and not gate_status.startswith("blocked_"):
            failures.append(f"{task_id}: approval_required tasks must start blocked_* until approved")
        if automation_class == "auto_rerunnable" and receipt_required:
            failures.append(f"{task_id}: auto_rerunnable should not require a human receipt")

        if gate_status in {"done_human_verified_with_receipt", "done_frozen_evidence_verified"}:
            if not receipt_path:
                failures.append(f"{task_id}: done-with-receipt status requires receipt_path")
            else:
                failures.extend(_receipt_has_required_fields(Path(receipt_path)))

    if failures:
        print("FAIL: task automation policy problems detected:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1

    print(f"PASS: task automation policy valid ({len(contracts)} contract(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
