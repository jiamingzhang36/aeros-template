"""Append-only event log primitives for AEROS.

Events are factual traces. They do not decide progress. The kernel evaluates
whether an event/artifact set supports a legal state transition. AEROS v0.5 moves
toward event-sourcing: materialized views should be derived from this log.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_LOG = Path("events/event_log.jsonl")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_ref(project_root: Path, path: str | Path) -> dict[str, Any]:
    p = Path(path)
    full = p if p.is_absolute() else project_root / p
    rel = str(p if not p.is_absolute() else full)
    try:
        rel = full.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        rel = str(p)
    if not full.exists() or not full.is_file():
        return {"path": rel, "sha256": "", "bytes": 0, "exists": False}
    return {"path": rel, "sha256": sha256_file(full), "bytes": full.stat().st_size, "exists": True}


@dataclass(frozen=True)
class Event:
    event_type: str
    action: str
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    evidence: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    event_id: str = ""
    parent_event_hash: str = ""
    actor: str = "codex"
    action_type: str = ""
    schema_version: int = 2
    input_hashes: list[str] = field(default_factory=list)
    output_hashes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("event_id", None)
        return payload

    def with_event_id(self) -> "Event":
        input_hashes = self.input_hashes or sorted(
            str(item.get("sha256", "")) for item in self.inputs if item.get("sha256")
        )
        output_hashes = self.output_hashes or sorted(
            str(item.get("sha256", "")) for item in self.outputs if item.get("sha256")
        )
        normalized = Event(
            event_type=self.event_type,
            action=self.action,
            inputs=self.inputs,
            outputs=self.outputs,
            evidence=self.evidence,
            timestamp=self.timestamp,
            event_id="",
            parent_event_hash=self.parent_event_hash,
            actor=self.actor or "unknown",
            action_type=self.action_type or self.action,
            schema_version=self.schema_version,
            input_hashes=input_hashes,
            output_hashes=output_hashes,
            metadata=self.metadata,
        )
        payload = json.dumps(normalized.canonical_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        eid = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return Event(
            event_type=normalized.event_type,
            action=normalized.action,
            inputs=normalized.inputs,
            outputs=normalized.outputs,
            evidence=normalized.evidence,
            timestamp=normalized.timestamp,
            event_id=eid,
            parent_event_hash=normalized.parent_event_hash,
            actor=normalized.actor,
            action_type=normalized.action_type,
            schema_version=normalized.schema_version,
            input_hashes=normalized.input_hashes,
            output_hashes=normalized.output_hashes,
            metadata=normalized.metadata,
        )


def append_event(project_root: Path, event: Event) -> Path:
    path = project_root / EVENT_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = read_events(project_root)
    parent_hash = previous[-1].event_id if previous else ""
    if event.parent_event_hash and event.parent_event_hash != parent_hash:
        raise ValueError("event parent_event_hash does not match current log tip")
    event = Event(
        event_type=event.event_type,
        action=event.action,
        inputs=event.inputs,
        outputs=event.outputs,
        evidence=event.evidence,
        timestamp=event.timestamp,
        event_id="",
        parent_event_hash=parent_hash,
        actor=event.actor,
        action_type=event.action_type or event.action,
        schema_version=event.schema_version,
        input_hashes=event.input_hashes,
        output_hashes=event.output_hashes,
        metadata=event.metadata,
    ).with_event_id()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(event), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def read_events(project_root: Path) -> list[Event]:
    path = project_root / EVENT_LOG
    if not path.exists():
        return []
    out: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        # Backward compatibility for older event rows using string inputs/outputs.
        for key in ("inputs", "outputs"):
            fixed = []
            for item in data.get(key) or []:
                fixed.append(item if isinstance(item, dict) else {"path": str(item), "sha256": "", "bytes": 0, "exists": False})
            data[key] = fixed
        data.setdefault("parent_event_hash", "")
        data.setdefault("actor", "unknown")
        data.setdefault("action_type", data.get("action", ""))
        data.setdefault("schema_version", 1)
        data.setdefault("input_hashes", sorted(str(item.get("sha256", "")) for item in data["inputs"] if item.get("sha256")))
        data.setdefault("output_hashes", sorted(str(item.get("sha256", "")) for item in data["outputs"] if item.get("sha256")))
        out.append(Event(**data))
    return out
