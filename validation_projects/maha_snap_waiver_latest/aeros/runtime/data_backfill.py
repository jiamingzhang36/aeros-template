"""Data-gap backfill orchestration for AEROS.

This layer turns data coverage gaps into a formal queue. It does not invent
evidence: local-cache-safe items can run only with explicit commands; official
source/API/credentialed items become blocked approval checklist entries.
"""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


INVENTORY = Path("discovery/data_inventory.csv")
QUEUE = Path("data/backfill/backfill_queue.yml")
COVERAGE_DELTA = Path("data/backfill/coverage_delta.md")
APPROVAL_CHECKLIST = Path("data/backfill/approval_checklist.md")
REPORT = Path("audits/data_backfill_report.md")


@dataclass(frozen=True)
class BackfillArgs:
    dry_run: bool
    run_local: bool
    approve: str = ""
    receipt: str = ""
    owner: str = ""
    source_snapshot: str = ""
    note: str = ""
    coverage: str = ""
    disagreement_log: str = ""
    human_decision: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_inventory(project_root: Path) -> list[dict[str, str]]:
    path = project_root / INVENTORY
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("data_id") or "").strip()]


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _local_path_exists(project_root: Path, value: str) -> bool:
    if not value:
        return False
    if value.startswith(("http://", "https://")):
        return False
    return (project_root / value).exists() or Path(value).expanduser().exists()


def _classify(row: dict[str, str], project_root: Path) -> tuple[str, str, str]:
    access = _norm(row.get("access_status")).lower()
    engineering = _norm(row.get("engineering_status")).lower()
    link = _norm(row.get("link_or_path"))
    next_probe = _norm(row.get("next_probe"))

    if _local_path_exists(project_root, link) or engineering in {"access_verified", "schema_inspected", "variables_verified", "linkage_tested", "coverage_diagnosed"}:
        return "auto_rerunnable", "pending", "local cache or verified accessible source"
    if access in {"restricted", "paid", "requested"}:
        return "approval_required", "blocked_missing_credentials", "restricted/paid/requested source requires credentials or access approval"
    if access in {"public", "located", "granted"}:
        return "approval_required", "blocked_missing_source_snapshot", "official/public source needs source-date snapshot approval before refresh"
    if next_probe:
        return "receipt_audited", "needs_receipt_audit", "human/source review probe needs receipt"
    return "receipt_audited", "needs_receipt_audit", "insufficient source evidence for automatic backfill"


def _queue_items(rows: list[dict[str, str]], project_root: Path) -> list[dict[str, Any]]:
    if not rows:
        return [{
            "task_id": "DATA-GAP-001",
            "data_id": "",
            "dataset_name": "data inventory missing or empty",
            "gap_type": "inventory_empty",
            "priority": 1,
            "automation_class": "receipt_audited",
            "gate_status": "needs_receipt_audit",
            "receipt_path": "evidence/receipts/DATA-GAP-001_human_review_receipt.md",
            "run_command": [],
            "reason": "no data inventory rows exist",
        }]

    items: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        data_id = _norm(row.get("data_id")) or f"DATA-{index:03d}"
        access = _norm(row.get("access_status")).lower()
        engineering = _norm(row.get("engineering_status")).lower()
        feasibility = _norm(row.get("feasibility_status")).lower()
        needs_work = (
            access in {"", "unknown", "located", "public", "restricted", "paid", "requested"}
            or engineering not in {"execution_ready"}
            or feasibility in {"", "tbd", "revise"}
            or bool(_norm(row.get("next_probe")))
        )
        if not needs_work:
            continue
        automation_class, gate_status, reason = _classify(row, project_root)
        receipt_path = ""
        if automation_class in {"receipt_audited", "frozen_evidence"}:
            receipt_path = f"evidence/receipts/{data_id}_human_review_receipt.md"
        items.append({
            "task_id": f"DATA-BACKFILL-{index:03d}",
            "data_id": data_id,
            "dataset_name": _norm(row.get("dataset_name")),
            "gap_type": "coverage_or_access_gap",
            "priority": index,
            "automation_class": automation_class,
            "gate_status": gate_status,
            "receipt_path": receipt_path,
            "run_command": [],
            "source": _norm(row.get("owner_or_source")),
            "link_or_path": _norm(row.get("link_or_path")),
            "next_probe": _norm(row.get("next_probe")),
            "reason": reason,
        })
    return items


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_markdown(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# " + title + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


def _read_queue(project_root: Path) -> dict[str, Any]:
    path = project_root / QUEUE
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _merge_existing_queue(project_root: Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve human-added queue fields across regenerated coverage audits."""
    existing = _read_queue(project_root)
    old_items = existing.get("items", []) if isinstance(existing, dict) else []
    by_key: dict[str, dict[str, Any]] = {}
    for old in old_items if isinstance(old_items, list) else []:
        if not isinstance(old, dict):
            continue
        for key in (str(old.get("task_id", "")), str(old.get("data_id", ""))):
            if key:
                by_key[key] = old
    preserved_keys = {
        "run_command",
        "approval",
        "receipt",
        "gate_status",
        "automation_class",
        "receipt_path",
        "human_note",
    }
    merged: list[dict[str, Any]] = []
    for item in items:
        old = by_key.get(str(item.get("task_id", ""))) or by_key.get(str(item.get("data_id", ""))) or {}
        out = dict(item)
        for key in preserved_keys:
            if key in old and old.get(key) not in (None, ""):
                out[key] = old[key]
        merged.append(out)
    return merged


def _find_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item_id in {str(item.get("task_id", "")), str(item.get("data_id", ""))}:
            return item
    return None


def _write_receipt(project_root: Path, item: dict[str, Any], args: BackfillArgs) -> Path:
    receipt_path = str(item.get("receipt_path") or f"evidence/receipts/{item.get('task_id')}_human_review_receipt.md")
    path = project_root / receipt_path
    lines = [
        "---",
        "receipt_type: human_review_receipt",
        "status: filled",
        f"reviewed_by: {args.owner}",
        f"reviewed_at: {_now()}",
        f"source_snapshot: {args.source_snapshot}",
        f"coverage: {args.coverage}",
        f"disagreement_log: {args.disagreement_log}",
        f"human_decision: {args.human_decision}",
        "---",
        "",
        "# Human Review Receipt",
        "",
        f"- Queue item: {item.get('task_id')}",
        f"- Data ID: {item.get('data_id')}",
        f"- Note: {args.note}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _approved(item: dict[str, Any]) -> bool:
    approval = item.get("approval")
    return isinstance(approval, dict) and bool(approval.get("approved_by")) and bool(approval.get("source_snapshot"))


def _run_local_items(project_root: Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in items:
        command = item.get("run_command") or []
        can_run = item.get("automation_class") == "auto_rerunnable" or (
            item.get("automation_class") == "approval_required" and _approved(item)
        )
        if not can_run or not command:
            continue
        proc = subprocess.run(command, cwd=project_root, text=True, capture_output=True, timeout=900)
        results.append({
            "task_id": item.get("task_id"),
            "command": command,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-2000:],
        })
    return results


def run_data_backfill(project_root: Path, args: BackfillArgs) -> int:
    rows = _read_inventory(project_root)
    items = _merge_existing_queue(project_root, _queue_items(rows, project_root))

    if args.approve or args.receipt:
        queue = _read_queue(project_root)
        items = queue.get("items", []) if isinstance(queue.get("items"), list) else items
        item_id = args.approve or args.receipt
        item = _find_item(items, item_id)
        if not item:
            print(f"FAIL: queue item not found: {item_id}")
            return 1
        if args.approve:
            if not args.owner or not args.source_snapshot:
                print("FAIL: approve requires --owner and --source-snapshot")
                return 1
            item["approval"] = {
                "approved_by": args.owner,
                "approved_at": _now(),
                "source_snapshot": args.source_snapshot,
                "note": args.note,
            }
            if str(item.get("gate_status", "")).startswith("blocked_"):
                item["gate_status"] = "pending"
            print(f"[data-backfill] approved queue item {item_id}; run only if an explicit run_command is present")
        if args.receipt:
            if not args.owner or not args.source_snapshot or not args.human_decision:
                print("FAIL: receipt requires --owner, --source-snapshot, and --human-decision")
                return 1
            path = _write_receipt(project_root, item, args)
            item["receipt"] = {"path": str(path.relative_to(project_root)), "written_at": _now()}
            item["receipt_path"] = str(path.relative_to(project_root))
            item["gate_status"] = "done_human_verified_with_receipt"
            print(f"[data-backfill] wrote receipt for {item_id}: {path.relative_to(project_root)}")
        payload = {
            "generated_at": str(queue.get("generated_at") or _now()) if isinstance(queue, dict) else _now(),
            "updated_at": _now(),
            "policy": "AEROS-DATA-AUTO-001",
            "items": items,
        }
        _write_yaml(project_root / QUEUE, payload)
        return 0

    runnable = [item for item in items if item["automation_class"] == "auto_rerunnable"]
    blocked = [item for item in items if str(item["gate_status"]).startswith("blocked_")]
    receipt = [item for item in items if item["gate_status"] == "needs_receipt_audit"]
    approved = [item for item in items if item["automation_class"] == "approval_required" and _approved(item)]

    print(f"[data-backfill] inventory rows: {len(rows)}")
    print(f"[data-backfill] queue items: {len(items)}")
    print(f"[data-backfill] runnable/local-cache: {len(runnable)}")
    print(f"[data-backfill] approved source-limited runnable: {len(approved)}")
    print(f"[data-backfill] receipt-audit: {len(receipt)}")
    print(f"[data-backfill] blocked approval/source-limited: {len(blocked)}")
    if args.dry_run:
        print("[data-backfill] dry-run: no files written and no commands run")
        for item in items:
            print(f"  - {item['task_id']} {item['automation_class']}/{item['gate_status']}: {item['reason']}")
        return 0

    payload = {
        "generated_at": _now(),
        "policy": "AEROS-DATA-AUTO-001",
        "items": items,
    }
    _write_yaml(project_root / QUEUE, payload)
    _write_markdown(project_root / COVERAGE_DELTA, "Coverage Delta", [
        f"- Generated at: {_now()}",
        f"- Inventory rows: {len(rows)}",
        f"- Queue items: {len(items)}",
        f"- Runnable/local-cache items: {len(runnable)}",
        f"- Approved source-limited runnable items: {len(approved)}",
        f"- Receipt-audit items: {len(receipt)}",
        f"- Blocked approval/source-limited items: {len(blocked)}",
        "",
        "## Skipped-Spec / Claim Boundary Impact",
        "",
        "No claim boundary is updated by data backfill orchestration alone. Claims must be reviewed through the claim registry and gate checks after backfill.",
    ])
    _write_markdown(project_root / APPROVAL_CHECKLIST, "Data Backfill Approval Checklist", [
        "Use this checklist before running official-source, API, credentialed, scraping, or source-date-sensitive backfills.",
        "",
        "## Blocked Items",
        "",
        *[
            f"- {item['task_id']} / {item.get('data_id')}: {item['gate_status']} - {item['reason']}"
            for item in blocked
        ],
        "",
        "## Required Approval Fields",
        "",
        "- approved_by:",
        "- approved_at:",
        "- source_snapshot_date:",
        "- credentials_or_terms_review:",
        "- explicit_run_command:",
        "- allowed_outputs:",
        "- rollback_plan:",
    ])
    results = _run_local_items(project_root, items) if args.run_local else []
    _write_markdown(project_root / REPORT, "Data Backfill Report", [
        f"- Policy: AEROS-DATA-AUTO-001",
        f"- Queue: {QUEUE}",
        f"- Local commands run: {len(results)}",
        "",
        "## Local Run Results",
        "",
        *[
            f"- {result['task_id']}: returncode={result['returncode']} command={result['command']}"
            for result in results
        ],
    ])
    print(f"[data-backfill] wrote {QUEUE}")
    print(f"[data-backfill] wrote {COVERAGE_DELTA}")
    print(f"[data-backfill] wrote {APPROVAL_CHECKLIST}")
    print(f"[data-backfill] wrote {REPORT}")
    if args.run_local:
        failures = [result for result in results if result["returncode"] != 0]
        if failures:
            print(f"[data-backfill] local command failures: {len(failures)}")
            return 1
    return 0
