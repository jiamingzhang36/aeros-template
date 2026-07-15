"""Deterministic, pointer-first context budgeting primitives.

This is not a memory store and does not call a model. It compiles a bounded
active brief from canonical project pointers and the latest runtime facts. Raw
tool output stays outside active context unless a caller retrieves the artifact.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MAX_INPUT_TOKENS = 8_000
DEFAULT_COMPACT_RATIO = 0.68
DEFAULT_ACTIVE_BRIEF_TOKENS = 1_000
DEFAULT_RECENT_EVENTS = 5


@dataclass(frozen=True)
class ContextPacket:
    active_brief: str
    recent_events: tuple[dict[str, Any], ...]
    artifact_pointers: tuple[dict[str, str], ...]
    estimated_tokens: int
    max_input_tokens: int
    compacted: bool
    omitted_event_count: int
    does_not_prove: tuple[str, ...] = (
        "semantic completeness of omitted artifacts",
        "scientific validity of the proposed action",
        "provider token or billing savings until a provider consumes this packet",
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def estimate_tokens(value: str) -> int:
    """Return a conservative deterministic estimate, not a tokenizer count."""

    return max(1, (len(value) + 3) // 4)


def pointer_first_result(
    *,
    artifact_path: str,
    summary: str,
    key_facts: Iterable[str] = (),
    changed_state: str = "",
    next_question: str = "",
) -> dict[str, Any]:
    """Represent a result by a summary and retrievable artifact pointer."""

    return {
        "artifact_path": artifact_path,
        "summary": summary[:800],
        "key_facts": [str(item)[:300] for item in key_facts][:8],
        "changed_state": changed_state[:400],
        "next_question": next_question[:400],
        "raw_output_in_context": False,
    }


def _bounded_text(path: Path, *, max_chars: int) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "\n[truncated; retrieve artifact for detail]"


def _recent_episode_events(root: Path, limit: int) -> tuple[list[dict[str, Any]], int]:
    path = root / "events" / "event_log.jsonl"
    if not path.exists():
        return [], 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return [], 0
    parsed: list[dict[str, Any]] = []
    for line in lines:
        try:
            item = json.loads(line)
        except (TypeError, ValueError):
            continue
        payload = item.get("payload", item)
        event_type = str(item.get("event_type", payload.get("event_type", "")))
        if event_type != "episode_step":
            continue
        parsed.append(
            {
                "step": payload.get("step", payload.get("step_index")),
                "action_signature": payload.get("action_signature", ""),
                "state_changed": bool(payload.get("state_changed", False)),
                "research_value_events": list(payload.get("research_value_events", []))[:7],
                "error_code": payload.get("error_code", ""),
                "stop_reason": payload.get("stop_reason", ""),
            }
        )
    omitted = max(0, len(parsed) - limit)
    return parsed[-limit:], omitted


def compile_active_brief(root: Path, action_spec: Any | None = None) -> tuple[str, tuple[dict[str, str], ...]]:
    """Compile an 800-1200-token active brief from canonical project pointers."""

    sources = (
        ("CURRENT_WORK.md", root / "CURRENT_WORK.md"),
        ("CURRENT_STATE.md", root / "CURRENT_STATE.md"),
        ("NEXT_ACTION.md", root / "NEXT_ACTION.md"),
    )
    sections: list[str] = []
    pointers: list[dict[str, str]] = []
    for label, path in sources:
        value = _bounded_text(path, max_chars=1_500)
        if not value:
            continue
        sections.append(f"## {label}\n{value}")
        pointers.append({"path": label, "role": "project_context"})
    if action_spec is not None:
        sections.append(
            "## Proposed action\n"
            f"kind: {getattr(action_spec, 'kind', '')}\n"
            f"lane: {getattr(action_spec, 'lane', '')}\n"
            f"effect_class: {getattr(action_spec, 'effect_class', '')}\n"
            f"stop_condition: {getattr(action_spec, 'stop_condition', '')}"
        )
    if not sections:
        sections.append("## Active context\nNo canonical operating brief is available; retrieve project state before acting.")
    brief = "\n\n".join(sections)
    max_chars = DEFAULT_ACTIVE_BRIEF_TOKENS * 4
    if len(brief) > max_chars:
        brief = brief[:max_chars].rstrip() + "\n[active brief compacted]"
    return brief, tuple(pointers)


def prepare_context_packet(
    root: Path,
    action_spec: Any | None = None,
    *,
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
    compact_ratio: float = DEFAULT_COMPACT_RATIO,
    recent_event_limit: int = DEFAULT_RECENT_EVENTS,
) -> ContextPacket:
    """Build a pointer-first packet and compact before the threshold."""

    brief, pointers = compile_active_brief(root, action_spec)
    events, omitted = _recent_episode_events(root, recent_event_limit)
    compacted = False

    def current_estimate() -> int:
        return estimate_tokens(json.dumps(
            {"active_brief": brief, "recent_events": events, "artifact_pointers": pointers},
            sort_keys=True,
            ensure_ascii=True,
        ))

    threshold = max(1, int(max_input_tokens * compact_ratio))
    estimated = current_estimate()
    while events and estimated > threshold:
        events.pop(0)
        omitted += 1
        compacted = True
        estimated = current_estimate()
    while estimated > threshold and len(brief) > 160:
        excess_ratio = max(0.2, min(0.9, threshold / estimated * 0.85))
        brief = brief[:max(160, int(len(brief) * excess_ratio))].rstrip() + "\n[active brief compacted to budget]"
        compacted = True
        estimated = current_estimate()

    return ContextPacket(
        active_brief=brief,
        recent_events=tuple(events),
        artifact_pointers=pointers,
        estimated_tokens=estimated,
        max_input_tokens=max_input_tokens,
        compacted=compacted,
        omitted_event_count=omitted,
    )
