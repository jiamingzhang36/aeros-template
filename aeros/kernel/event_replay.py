"""Deterministic replay and event-derived audit helpers."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .events import Event, read_events


@dataclass(frozen=True)
class ReplayState:
    event_count: int
    digest: str
    facts: dict[str, Any] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)


def _update_fact(facts: dict[str, Any], event: Event) -> None:
    facts.setdefault("event_types", {})[event.event_type] = facts.setdefault("event_types", {}).get(event.event_type, 0) + 1
    facts.setdefault("actions", {})[event.action] = facts.setdefault("actions", {}).get(event.action, 0) + 1
    for output in event.outputs:
        path = str(output.get("path", ""))
        if path:
            facts.setdefault("artifacts", {})[path] = {
                "sha256": output.get("sha256", ""),
                "bytes": output.get("bytes", 0),
                "last_event_id": event.event_id,
                "event_type": event.event_type,
                "action": event.action,
            }


def replay(project_root: Path) -> ReplayState:
    events = read_events(project_root)
    facts: dict[str, Any] = {"event_types": {}, "actions": {}, "artifacts": {}}
    violations: list[str] = []
    h = hashlib.sha256()
    seen_ids: set[str] = set()
    for event in events:
        payload = json.dumps(event.canonical_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if event.event_id and event.event_id != expected:
            violations.append(f"event_id mismatch for {event.event_type}/{event.action} at {event.timestamp}")
        if event.event_id and event.event_id in seen_ids:
            violations.append(f"duplicate event_id: {event.event_id}")
        if event.event_id:
            seen_ids.add(event.event_id)
        h.update(json.dumps(event.canonical_payload(), ensure_ascii=False, sort_keys=True).encode("utf-8"))
        _update_fact(facts, event)
    return ReplayState(event_count=len(events), digest=h.hexdigest(), facts=facts, violations=violations)


def check_happens_before(project_root: Path) -> list[str]:
    """Require preanalysis plan commit before outcome-data access/spec execution."""
    events = read_events(project_root)
    failures: list[str] = []
    preanalysis_index: int | None = None
    outcome_events = {"access_outcome", "run_spec", "register_result"}
    for idx, event in enumerate(events):
        if event.event_type == "preanalysis_plan_committed":
            preanalysis_index = idx if preanalysis_index is None else preanalysis_index
        if event.event_type in outcome_events and preanalysis_index is None:
            failures.append(f"{event.event_type} at {event.timestamp} occurred before preanalysis_plan_committed")
    return failures
