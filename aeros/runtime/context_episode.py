"""Scoped context episodes for auditable AEROS agent turns.

An episode records the compact context actually consumed before AEROS emits
project-level guidance. It stores neither raw chat transcripts nor raw tool
output. Closing an episode separates an agent's declared work summary from the
limited workspace and artifact changes AEROS could observe.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

from .context_bundle import build_context_bundle


EPISODE_VERSION = 1
EPISODE_ROOT = Path("outputs/context/episodes")
PACKAGE_EPISODE_ROOT = Path(".aeros/context/episodes")
PACKAGE_CONTEXT_MARKER = Path(".aeros/context/.aeros-managed.json")
MAX_ARTIFACT_HASH_BYTES = 16 * 1024 * 1024
DOES_NOT_PROVE = [
    "that a declared work summary is independently verified",
    "that observed workspace changes are exclusively attributable in a shared worktree",
    "that a task, claim, gate, or release is complete or approved",
    "that an artifact is scientifically valid or supports a claim",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str, *, fallback: str = "default") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return cleaned.strip("._") or fallback


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(raw)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _episode_root(root: Path) -> Path:
    """Keep package-mode session state detachable and project-local.

    Vendored AEROS projects retain the established ``outputs/context`` path.
    Generic projects attached to the installed package write ephemeral episode
    records below ``.aeros`` instead, with a marker that lets ``detach`` remove
    only AEROS-owned state.
    """
    if not (root / ".aeros/attachment.yml").is_file():
        return EPISODE_ROOT
    marker = root / PACKAGE_CONTEXT_MARKER
    if not marker.exists():
        _write_json(
            marker,
            {
                "schema_version": 1,
                "managed_by": "aeros_context_episode",
                "does_not_prove": "that the surrounding project is scientifically valid or ready for any research gate",
            },
        )
    return PACKAGE_EPISODE_ROOT


def _episode_dir(root: Path, episode_id: str) -> Path:
    safe = _slug(episode_id, fallback="")
    if not safe or safe != episode_id:
        raise ValueError("invalid context episode id")
    return root / _episode_root(root) / safe


def _active_path(root: Path, conversation_id: str) -> Path:
    return root / _episode_root(root) / "active" / f"{_slug(conversation_id)}.json"


def _safe_relative(root: Path, raw: str) -> str:
    value = Path(str(raw or "").strip())
    if not str(value):
        raise ValueError("artifact path is empty")
    candidate = value.resolve() if value.is_absolute() else (root / value).resolve()
    try:
        return candidate.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"artifact path escapes project root: {raw}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_state(root: Path, raw: str) -> dict[str, Any]:
    relative = _safe_relative(root, raw)
    path = root / relative
    if not path.exists() or not path.is_file():
        return {"path": relative, "exists": False, "hash_status": "missing"}
    stat = path.stat()
    record: dict[str, Any] = {
        "path": relative,
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if stat.st_size <= MAX_ARTIFACT_HASH_BYTES:
        record.update({"sha256": _sha256(path), "hash_status": "computed"})
    else:
        record.update({"sha256": "", "hash_status": "omitted_large_file"})
    return record


def _workspace_snapshot(root: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "reason": str(exc), "entries": {}}
    if completed.returncode != 0:
        return {"available": False, "reason": (completed.stderr or completed.stdout).strip(), "entries": {}}
    entries: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.rsplit(" -> ", 1)[-1].strip()
        if raw:
            entries[raw] = line[:2]
    return {"available": True, "entries": entries}


def _workspace_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    if not before.get("available") or not after.get("available"):
        return {
            "status": "unavailable",
            "reason": "git workspace status was unavailable at open or close",
            "paths": [],
            "does_not_prove": "No project-wide file delta could be observed.",
        }
    previous = before.get("entries") or {}
    current = after.get("entries") or {}
    changed = [
        {"path": path, "status_before": previous.get(path, ""), "status_after": current.get(path, "")}
        for path in sorted(set(previous) | set(current))
        if previous.get(path, "") != current.get(path, "")
    ]
    limit = 100
    return {
        "status": "observed",
        "path_count": len(changed),
        "paths": changed[:limit],
        "truncated": len(changed) > limit,
        "attribution": "workspace_observed_not_exclusive",
        "does_not_prove": "Parallel agents or pre-existing worktree activity can produce the same delta.",
    }


def _context_projection(bundle: dict[str, Any], *, lane: str, goal: str) -> dict[str, Any]:
    next_action = bundle.get("next_action") if isinstance(bundle.get("next_action"), dict) else {}
    return {
        "lane": lane,
        "goal": str(goal or bundle.get("current_goal") or "").strip(),
        "current_goal": str(bundle.get("current_goal") or "").strip(),
        "current_blocker": str(bundle.get("current_blocker") or "").strip(),
        "latest_substantive_artifact": str(bundle.get("latest_substantive_artifact") or "").strip(),
        "next_action": {
            "recommended_next_action": str(next_action.get("recommended_next_action") or "").strip(),
            "command": str(next_action.get("command") or "").strip(),
            "status_label": str(next_action.get("status_label") or "").strip(),
            "stop_condition": str(next_action.get("stop_condition") or "").strip(),
        },
        "source_hashes": dict(bundle.get("source_hashes") or {}),
        "does_not_prove": bundle.get("does_not_prove") or "",
    }


def _basis(record: dict[str, Any], *, status: str, reused: bool) -> dict[str, Any]:
    projection = record.get("context_projection") or {}
    return {
        "episode_id": record.get("episode_id", ""),
        "conversation_id": record.get("conversation_id", ""),
        "context_hash": record.get("context_hash", ""),
        "lane": projection.get("lane", "project"),
        "status": status,
        "reused": reused,
        "opened_at": record.get("opened_at", ""),
        "source_hashes": projection.get("source_hashes") or {},
        "does_not_prove": DOES_NOT_PROVE,
    }


def _load_opened(root: Path, episode_id: str) -> dict[str, Any]:
    return _read_json(_episode_dir(root, episode_id) / "opened.json")


def open_context_episode(
    root: Path | str,
    *,
    lane: str = "project",
    goal: str = "",
    entrypoint: str = "context",
    conversation_id: str = "",
    tracked_artifacts: list[str] | tuple[str, ...] = (),
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Open or reuse a fresh scoped context record.

    ``bundle`` is injectable for deterministic fixtures. Production callers
    leave it unset so the current source-anchored bundle is rebuilt first.
    """

    project_root = Path(root).resolve()
    requested_lane = str(lane or "project").strip() or "project"
    current_bundle = bundle or build_context_bundle(project_root, lane=requested_lane, brief=True)
    effective_lane = str(current_bundle.get("lane") or requested_lane).strip() or "project"
    projection = _context_projection(current_bundle, lane=effective_lane, goal=goal)
    context_hash = _json_hash(projection)
    resolved_conversation_id = str(conversation_id or os.environ.get("AEROS_CONVERSATION_ID", ""))
    conversation_key = _slug(resolved_conversation_id)
    active_path = _active_path(project_root, conversation_key)
    active = _read_json(active_path)
    active_id = str(active.get("episode_id") or "")
    if active.get("state") == "open" and active_id:
        opened = _load_opened(project_root, active_id)
        if opened and opened.get("context_hash") == context_hash and opened.get("context_projection", {}).get("lane") == effective_lane:
            return {"status": "REUSED", "context_basis": _basis(opened, status="fresh", reused=True), "episode": opened}
        if opened:
            try:
                _write_json(
                    _episode_dir(project_root, active_id) / "superseded.json",
                    {
                        "episode_id": active_id,
                        "superseded_at": _now(),
                        "reason": "A newer scoped context replaced this open episode before it was explicitly closed.",
                        "does_not_prove": "No work summary or completion conclusion was inferred for the superseded episode.",
                    },
                )
            except OSError:
                # Historical episode directories can be read-only after a
                # migration or external restore. They are advisory history;
                # inability to annotate one must not suppress fresh advice.
                pass

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    episode_id = f"CTX-{timestamp}-{conversation_key[:24]}-{context_hash[:12]}"
    directory = _episode_dir(project_root, episode_id)
    tracked: dict[str, dict[str, Any]] = {}
    for raw in tracked_artifacts:
        record = _artifact_state(project_root, raw)
        tracked[str(record["path"])] = record
    opened = {
        "version": EPISODE_VERSION,
        "episode_id": episode_id,
        "conversation_id": resolved_conversation_id,
        "conversation_key": conversation_key,
        "opened_at": _now(),
        "entrypoint": str(entrypoint or "context"),
        "context_hash": context_hash,
        "context_projection": projection,
        "workspace_snapshot": _workspace_snapshot(project_root),
        "tracked_artifacts": tracked,
        "does_not_prove": DOES_NOT_PROVE,
    }
    _write_json(directory / "opened.json", opened)
    _write_json(active_path, {"episode_id": episode_id, "state": "open", "updated_at": _now()})
    return {"status": "OPENED", "context_basis": _basis(opened, status="fresh", reused=False), "episode": opened}


def ensure_advice_context(
    root: Path | str,
    *,
    lane: str = "project",
    goal: str = "",
    entrypoint: str,
    conversation_id: str = "",
) -> dict[str, Any]:
    """Record a fresh context basis before exposing project-level advice."""
    project_root = Path(root).resolve()
    try:
        return open_context_episode(
            project_root,
            lane=lane,
            goal=goal,
            entrypoint=entrypoint,
            conversation_id=conversation_id,
        )["context_basis"]
    except OSError as exc:
        # Context is still compiled and used when a restored/read-only runtime
        # directory prevents persistence.  Advice must expose the degradation,
        # never silently claim that an episode was recorded, and must not fail
        # before surfacing the project risk the user asked to see.
        bundle = build_context_bundle(project_root, lane=lane or "project", brief=True)
        projection = _context_projection(bundle, lane=str(bundle.get("lane") or lane or "project"), goal=goal)
        return {
            "episode_id": "",
            "conversation_id": str(conversation_id or os.environ.get("AEROS_CONVERSATION_ID", "")),
            "context_hash": _json_hash(projection),
            "lane": projection.get("lane", "project"),
            "status": "EPHEMERAL_UNPERSISTED",
            "reused": False,
            "opened_at": "",
            "source_hashes": projection.get("source_hashes") or {},
            "persistence_warning": f"context episode was not persisted: {exc}",
            "does_not_prove": [
                *DOES_NOT_PROVE,
                "that a durable context episode exists for this advice",
            ],
        }


def close_context_episode(
    root: Path | str,
    *,
    episode_id: str = "",
    conversation_id: str = "",
    summary: str,
    work_items: list[str] | tuple[str, ...] = (),
    artifact_paths: list[str] | tuple[str, ...] = (),
    receipt_paths: list[str] | tuple[str, ...] = (),
    blockers: list[str] | tuple[str, ...] = (),
    next_action: str = "",
    outcome: str = "",
) -> dict[str, Any]:
    """Close an episode with declared work and bounded observed changes."""

    project_root = Path(root).resolve()
    if not str(summary or "").strip():
        raise ValueError("closing a context episode requires a concise work summary")
    resolved_conversation_id = str(conversation_id or os.environ.get("AEROS_CONVERSATION_ID", ""))
    conversation_key = _slug(resolved_conversation_id)
    active_path = _active_path(project_root, conversation_key)
    active = _read_json(active_path)
    resolved_id = str(episode_id or active.get("episode_id") or "")
    if not resolved_id:
        raise ValueError("no context episode is available to close")
    opened = _load_opened(project_root, resolved_id)
    if not opened:
        raise ValueError(f"context episode is missing or unreadable: {resolved_id}")
    directory = _episode_dir(project_root, resolved_id)
    if (directory / "closed.json").exists():
        raise ValueError(f"context episode is already closed: {resolved_id}")

    tracked = opened.get("tracked_artifacts") if isinstance(opened.get("tracked_artifacts"), dict) else {}
    requested = list(tracked) + [str(item) for item in artifact_paths]
    artifacts: dict[str, dict[str, Any]] = {}
    for raw in requested:
        after = _artifact_state(project_root, raw)
        before = tracked.get(after["path"])
        if isinstance(before, dict):
            if before.get("sha256") and after.get("sha256"):
                changed: bool | str = before.get("sha256") != after.get("sha256")
            else:
                changed = (
                    before.get("exists") != after.get("exists")
                    or before.get("size_bytes") != after.get("size_bytes")
                    or before.get("mtime_ns") != after.get("mtime_ns")
                )
        else:
            changed = "not_tracked_at_open"
        artifacts[str(after["path"])] = {"before": before or {}, "after": after, "changed_since_open": changed}

    linked_receipts: list[dict[str, Any]] = []
    for raw in receipt_paths:
        relative = _safe_relative(project_root, raw)
        linked_receipts.append({"path": relative, "exists": (project_root / relative).is_file()})
    closed = {
        "version": EPISODE_VERSION,
        "episode_id": resolved_id,
        "closed_at": _now(),
        "declared_summary": str(summary).strip(),
        "declared_work_items": [str(item).strip() for item in work_items if str(item).strip()],
        "outcome": str(outcome or "closed_without_completion_claim").strip(),
        "new_blockers": [str(item).strip() for item in blockers if str(item).strip()],
        "recommended_next_action": str(next_action or "").strip(),
        "observed_artifacts": list(artifacts.values()),
        "observed_workspace_delta": _workspace_delta(opened.get("workspace_snapshot") or {}, _workspace_snapshot(project_root)),
        "linked_receipts": linked_receipts,
        "context_hash": opened.get("context_hash", ""),
        "does_not_prove": DOES_NOT_PROVE,
    }
    _write_json(directory / "closed.json", closed)
    if str(active.get("episode_id") or "") == resolved_id:
        _write_json(active_path, {"episode_id": resolved_id, "state": "closed", "updated_at": _now()})
    return {"status": "CLOSED", "episode": opened, "close": closed}


def context_episode_status(
    root: Path | str,
    *,
    episode_id: str = "",
    conversation_id: str = "",
) -> dict[str, Any]:
    project_root = Path(root).resolve()
    resolved_conversation_id = str(conversation_id or os.environ.get("AEROS_CONVERSATION_ID", ""))
    active = _read_json(_active_path(project_root, _slug(resolved_conversation_id)))
    resolved_id = str(episode_id or active.get("episode_id") or "")
    if not resolved_id:
        return {"status": "ABSENT", "message": "No context episode has been recorded for this conversation key."}
    opened = _load_opened(project_root, resolved_id)
    if not opened:
        return {"status": "UNREADABLE", "episode_id": resolved_id}
    directory = _episode_dir(project_root, resolved_id)
    if (directory / "closed.json").exists():
        state = "closed"
    elif (directory / "superseded.json").exists():
        state = "superseded_without_close"
    else:
        state = "open"
    return {
        "status": state.upper(),
        "episode_id": resolved_id,
        "conversation_id": opened.get("conversation_id", ""),
        "opened_at": opened.get("opened_at", ""),
        "context_hash": opened.get("context_hash", ""),
        "lane": (opened.get("context_projection") or {}).get("lane", "project"),
        "active_pointer_state": active.get("state", ""),
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_context_episode(report: dict[str, Any]) -> str:
    close = report.get("close") if isinstance(report.get("close"), dict) else {}
    episode = report.get("episode") if isinstance(report.get("episode"), dict) else {}
    if close:
        delta = close.get("observed_workspace_delta") or {}
        lines = [
            "# CONTEXT_EPISODE",
            "",
            f"status: {report.get('status', '')}",
            f"episode_id: {close.get('episode_id', '')}",
            f"declared_summary: {close.get('declared_summary', '')}",
            f"outcome: {close.get('outcome', '')}",
            f"observed_workspace_delta: {delta.get('status', 'unknown')} ({delta.get('path_count', 0)} path(s))",
            f"artifacts_recorded: {len(close.get('observed_artifacts') or [])}",
        ]
        for item in close.get("new_blockers") or []:
            lines.append(f"blocker: {item}")
        if close.get("recommended_next_action"):
            lines.append(f"next_action: {close.get('recommended_next_action')}")
        lines.append("This record separates declared work from observed artifacts; it is not completion or scientific validation.")
        return "\n".join(lines)
    if episode:
        projection = episode.get("context_projection") or {}
        return "\n".join([
            "# CONTEXT_EPISODE",
            "",
            f"status: {report.get('status', '')}",
            f"episode_id: {episode.get('episode_id', '')}",
            f"lane: {projection.get('lane', 'project')}",
            f"context_hash: {episode.get('context_hash', '')}",
            f"current_goal: {projection.get('goal', '')}",
            "This record is a scoped context basis, not completion or authority.",
        ])
    return "# CONTEXT_EPISODE\n\nstatus: " + str(report.get("status", "ABSENT"))
