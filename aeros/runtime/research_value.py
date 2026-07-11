"""Small, economics-oriented vocabulary for decision-relevant progress."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

RESEARCH_VALUE_EVENT_TYPES = {
    "resolved_data_gap",
    "probe_passed",
    "route_decision_changed",
    "claim_bearing_citation_grounded",
    "diagnostic_obligation_closed",
    "paper_exhibit_reproduced",
    "replication_blocker_resolved",
}


def validate_events(root: Path, raw: Any, allowed_outputs: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    events = raw if isinstance(raw, list) else []
    normalized: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, item in enumerate(events):
        if not isinstance(item, dict):
            failures.append(f"research_value_events[{index}] must be a mapping")
            continue
        event_type = str(item.get("event_type") or "").strip()
        subject_id = str(item.get("subject_id") or "").strip()
        before = str(item.get("before_status") or "").strip()
        after = str(item.get("after_status") or "").strip()
        evidence = [str(x).strip() for x in item.get("evidence_paths") or [] if str(x).strip()]
        if event_type not in RESEARCH_VALUE_EVENT_TYPES:
            failures.append(f"research_value_events[{index}] has unsupported event_type {event_type!r}")
        if not subject_id or not before or not after or before == after:
            failures.append(f"research_value_events[{index}] requires subject_id and a real before_status -> after_status transition")
        if not evidence:
            failures.append(f"research_value_events[{index}] requires evidence_paths")
        for rel in evidence:
            if not (root / rel).exists():
                failures.append(f"research value evidence does not exist: {rel}")
            if not any(rel == out or rel.startswith(out.rstrip('/') + '/') for out in allowed_outputs):
                failures.append(f"research value evidence is outside allowed_outputs: {rel}")
        normalized.append({
            "event_type": event_type,
            "subject_id": subject_id,
            "before_status": before,
            "after_status": after,
            "evidence_paths": evidence,
            "verification_check": str(item.get("verification_check") or "").strip(),
        })
    return normalized, failures


def encode_events(events: list[dict[str, Any]]) -> str:
    return json.dumps(events, sort_keys=True, separators=(",", ":")) if events else "[]"


def decode_events(raw: str) -> tuple[dict[str, Any], ...]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return ()
    return tuple(item for item in data if isinstance(item, dict)) if isinstance(data, list) else ()

