"""Deterministic anti-loop decisions for bounded AEROS episodes.

The watchdog is not a planner or scientific judge.  It observes stable action,
input, state, artifact, blocker, error, text, token, cost, and timing facts and
returns a typed stop/replan/cache decision.  Records reuse the existing
append-only event log instead of creating another registry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re
import time
from typing import Any

from aeros.kernel.events import Event, append_event, artifact_ref, read_events


SEMANTIC_FILES = (
    "aeros_state.yml",
    "CURRENT_STATE.md",
    "decisions/human_gate_queue.yml",
    "decisions/decision_log.csv",
    "data/data_state.yml",
    "data/data_gap_plan.yml",
    "data/backfill/backfill_queue.yml",
    "discovery/data_inventory.csv",
    "discovery/literature/paper_registry.csv",
    "discovery/literature/search_log.csv",
    "discovery/literature/missing_fulltext_queue.csv",
    "evidence/claim_registry.md",
    "evidence/result_index.csv",
    "evidence/result_registry.csv",
    "evidence/research_graph.yml",
    "paper/draft.md",
    "replication/aea_data_package_manifest.yml",
)

SUBSTANTIVE_ROOTS = (
    "data",
    "discovery/literature/extraction_cards",
    "discovery/literature/synthesis",
    "evidence",
    "outputs/source_snapshots",
    "outputs/tables",
    "outputs/figures",
    "outputs/model_outputs",
    "paper",
    "replication",
)

SUBSTANTIVE_FILES = (
    "decisions/human_gate_queue.yml",
    "decisions/decision_log.csv",
    "aeros_state.yml",
)

BLOCKER_FILES = (
    "decisions/human_gate_queue.yml",
    "data/data_gap_plan.yml",
    "data/backfill/backfill_queue.yml",
    "discovery/literature/missing_fulltext_queue.csv",
    "campaigns/active_campaign.yml",
)


def _hash_file(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def _stable_hash(values: list[str] | tuple[str, ...]) -> str:
    return sha256("\n".join(values).encode("utf-8")).hexdigest()


# Lines whose only role is bookkeeping metadata that is re-stamped on every state
# save (e.g. state.py writes updated_at=_now()). They change without substantive
# progress, so hashing them would defeat the no_state_change stop. Timestamps that
# accompany real progress (a new search_log/registry row) are NOT stripped.
_VOLATILE_LINE_PREFIXES: dict[str, tuple[str, ...]] = {
    "aeros_state.yml": ("updated_at:",),
    "CURRENT_STATE.md": ("last_validation:",),
}


def _semantic_file_hash(rel: str, path: Path) -> str:
    """Content hash of a semantic file, with per-save volatile metadata lines
    stripped so that a step which only re-stamps a timestamp is not mistaken for
    substantive state change."""
    prefixes = _VOLATILE_LINE_PREFIXES.get(rel)
    if not prefixes:
        return _hash_file(path)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    kept = [ln for ln in text.splitlines() if not ln.lstrip().startswith(prefixes)]
    return sha256("\n".join(kept).encode("utf-8")).hexdigest()


def semantic_state_fingerprint(root: Path) -> str:
    """Hash decision-relevant project state while excluding logs/receipts."""
    rows: list[str] = []
    for rel in SEMANTIC_FILES:
        path = root / rel
        if path.is_file():
            rows.append(f"{rel}:{_semantic_file_hash(rel, path)}")
        elif path.exists():
            rows.append(f"{rel}:exists")
    return _stable_hash(rows)


def artifact_state_fingerprint(root: Path) -> str:
    """Hash substantive artifacts, excluding runtime chatter and timestamps."""
    rows: list[str] = []
    for rel in SUBSTANTIVE_FILES:
        path = root / rel
        if path.is_file():
            rows.append(f"{rel}:{_hash_file(path)}")
    for rel in SUBSTANTIVE_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(candidate for candidate in base.rglob("*") if candidate.is_file()):
            if "__pycache__" in path.parts or path.name == ".DS_Store":
                continue
            rows.append(f"{path.relative_to(root).as_posix()}:{_hash_file(path)}")
    return _stable_hash(rows)


def frontier_fingerprint(action: dict[str, Any], spec: dict[str, Any]) -> str:
    return _stable_hash([
        str(action.get("lane", "")),
        str(action.get("status_label", "")),
        str(spec.get("id", "")),
        str(spec.get("kind", "")),
        str(spec.get("effect_class", "")),
        str(spec.get("requires_decision", "")),
        str(action.get("source", "")),
    ])


def action_fingerprint(spec: dict[str, Any]) -> str:
    return _stable_hash([
        str(spec.get("id", "")),
        str(spec.get("kind", "")),
        str(spec.get("effect_class", "")),
        str(spec.get("command", "")),
        str(spec.get("idempotency_key", "")),
    ])


def input_fingerprint(root: Path, spec: dict[str, Any]) -> str:
    rows = [
        json.dumps(spec.get("preconditions") or [], sort_keys=True, default=str),
        str(spec.get("idempotency_key", "")),
    ]
    declared = spec.get("inputs") or spec.get("input_artifacts") or []
    if isinstance(declared, (str, dict)):
        declared = [declared]
    for item in declared if isinstance(declared, list) else []:
        value = str(item.get("path", "")) if isinstance(item, dict) else str(item)
        candidate = root / value
        rows.append(f"{value}:{_hash_file(candidate) if candidate.is_file() else 'missing'}")
    return _stable_hash(rows)


def blocker_fingerprints(root: Path) -> tuple[str, ...]:
    rows = []
    for rel in BLOCKER_FILES:
        path = root / rel
        if path.is_file():
            rows.append(f"{rel}:{_hash_file(path)}")
    return tuple(rows)


def artifact_hashes(root: Path, paths: tuple[str, ...] | list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in paths:
        value = str(rel).strip().lstrip("./")
        candidate = root / value
        if value and candidate.is_file():
            out[value] = _hash_file(candidate)
    return out


def changed_artifacts(root: Path, expected: tuple[str, ...], before: dict[str, str]) -> dict[str, str]:
    after = artifact_hashes(root, expected)
    return {path: digest for path, digest in after.items() if before.get(path) != digest}


def research_value_events_since(root: Path, started_at_epoch: float) -> tuple[dict[str, Any], ...]:
    try:
        from .campaign import infer_research_value_events
        return tuple(infer_research_value_events(root, since_mtime=started_at_epoch))
    except Exception:
        return ()


def tool_result_fingerprint(return_code: int, state_after: str, accepted: dict[str, str]) -> str:
    return _stable_hash([
        str(return_code),
        state_after,
        json.dumps(accepted, sort_keys=True),
    ])


def new_episode_id(root: Path, lane: str) -> str:
    return "EP-" + sha256(f"{root.resolve()}|{lane}|{time.time_ns()}".encode()).hexdigest()[:16]


@dataclass(frozen=True)
class WatchdogPolicy:
    repeated_action_limit: int = 2
    no_state_change_limit: int = 2
    same_error_limit: int = 2
    text_loop_window: int = 3
    text_similarity_threshold: float = 0.90
    max_tokens_without_value: int = 50_000


@dataclass(frozen=True)
class EpisodeStep:
    episode_id: str
    objective_id: str
    frontier_id: str
    step: int
    action_signature: str
    input_fingerprint: str
    state_fingerprint_before: str
    state_fingerprint_after: str
    expected_artifacts: tuple[str, ...] = ()
    accepted_artifacts: tuple[str, ...] = ()
    accepted_artifact_hashes: dict[str, str] = field(default_factory=dict)
    research_value_events: tuple[dict[str, Any], ...] = ()
    blockers_before: tuple[str, ...] = ()
    blockers_after: tuple[str, ...] = ()
    tool_result_hash: str = ""
    error_code: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    wall_time: float = 0.0
    assistant_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WatchdogDecision:
    stop: bool
    reason: str
    disposition: str
    previous_artifacts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stop": self.stop,
            "reason": self.reason,
            "disposition": self.disposition,
            "previous_artifacts": list(self.previous_artifacts),
            "does_not_prove": [
                "scientific validity",
                "optimality of the next research action",
                "claim, gate, submission, or release authority",
            ],
        }


ALLOW = WatchdogDecision(False, "watchdog_clear", "continue")


def _has_value(step: EpisodeStep) -> bool:
    blocker_reduced = bool(set(step.blockers_before) - set(step.blockers_after))
    return bool(step.accepted_artifacts or step.research_value_events or blocker_reduced)


def _artifact_cache_valid(root: Path, step: EpisodeStep) -> bool:
    return bool(step.accepted_artifact_hashes) and all(
        (root / rel).is_file() and _hash_file(root / rel) == digest
        for rel, digest in step.accepted_artifact_hashes.items()
    )


def assess_before(root: Path, history: list[EpisodeStep], draft: EpisodeStep,
                  policy: WatchdogPolicy = WatchdogPolicy()) -> WatchdogDecision:
    matches = [
        item for item in history
        if item.action_signature == draft.action_signature
        and item.input_fingerprint == draft.input_fingerprint
        and draft.state_fingerprint_before in {
            item.state_fingerprint_before,
            item.state_fingerprint_after,
        }
    ]
    for item in reversed(matches):
        if not item.error_code and _artifact_cache_valid(root, item):
            return WatchdogDecision(True, "CACHE_HIT", "reuse_previous_accepted_artifacts", item.accepted_artifacts)
    if len(matches) >= policy.repeated_action_limit:
        return WatchdogDecision(True, "STOP_REPEATED_ACTION", "stop_and_replan")
    return ALLOW


def _normalized_tokens(text: str) -> set[str]:
    normalized = re.sub(r"\b\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+Z-]+)?\b", " ", text.lower())
    normalized = re.sub(r"\b[a-f0-9]{8,64}\b", " ", normalized)
    return set(re.findall(r"[a-z0-9_\u4e00-\u9fff]+", normalized))


def _similarity(left: str, right: str) -> float:
    a, b = _normalized_tokens(left), _normalized_tokens(right)
    if not a and not b:
        return 1.0
    return len(a & b) / max(len(a | b), 1)


def assess_after(history: list[EpisodeStep], current: EpisodeStep,
                 policy: WatchdogPolicy = WatchdogPolicy()) -> WatchdogDecision:
    if current.error_code:
        same_errors = [
            item for item in history
            if item.error_code == current.error_code
            and item.action_signature == current.action_signature
            and item.input_fingerprint == current.input_fingerprint
        ]
        if len(same_errors) + 1 >= policy.same_error_limit:
            return WatchdogDecision(True, "STOP_SAME_ERROR", "change_executor_input_or_escalate")

    recent_text = [item for item in history if item.assistant_text and not _has_value(item)]
    window = [*recent_text[-(policy.text_loop_window - 1):], current]
    if len(window) >= policy.text_loop_window and current.assistant_text and not _has_value(current):
        if all(_similarity(item.assistant_text, current.assistant_text) >= policy.text_similarity_threshold for item in window[:-1]):
            return WatchdogDecision(True, "STOP_TEXT_LOOP", "stop_and_deliver_or_replan")

    no_change = current.state_fingerprint_before == current.state_fingerprint_after and not _has_value(current)
    if no_change:
        stalled = [
            item for item in history
            if item.objective_id == current.objective_id
            and item.frontier_id == current.frontier_id
            and item.state_fingerprint_before == item.state_fingerprint_after
            and not _has_value(item)
        ]
        if len(stalled) + 1 >= policy.no_state_change_limit:
            return WatchdogDecision(True, "STOP_NO_STATE_CHANGE", "stop_and_replan")
        return WatchdogDecision(True, "REPLAN_REQUIRED", "replan_before_any_more_spend")

    trailing: list[EpisodeStep] = []
    for item in reversed(history):
        if _has_value(item):
            break
        trailing.append(item)
    token_spend = sum(item.tokens_input + item.tokens_output for item in trailing) + current.tokens_input + current.tokens_output
    if not _has_value(current) and token_spend >= 2 * policy.max_tokens_without_value:
        return WatchdogDecision(True, "STOP_TOKEN_WASTE", "stop_and_compact_context")
    if not _has_value(current) and token_spend >= policy.max_tokens_without_value:
        return WatchdogDecision(True, "REPLAN_WITH_COMPACT_CONTEXT", "compact_context_then_retry_once")
    return ALLOW


def record_episode_step(root: Path, step: EpisodeStep, decision: WatchdogDecision) -> Path:
    inputs = [artifact_ref(root, path) for path in step.expected_artifacts if (root / path).exists()]
    outputs = [artifact_ref(root, path) for path in step.accepted_artifacts]
    return append_event(root, Event(
        event_type="episode_step",
        action=step.action_signature,
        action_type="episode_watchdog_observation",
        inputs=inputs,
        outputs=outputs,
        evidence=1.0 if _has_value(step) else 0.0,
        metadata={"episode_step": step.to_dict(), "watchdog_decision": decision.to_dict()},
    ))


def load_episode_steps(root: Path) -> list[EpisodeStep]:
    steps: list[EpisodeStep] = []
    for event in read_events(root):
        if event.event_type != "episode_step":
            continue
        raw = event.metadata.get("episode_step") if isinstance(event.metadata, dict) else None
        if not isinstance(raw, dict):
            continue
        try:
            raw = dict(raw)
            for key in ("expected_artifacts", "accepted_artifacts", "research_value_events", "blockers_before", "blockers_after"):
                raw[key] = tuple(raw.get(key) or [])
            raw.setdefault("accepted_artifact_hashes", {})
            steps.append(EpisodeStep(**raw))
        except (TypeError, ValueError):
            continue
    return steps
