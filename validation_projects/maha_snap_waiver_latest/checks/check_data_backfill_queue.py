#!/usr/bin/env python3
"""Validate AEROS data backfill queue semantics when a queue exists."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


QUEUE = Path("data/backfill/backfill_queue.yml")
POLICY = Path("harness/automation_policy.yml")
ALLOWED_CLASSES = {"auto_rerunnable", "receipt_audited", "frozen_evidence", "approval_required"}
ALLOWED_STATUSES = {
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


def _load_policy() -> tuple[set[str], set[str]]:
    if not POLICY.exists():
        return ALLOWED_CLASSES, ALLOWED_STATUSES
    data = yaml.safe_load(POLICY.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return ALLOWED_CLASSES, ALLOWED_STATUSES
    classes = data.get("automation_classes", {})
    statuses = data.get("gate_statuses", [])
    allowed_classes = set(classes) if isinstance(classes, dict) and classes else ALLOWED_CLASSES
    allowed_statuses = set(statuses) if isinstance(statuses, list) and statuses else ALLOWED_STATUSES
    return allowed_classes, allowed_statuses


def main() -> int:
    if not QUEUE.exists():
        print("SKIP: data backfill queue not present")
        return 0
    allowed_classes, allowed_statuses = _load_policy()
    data = yaml.safe_load(QUEUE.read_text(encoding="utf-8")) or {}
    items = data.get("items", []) if isinstance(data, dict) else []
    failures: list[str] = []
    if not isinstance(items, list):
        failures.append("queue items must be a list")
        items = []
    for item in items:
        if not isinstance(item, dict):
            failures.append("queue item must be a mapping")
            continue
        task_id = str(item.get("task_id", "(missing)"))
        automation_class = str(item.get("automation_class", ""))
        gate_status = str(item.get("gate_status", ""))
        if automation_class not in allowed_classes:
            failures.append(f"{task_id}: invalid automation_class {automation_class!r}")
        if gate_status not in allowed_statuses:
            failures.append(f"{task_id}: invalid gate_status {gate_status!r}")
        approval = item.get("approval", {})
        approved = (
            isinstance(approval, dict)
            and bool(approval.get("approved_by"))
            and bool(approval.get("source_snapshot"))
        )
        if automation_class == "approval_required" and not gate_status.startswith("blocked_") and not approved:
            failures.append(f"{task_id}: approval_required item must be blocked unless approval metadata is recorded")
        if automation_class == "auto_rerunnable" and gate_status.startswith("blocked_"):
            failures.append(f"{task_id}: auto_rerunnable item must not be blocked")
        if gate_status in {"done_human_verified_with_receipt", "done_frozen_evidence_verified"}:
            receipt_path = str(item.get("receipt_path", "") or "")
            if not receipt_path:
                failures.append(f"{task_id}: verified-with-receipt item missing receipt_path")
            elif not Path(receipt_path).exists():
                failures.append(f"{task_id}: receipt_path does not exist: {receipt_path}")
        command = item.get("run_command", [])
        if command and not isinstance(command, list):
            failures.append(f"{task_id}: run_command must be a list")
    if failures:
        print("FAIL: data backfill queue problems detected:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(f"PASS: data backfill queue valid ({len(items)} item(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
