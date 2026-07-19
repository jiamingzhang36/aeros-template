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
    previous_hash = ""
    for idx, event in enumerate(events):
        payload = json.dumps(event.canonical_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if not event.event_id:
            violations.append(f"missing event_id at row {idx + 1}")
        elif event.event_id != expected:
            violations.append(f"event_id mismatch for {event.event_type}/{event.action} at {event.timestamp}")
        if event.event_id and event.event_id in seen_ids:
            violations.append(f"duplicate event_id: {event.event_id}")
        if event.parent_event_hash != previous_hash:
            violations.append(
                f"hash-chain mismatch at row {idx + 1}: parent={event.parent_event_hash or '<root>'} expected={previous_hash or '<root>'}"
            )
        if event.schema_version >= 2:
            if not event.actor:
                violations.append(f"{event.event_id}: missing actor")
            if not event.action_type:
                violations.append(f"{event.event_id}: missing action_type")
        if event.event_id:
            seen_ids.add(event.event_id)
            previous_hash = event.event_id
        h.update(json.dumps(event.canonical_payload(), ensure_ascii=False, sort_keys=True).encode("utf-8"))
        _update_fact(facts, event)
    return ReplayState(event_count=len(events), digest=h.hexdigest(), facts=facts, violations=violations)


RETROSPECTIVE_PLAN_STATUSES = {
    "retrospective_not_preregistered",
    "retrospective",
}


def preanalysis_plan_status(project_root: Path) -> tuple[str, str]:
    """Return (status, plan_id) declared by analysis/preanalysis_plan.yml.

    Returns ("", "") when no plan file exists or it cannot be parsed.
    """
    plan_path = project_root / "analysis" / "preanalysis_plan.yml"
    if not plan_path.exists():
        return "", ""
    status = plan_id = ""
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("status:") and not status:
            status = stripped.split(":", 1)[1].strip().strip("'\"")
        elif stripped.startswith("plan_id:") and not plan_id:
            plan_id = stripped.split(":", 1)[1].strip().strip("'\"")
        if status and plan_id:
            break
    return status, plan_id


def check_happens_before(project_root: Path) -> list[str]:
    """Require preanalysis plan commit before outcome-data access/spec execution.

    A project whose plan declares itself retrospective is not held to this
    ordering: there is no preregistration for the analysis to precede. That is
    a disclosure, not an exemption -- the caller is expected to surface the
    declared status so a reader can see the analysis was documented after the
    fact. Only an absent or silent plan produces ordering failures, because
    then the ordering is genuinely unverified.
    """
    events = read_events(project_root)
    status, _ = preanalysis_plan_status(project_root)
    if status in RETROSPECTIVE_PLAN_STATUSES:
        return []
    failures: list[str] = []
    preanalysis_index: int | None = None
    outcome_events = {"access_outcome", "run_spec", "register_result"}
    for idx, event in enumerate(events):
        if event.event_type == "preanalysis_plan_committed":
            preanalysis_index = idx if preanalysis_index is None else preanalysis_index
        if event.event_type in outcome_events and preanalysis_index is None:
            failures.append(f"{event.event_type} at {event.timestamp} occurred before preanalysis_plan_committed")
    return failures
