"""Unified evidence-delta ledger for incremental research progress.

The delta ledger is deliberately thin: one append-only JSONL file shared by all
work lanes. It records what evidence changed, what remains missing, and what the
next best increment is. It does not approve gates or certify claims.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .work_lane import LANES, normalize_lane

DELTA_LOG = Path("evidence/delta_log.jsonl")
SUFFICIENCY_LEVELS = {
    "insufficient",
    "inventory_started",
    "minimum_viable",
    "expanding",
    "locked_for_current_analysis",
    "reopened",
    "blocked",
}


@dataclass(frozen=True)
class EvidenceDeltaArgs:
    lane: str
    summary: str
    artifacts_added: list[str] = field(default_factory=list)
    artifacts_updated: list[str] = field(default_factory=list)
    coverage_delta: dict[str, Any] = field(default_factory=dict)
    judgment_implications: list[str] = field(default_factory=list)
    remaining_gaps: list[str] = field(default_factory=list)
    next_best_increment: str = ""
    sufficiency: str = "insufficient"
    task_id: str = ""
    run_ref: str = ""
    dry_run: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _existing_records(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / DELTA_LOG
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _lane_prefix(lane: str) -> str:
    return {
        "data": "DATA",
        "literature": "LIT",
        "analysis": "ANALYSIS",
        "claim": "CLAIM",
        "writing": "WRITE",
        "compliance": "COMP",
        "harness": "HARNESS",
    }[lane]


def _next_delta_id(project_root: Path, lane: str) -> str:
    prefix = _lane_prefix(lane)
    max_seen = 0
    for record in _existing_records(project_root):
        raw = str(record.get("delta_id", ""))
        if not raw.startswith(prefix + "-DELTA-"):
            continue
        try:
            max_seen = max(max_seen, int(raw.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"{prefix}-DELTA-{max_seen + 1:03d}"


def build_record(project_root: Path, args: EvidenceDeltaArgs) -> dict[str, Any]:
    lane = normalize_lane(args.lane)
    return {
        "version": 1,
        "policy": "AEROS-EVIDENCE-DELTA-001",
        "delta_id": _next_delta_id(project_root, lane) if lane else "",
        "created_at": _now(),
        "lane": lane,
        "task_id": args.task_id,
        "run_ref": args.run_ref,
        "summary": args.summary.strip(),
        "artifacts_added": list(args.artifacts_added),
        "artifacts_updated": list(args.artifacts_updated),
        "coverage_delta": dict(args.coverage_delta),
        "judgment_implications": list(args.judgment_implications),
        "remaining_gaps": list(args.remaining_gaps),
        "next_best_increment": args.next_best_increment.strip(),
        "sufficiency_for_current_purpose": args.sufficiency.strip(),
    }


def validate_record(record: dict[str, Any], project_root: Path | None = None) -> list[str]:
    delta_id = str(record.get("delta_id", "(missing)"))
    failures: list[str] = []
    lane = normalize_lane(str(record.get("lane", "")))
    if not lane:
        failures.append(f"{delta_id}: lane must be one of {sorted(LANES)}")
    if not str(record.get("summary", "")).strip():
        failures.append(f"{delta_id}: summary is required")
    sufficiency = str(record.get("sufficiency_for_current_purpose", "")).strip()
    if sufficiency not in SUFFICIENCY_LEVELS:
        failures.append(
            f"{delta_id}: invalid sufficiency_for_current_purpose {sufficiency!r}"
        )
    for key in ["artifacts_added", "artifacts_updated", "judgment_implications", "remaining_gaps"]:
        if not isinstance(record.get(key, []), list):
            failures.append(f"{delta_id}: {key} must be a list")
    if not isinstance(record.get("coverage_delta", {}), dict):
        failures.append(f"{delta_id}: coverage_delta must be a mapping")
    artifacts = [
        str(item).strip()
        for item in [
            *(record.get("artifacts_added") or []),
            *(record.get("artifacts_updated") or []),
        ]
        if str(item).strip()
    ]
    if sufficiency not in {"blocked", "insufficient"} and not artifacts:
        failures.append(
            f"{delta_id}: non-blocked/non-insufficient delta requires at least one artifact"
        )
    if not str(record.get("next_best_increment", "")).strip():
        failures.append(f"{delta_id}: next_best_increment is required")
    if project_root is not None:
        for rel in artifacts:
            if rel.startswith(("http://", "https://")):
                continue
            if not (project_root / rel).exists():
                failures.append(f"{delta_id}: referenced artifact does not exist: {rel}")
    return failures


def append_delta(project_root: Path, args: EvidenceDeltaArgs) -> tuple[Path, dict[str, Any], list[str]]:
    record = build_record(project_root, args)
    failures = validate_record(record, project_root)
    path = project_root / DELTA_LOG
    if not args.dry_run and not failures:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path, record, failures


def read_delta_records(project_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = project_root / DELTA_LOG
    if not path.exists():
        return [], []
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    seen: set[str] = set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            failures.append(f"{DELTA_LOG}:{lineno}: invalid JSON ({exc})")
            continue
        if not isinstance(record, dict):
            failures.append(f"{DELTA_LOG}:{lineno}: record must be an object")
            continue
        delta_id = str(record.get("delta_id", "")).strip()
        if delta_id in seen:
            failures.append(f"{DELTA_LOG}:{lineno}: duplicate delta_id {delta_id}")
        seen.add(delta_id)
        failures.extend(validate_record(record, project_root))
        records.append(record)
    return records, failures
