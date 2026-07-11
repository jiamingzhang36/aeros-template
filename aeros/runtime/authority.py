"""Tiered authority evidence for bounded human-only actions.

``local_authorship`` is a cooperative local provenance anchor, not proof of a
real-world person. ``signed_commit`` additionally requires Git to verify the
last commit's SSH/GPG signature. ``external_human_approval`` is reserved and
fails closed until an independent verifier is configured.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any

import yaml

from .identity import approved_by_human, last_commit_author

AUTHORITY_LEVELS = {"local_authorship", "signed_commit", "external_human_approval"}


@dataclass(frozen=True)
class AuthorityEvidence:
    level: str
    granted: bool
    actor: str = ""
    artifact: str = ""
    verification_method: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, timeout=20)


def evaluate_authority(root: Path, artifact: Path, level: str) -> AuthorityEvidence:
    level = str(level or "local_authorship").strip()
    rel = str(artifact.resolve().relative_to(root.resolve()))
    if level not in AUTHORITY_LEVELS:
        return AuthorityEvidence(level, False, artifact=rel, reason=f"unknown authority evidence level: {level}")
    local_granted, local_reason = approved_by_human(artifact, root)
    actor = last_commit_author(artifact, root) or ""
    if not local_granted:
        return AuthorityEvidence(level, False, actor, rel, "git_committer_allowlist", local_reason)
    if level == "local_authorship":
        return AuthorityEvidence(
            level, True, actor, rel, "configured_local_git_authorship",
            "configured local approver authored the clean committed artifact; real-world human identity is not proven",
        )
    if level == "signed_commit":
        commit = _git(root, "log", "-1", "--format=%H", "--", rel)
        commit_hash = commit.stdout.strip() if commit.returncode == 0 else ""
        verified = _git(root, "verify-commit", commit_hash) if commit_hash else None
        if not verified or verified.returncode != 0:
            detail = ((verified.stderr if verified else "") or (verified.stdout if verified else "")).strip()
            return AuthorityEvidence(level, False, actor, rel, "git_verify_commit", detail or "commit signature is not verifiable")
        return AuthorityEvidence(level, True, actor, rel, "git_verify_commit", "signed commit verified by Git")
    return AuthorityEvidence(
        level, False, actor, rel, "external_verifier_required",
        "external_human_approval is reserved; no independent verifier is configured",
    )


def load_requested_level(artifact: Path) -> str:
    try:
        data = yaml.safe_load(artifact.read_text(encoding="utf-8")) or {}
    except Exception:
        return ""
    return str(data.get("authority_evidence") or "local_authorship").strip()

