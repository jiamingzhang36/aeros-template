"""Trust anchor: bind human-only actions to a git committer identity.

AEROS gates ("human adjudication") are only meaningful if the autonomous agent
*cannot* grant them. Field-presence checks are forgeable: the same agent that
runs the work can write ``human_decision: approved`` into a markdown file.

This module ties an approval to the git *author* of the commit that last
touched the artifact. The autonomous loop is configured to commit under an
``agent_identity`` and is forbidden from changing git config; only commits
authored by an ``approver_identity`` count as a human grant.

Single-user reality: one person may hold both identities, so this is
*tamper-evident* (every bypass leaves a traceable git author), not
*tamper-proof*. For true tamper resistance, escalate to GPG-signed commits;
the interface here stays the same.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

PERMISSIONS = Path("harness/permissions.yml")


def _load_human_approval(project_root: Path) -> dict:
    path = project_root / PERMISSIONS
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    section = data.get("human_approval", {})
    return section if isinstance(section, dict) else {}


def _as_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def approver_identities(project_root: Path) -> list[str]:
    return _as_list(_load_human_approval(project_root).get("approver_identity"))


def agent_identities(project_root: Path) -> list[str]:
    return _as_list(_load_human_approval(project_root).get("agent_identity"))


def enforcement_enabled(project_root: Path) -> bool:
    return str(_load_human_approval(project_root).get("enforcement", "")).strip() == "git_committer"


def _rel(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path)


def _git(project_root: Path, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", "-C", str(project_root), *args],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def last_commit_author(path: Path, project_root: Path) -> str | None:
    """Author name of the last commit that touched ``path``; None if untracked."""
    rel = _rel(path, project_root)
    result = _git(project_root, "log", "-1", "--format=%an", "--", rel)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.strip() or None


def has_uncommitted_changes(path: Path, project_root: Path) -> bool:
    rel = _rel(path, project_root)
    result = _git(project_root, "status", "--porcelain", "--", rel)
    if result is None:
        return True  # fail closed: cannot prove it is committed
    return bool(result.stdout.strip())


def approved_by_human(path: Path, project_root: Path) -> tuple[bool, str]:
    """Return (granted, reason) for a human-only artifact at ``path``.

    Granted only when ``path`` is committed (clean) and its last commit author
    is in ``approver_identity``. An artifact committed by an ``agent_identity``
    is explicitly rejected.
    """
    approvers = approver_identities(project_root)
    if not approvers:
        return False, "no approver_identity configured in harness/permissions.yml human_approval"
    if not (project_root / path).exists() and not (Path(path).is_absolute() and Path(path).exists()):
        return False, f"approval artifact does not exist: {path}"
    if has_uncommitted_changes(path, project_root):
        return False, f"{path} has uncommitted changes; an approver must commit it to grant approval"
    author = last_commit_author(path, project_root)
    if author is None:
        return False, f"{path} is not committed; cannot verify approver identity"
    if author in agent_identities(project_root):
        return False, f"{path} was committed by agent identity {author!r}; the agent cannot grant its own approval"
    if author not in approvers:
        return False, f"{path} last committed by {author!r}, not an approved identity {approvers}"
    return True, f"approved by {author}"
