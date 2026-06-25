"""Derived global state graph for AEROS.

The global state is a derived index, not a new truth source. It summarizes
local state across data inventory, probes, backfill queue, provenance, results,
evidence, claims, and action receipts so checks can reason about cross-layer
constraints.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

GLOBAL_STATE = Path("aeros/state/global_state.yml")
DATA_INVENTORY = Path("discovery/data_inventory.csv")
PROBE_ROOT = Path("data/probes")
BACKFILL_QUEUE = Path("data/backfill/backfill_queue.yml")
CLAIM_REGISTRY = Path("evidence/claim_registry.md")
EVIDENCE_LEDGER = Path("evidence/evidence_ledger.csv")
RESULT_INDEX = Path("evidence/result_index.csv")
PROVENANCE_DIR = Path("outputs/.provenance")
ACTION_RECEIPTS = Path("agent_runs/action_receipts")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle)]


def _claim_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()]
    table = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table) < 2:
        return []
    headers = [h.strip() for h in table[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        row = dict(zip(headers, cells))
        if any(row.values()):
            rows.append(row)
    return rows


def _probe_by_dataset(project_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted((project_root / PROBE_ROOT).glob("*/probe_metadata.yml")):
        data = _load_yaml(path)
        if not isinstance(data, dict):
            continue
        data_id = str(data.get("data_id") or path.parent.name).strip()
        out[data_id] = {
            "status": str(data.get("probe_verdict") or "unknown"),
            "metadata_path": _rel(project_root, path),
            "sample_path": str(data.get("sample_path") or ""),
            "sample_rows": int(data.get("sample_rows") or 0),
            "failure_types": list(data.get("failure_types") or []),
            "scorecard": data.get("scorecard") or {},
        }
    return out


def _queue_by_dataset(project_root: Path) -> dict[str, dict[str, Any]]:
    queue = _load_yaml(project_root / BACKFILL_QUEUE)
    items = queue.get("items", []) if isinstance(queue, dict) else []
    out: dict[str, dict[str, Any]] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        data_id = str(item.get("data_id") or item.get("task_id") or "").strip()
        if not data_id:
            continue
        out[data_id] = {
            "status": str(item.get("gate_status") or "unknown"),
            "automation_class": str(item.get("automation_class") or ""),
            "task_id": str(item.get("task_id") or ""),
            "receipt_path": str(item.get("receipt_path") or ""),
        }
    return out


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _read_action_summary(project_root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted((project_root / ACTION_RECEIPTS).glob("*.yml")):
        data = _load_yaml(path)
        if not isinstance(data, dict):
            continue
        out.append({
            "path": _rel(project_root, path),
            "action_id": data.get("action_id", ""),
            "action_mode": data.get("action_mode", ""),
            "honest_progress_label": data.get("honest_progress_label", ""),
            "dependency_type": (data.get("causal_attribution") or {}).get("dependency_type", ""),
        })
    return out


def build_global_state(project_root: Path) -> dict[str, Any]:
    inventory = [row for row in _read_csv(project_root / DATA_INVENTORY) if str(row.get("data_id", "")).strip()]
    probes = _probe_by_dataset(project_root)
    queue = _queue_by_dataset(project_root)
    datasets: dict[str, Any] = {}
    for row in inventory:
        data_id = str(row.get("data_id", "")).strip()
        probe = probes.get(data_id, {})
        backfill = queue.get(data_id, {})
        probe_status = str(probe.get("status") or "unknown")
        backfill_status = str(backfill.get("status") or "unknown")
        schema_status = "valid" if probe.get("scorecard", {}).get("schema_validity") else "unknown"
        linkage_status = "resolved" if probe.get("scorecard", {}).get("linkage_feasibility") else "unknown"
        datasets[data_id] = {
            "dataset_name": row.get("dataset_name", ""),
            "status": {
                "probe": probe_status,
                "backfill": backfill_status,
                "schema": schema_status,
                "linkage": linkage_status,
                "access": row.get("access_status", ""),
                "engineering": row.get("engineering_status", ""),
            },
            "evidence_links": [p for p in [probe.get("metadata_path"), probe.get("sample_path"), backfill.get("receipt_path")] if p],
            "confidence": {
                "collection_feasibility": 0.8 if probe_status == "passed" else 0.2 if probe_status == "failed" else 0.0,
                "research_readiness": 0.6 if probe_status == "passed" and backfill_status in {"done_auto_verified", "done_human_verified_with_receipt", "pending"} else 0.0,
            },
            "failure_types": list(probe.get("failure_types") or []),
        }
    claim_rows = _claim_rows(project_root / CLAIM_REGISTRY)
    result_rows = _read_csv(project_root / RESULT_INDEX)
    evidence_rows = _read_csv(project_root / EVIDENCE_LEDGER)
    provenance_records = sorted(_rel(project_root, p) for p in (project_root / PROVENANCE_DIR).glob("*.json")) if (project_root / PROVENANCE_DIR).exists() else []
    return {
        "version": 1,
        "policy": "AEROS-GLOBAL-STATE-001",
        "generated_at": _now(),
        "derived_from": {
            "data_inventory": str(DATA_INVENTORY),
            "probe_root": str(PROBE_ROOT),
            "backfill_queue": str(BACKFILL_QUEUE),
            "claim_registry": str(CLAIM_REGISTRY),
            "evidence_ledger": str(EVIDENCE_LEDGER),
            "result_index": str(RESULT_INDEX),
            "provenance_dir": str(PROVENANCE_DIR),
            "action_receipts": str(ACTION_RECEIPTS),
        },
        "datasets": datasets,
        "claims": {"count": len(claim_rows)},
        "evidence": {"rows": len(evidence_rows)},
        "results": {"rows": len(result_rows)},
        "provenance": {"records": len(provenance_records)},
        "actions": _read_action_summary(project_root),
        "invariants": {
            "probe_evidence_cannot_directly_support_claim": True,
            "action_receipts_are_progress_metadata_not_evidence": True,
            "global_state_is_derived_not_authoritative": True,
        },
    }


def write_global_state(project_root: Path, dry_run: bool = False) -> tuple[Path, dict[str, Any]]:
    payload = build_global_state(project_root)
    path = project_root / GLOBAL_STATE
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path, payload


def validate_global_state(project_root: Path) -> list[str]:
    path = project_root / GLOBAL_STATE
    if not path.exists():
        return []
    data = _load_yaml(path)
    if not isinstance(data, dict):
        return [f"{GLOBAL_STATE}: must be a mapping"]
    failures: list[str] = []
    if data.get("policy") != "AEROS-GLOBAL-STATE-001":
        failures.append(f"{GLOBAL_STATE}: missing policy AEROS-GLOBAL-STATE-001")
    inv = data.get("invariants") or {}
    for key in ["probe_evidence_cannot_directly_support_claim", "action_receipts_are_progress_metadata_not_evidence", "global_state_is_derived_not_authoritative"]:
        if not bool(inv.get(key)):
            failures.append(f"{GLOBAL_STATE}: invariant {key} must be true")
    datasets = data.get("datasets") or {}
    if not isinstance(datasets, dict):
        failures.append(f"{GLOBAL_STATE}: datasets must be a mapping")
        return failures
    for data_id, row in datasets.items():
        status = row.get("status") if isinstance(row, dict) else {}
        if not isinstance(status, dict):
            failures.append(f"{data_id}: status must be a mapping")
            continue
        for key in ["probe", "backfill", "schema", "linkage"]:
            if key not in status:
                failures.append(f"{data_id}: status missing {key}")
        conf = row.get("confidence") if isinstance(row, dict) else {}
        if not isinstance(conf, dict):
            failures.append(f"{data_id}: confidence must be a mapping")
        else:
            for key in ["collection_feasibility", "research_readiness"]:
                try:
                    value = float(conf.get(key, 0.0))
                except (TypeError, ValueError):
                    failures.append(f"{data_id}: confidence.{key} must be numeric")
                    continue
                if value < 0.0 or value > 1.0:
                    failures.append(f"{data_id}: confidence.{key} must be between 0 and 1")
    return failures
