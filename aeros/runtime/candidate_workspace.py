"""Isolated candidate-worktree execution for write-producing callbacks.

The callback may call an LLM/provider or any other runtime that writes project
artifacts.  It runs against a detached git worktree.  Only declared,
non-protected, non-empty candidate outputs are copied back to the main project;
the callback cannot write canonical authority surfaces by construction.

This is filesystem confinement, not a network, credential, cost, or scientific
validity sandbox.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Callable
import json
import re
import shutil
import subprocess
import tempfile

import yaml


DEFAULT_DENY_ROOTS = (
    ".git/",
    "aeros/state/",
    "data/raw/",
    "data/processed/",
    "data/canonical/",
    "decisions/approvals/",
    "decisions/decision_log.csv",
    "evidence/claim_registry.md",
    "evidence/evidence_ledger.csv",
    "evidence/result_registry.csv",
)


@dataclass(frozen=True)
class CandidateWorkspaceResult:
    callback_value: Any = None
    callback_ok: bool = False
    boundary_ok: bool = False
    observed_writes: tuple[str, ...] = ()
    accepted_outputs: tuple[str, ...] = ()
    denied_writes: tuple[str, ...] = ()
    undeclared_writes: tuple[str, ...] = ()
    missing_expected_outputs: tuple[str, ...] = ()
    empty_outputs: tuple[str, ...] = ()
    main_conflicts: tuple[str, ...] = ()
    callback_error: str = ""
    worktree_removed: bool = False

    @property
    def ok(self) -> bool:
        return self.callback_ok and self.boundary_ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "callback_ok": self.callback_ok,
            "boundary_ok": self.boundary_ok,
            "observed_writes": list(self.observed_writes),
            "accepted_outputs": list(self.accepted_outputs),
            "denied_writes": list(self.denied_writes),
            "undeclared_writes": list(self.undeclared_writes),
            "missing_expected_outputs": list(self.missing_expected_outputs),
            "empty_outputs": list(self.empty_outputs),
            "main_conflicts": list(self.main_conflicts),
            "callback_error": self.callback_error,
            "worktree_removed": self.worktree_removed,
            "does_not_prove": [
                "safe provider or network behavior",
                "credential authorization",
                "scientific validity",
                "canonical promotion, claim admission, gate approval, or release",
            ],
        }


def load_candidate_policy(root: Path) -> dict[str, Any]:
    path = root / "harness/agent_envelope_policy.yml"
    if not path.exists():
        return {"mode": "isolated_candidate", "block_on_violation": True, "deny_roots": list(DEFAULT_DENY_ROOTS)}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def _normalise(value: str) -> str:
    return value.strip().replace("\\", "/").lstrip("./")


def _matches(path: str, rule: str) -> bool:
    path = _normalise(path)
    rule = _normalise(rule)
    if not rule:
        return False
    if any(char in rule for char in "*?["):
        return fnmatch(path, rule)
    if rule.endswith("/"):
        return path == rule.rstrip("/") or path.startswith(rule)
    return path == rule


def _status_entries(root: Path) -> dict[str, str]:
    proc = _git(root, "status", "--porcelain", "--untracked-files=all")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git status failed")
    entries: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        entries[_normalise(rel)] = status
    return entries


def _callback_succeeded(value: Any) -> bool:
    if isinstance(value, int):
        return value == 0
    if hasattr(value, "ok"):
        return bool(getattr(value, "ok"))
    return value is not None


def _expected_problem(worktree: Path, observed: tuple[str, ...], rule: str) -> tuple[bool, bool]:
    matches = [path for path in observed if _matches(path, rule)]
    if not matches:
        return True, False
    files = [worktree / path for path in matches]
    nonempty = any(path.is_file() and not path.is_symlink() and path.stat().st_size > 0 for path in files)
    return False, not nonempty


def _copy_outputs(worktree: Path, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    copied: list[str] = []
    for rel in paths:
        src = worktree / rel
        if not src.is_file() or src.is_symlink():
            continue
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return tuple(copied)


def execute_callback_in_candidate_worktree(
    root: Path,
    callback: Callable[[Path], Any],
    *,
    allowed_outputs: tuple[str, ...] | list[str],
    expected_outputs: tuple[str, ...] | list[str] | None = None,
    deny_roots: tuple[str, ...] | list[str] = DEFAULT_DENY_ROOTS,
) -> CandidateWorkspaceResult:
    root = root.resolve()
    allowed = tuple(_normalise(item) for item in allowed_outputs if _normalise(item))
    expected = tuple(_normalise(item) for item in (expected_outputs or allowed) if _normalise(item))
    denied_rules = tuple(_normalise(item) for item in deny_roots if _normalise(item))
    main_before = _status_entries(root)
    value: Any = None
    callback_error = ""
    callback_ok = False
    observed: tuple[str, ...] = ()
    accepted: tuple[str, ...] = ()
    denied: tuple[str, ...] = ()
    undeclared: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    empty: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    cleanup_ok = False

    with tempfile.TemporaryDirectory(prefix="aeros_candidate_workspace_") as tmp_name:
        worktree = Path(tmp_name) / "worktree"
        add = _git(root, "worktree", "add", "--detach", str(worktree), "HEAD")
        if add.returncode != 0:
            return CandidateWorkspaceResult(callback_error=add.stderr.strip() or "git worktree add failed")
        try:
            try:
                value = callback(worktree)
                callback_ok = _callback_succeeded(value)
            except Exception as exc:  # noqa: BLE001
                callback_error = str(exc)
                callback_ok = False

            entries = _status_entries(worktree)
            observed = tuple(sorted(entries))
            denied = tuple(sorted(path for path in observed if any(_matches(path, rule) for rule in denied_rules)))
            undeclared = tuple(sorted(path for path in observed if not any(_matches(path, rule) for rule in allowed)))
            deleted = tuple(sorted(path for path, status in entries.items() if "D" in status))
            symlinks = tuple(sorted(path for path in observed if (worktree / path).is_symlink()))
            if deleted or symlinks:
                undeclared = tuple(sorted(set(undeclared) | set(deleted) | set(symlinks)))
            conflicts = tuple(sorted(path for path in observed if path in main_before))

            if callback_ok:
                missing_items: list[str] = []
                empty_items: list[str] = []
                for rule in expected:
                    is_missing, is_empty = _expected_problem(worktree, observed, rule)
                    if is_missing:
                        missing_items.append(rule)
                    elif is_empty:
                        empty_items.append(rule)
                missing = tuple(sorted(missing_items))
                empty = tuple(sorted(empty_items))

            boundary_ok = not (denied or undeclared or missing or empty or conflicts)
            if callback_ok and boundary_ok:
                accepted = _copy_outputs(worktree, root, observed)
        finally:
            remove = _git(root, "worktree", "remove", "--force", str(worktree))
            cleanup_ok = remove.returncode == 0 and not worktree.exists()

    return CandidateWorkspaceResult(
        callback_value=value,
        callback_ok=callback_ok,
        boundary_ok=not (denied or undeclared or missing or empty or conflicts),
        observed_writes=observed,
        accepted_outputs=accepted,
        denied_writes=denied,
        undeclared_writes=undeclared,
        missing_expected_outputs=missing,
        empty_outputs=empty,
        main_conflicts=conflicts,
        callback_error=callback_error,
        worktree_removed=cleanup_ok,
    )


def format_candidate_workspace_failure(result: CandidateWorkspaceResult) -> str:
    parts = ["Candidate workspace rejected provider/agent output."]
    for label, values in (
        ("denied_writes", result.denied_writes),
        ("undeclared_writes", result.undeclared_writes),
        ("missing_expected_outputs", result.missing_expected_outputs),
        ("empty_outputs", result.empty_outputs),
        ("main_conflicts", result.main_conflicts),
    ):
        if values:
            parts.append(f"{label}=" + ", ".join(values))
    if result.callback_error:
        parts.append("callback_error=" + result.callback_error)
    return "\n".join(parts)


def write_candidate_workspace_audit(root: Path, task_id: str, result: CandidateWorkspaceResult) -> Path:
    out_dir = root / "agent_runs" / "agent_envelope_audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_id).strip("_") or "provider"
    path = out_dir / f"{safe}_{stamp}.json"
    payload = {"task_id": task_id, "mode": "isolated_candidate", **result.to_dict()}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
