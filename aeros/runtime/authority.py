"""Tiered, identity-bound authority evidence for human-only actions.

``local_authorship`` is provenance only. Security-sensitive consumers impose a
minimum authority floor (signed by default). Signed authority is verified
against trust anchors stored in the committed ``harness/permissions.yml``;
repository-local ``allowedSignersFile`` configuration is never trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import yaml

from .identity import has_uncommitted_changes, last_commit_author

AUTHORITY_RANK = {
    "local_authorship": 0,
    "signed_commit": 1,
    "external_human_approval": 2,
}
AUTHORITY_LEVELS = frozenset(AUTHORITY_RANK)
SECURE_DEFAULT_MINIMUMS = {
    "campaign_release": "signed_commit",
    "gate_approval": "signed_commit",
    "gate_apply": "signed_commit",
    "claim_upgrade": "signed_commit",
    "rubric_freeze": "signed_commit",
    "release": "signed_commit",
}


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


def authority_meets(actual: str, required: str) -> bool:
    return AUTHORITY_RANK.get(actual, -1) >= AUTHORITY_RANK.get(required, 10**6)


def _committed_policy(root: Path) -> tuple[dict[str, Any], str]:
    policy = root / "harness/permissions.yml"
    if not policy.exists():
        return {}, "harness/permissions.yml is missing"
    if has_uncommitted_changes(policy, root):
        return {}, "harness/permissions.yml has uncommitted changes; authority trust policy fails closed"
    shown = _git(root, "show", "HEAD:harness/permissions.yml")
    if shown.returncode != 0:
        return {}, "harness/permissions.yml is not available from committed HEAD"
    try:
        data = yaml.safe_load(shown.stdout) or {}
    except Exception as exc:
        return {}, f"committed permissions policy cannot be parsed: {exc}"
    human = data.get("human_approval") or {}
    return (human if isinstance(human, dict) else {}), ""


def minimum_authority(root: Path, action: str) -> tuple[str, str]:
    human, error = _committed_policy(root)
    if error:
        return "", error
    configured = human.get("minimum_authority") or {}
    floor = SECURE_DEFAULT_MINIMUMS.get(action, "signed_commit")
    level = str((configured.get(action) if isinstance(configured, dict) else "") or floor).strip()
    if level not in AUTHORITY_LEVELS:
        return "", f"invalid minimum authority for {action}: {level}"
    if not authority_meets(level, floor):
        return "", f"configured minimum {level} cannot weaken the built-in {floor} floor for {action}"
    return level, ""


def _trusted_signers(human: dict[str, Any], actor: str) -> tuple[list[tuple[str, str]], set[str]]:
    ssh: list[tuple[str, str]] = []
    gpg: set[str] = set()
    for row in human.get("trusted_signers") or []:
        if not isinstance(row, dict) or str(row.get("identity") or "").strip() != actor:
            continue
        principal = str(row.get("principal") or "").strip()
        public_key = str(row.get("ssh_public_key") or "").strip()
        if principal and public_key:
            ssh.append((principal, public_key))
        fingerprint = str(row.get("gpg_fingerprint") or "").replace(" ", "").upper()
        if fingerprint:
            gpg.add(fingerprint)
    return ssh, gpg


def _verify_signed_commit(root: Path, commit_hash: str, actor: str, human: dict[str, Any]) -> tuple[bool, str, str]:
    ssh, gpg = _trusted_signers(human, actor)
    if not ssh and not gpg:
        return False, "protected_trust_anchor", f"no committed trusted signer is bound to approver identity {actor!r}"
    if ssh:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            for principal, key in ssh:
                handle.write(f"{principal} {key}\n")
            handle.flush()
            verified = _git(root, "-c", "gpg.format=ssh", "-c", f"gpg.ssh.allowedSignersFile={handle.name}", "verify-commit", commit_hash)
        if verified.returncode == 0:
            return True, "git_verify_commit_protected_ssh_anchor", "SSH signature matches the committed signer bound to the approver"
    if gpg:
        verified = _git(root, "verify-commit", "--raw", commit_hash)
        raw = (verified.stderr or "") + "\n" + (verified.stdout or "")
        for line in raw.splitlines():
            if "VALIDSIG " in line:
                fingerprint = line.split("VALIDSIG ", 1)[1].split()[0].replace(" ", "").upper()
                if verified.returncode == 0 and fingerprint in gpg:
                    return True, "git_verify_commit_protected_gpg_anchor", "GPG signature fingerprint matches the committed approver binding"
    return False, "protected_trust_anchor", "commit signature does not match a committed signer bound to this approver"


def _policy_evolution_error(root: Path, current: dict[str, Any]) -> str:
    """Require later trust-policy changes to be signed by the prior signer."""
    history = _git(root, "log", "-2", "--format=%H", "--", "harness/permissions.yml")
    commits = [row.strip() for row in history.stdout.splitlines() if row.strip()] if history.returncode == 0 else []
    if len(commits) < 2:
        return ""
    current_commit, previous_commit = commits[0], commits[1]
    previous = _git(root, "show", f"{previous_commit}:harness/permissions.yml")
    try:
        previous_data = yaml.safe_load(previous.stdout) or {} if previous.returncode == 0 else {}
        previous_human = previous_data.get("human_approval") or {}
    except Exception:
        return "previous committed permissions policy cannot be parsed"
    previous_signers = previous_human.get("trusted_signers") or [] if isinstance(previous_human, dict) else []
    current_signers = current.get("trusted_signers") or []
    if not previous_signers:
        if current_signers:
            bootstrap = current.get("trust_bootstrap") or {}
            if not isinstance(bootstrap, dict) or bootstrap.get("method") != "interactive_fingerprint_confirmation":
                return "first signer enrollment lacks an explicit interactive trust bootstrap record"
            actor_result = _git(root, "show", "-s", "--format=%an", current_commit)
            actor = actor_result.stdout.strip() if actor_result.returncode == 0 else ""
            granted, _, reason = _verify_signed_commit(root, current_commit, actor, current)
            if not granted:
                return f"first signer enrollment commit is not signed by the confirmed bootstrap key: {reason}"
        return ""
    actor_result = _git(root, "show", "-s", "--format=%an", current_commit)
    actor = actor_result.stdout.strip() if actor_result.returncode == 0 else ""
    granted, _, reason = _verify_signed_commit(root, current_commit, actor, previous_human)
    if not granted:
        return f"permissions policy update is not signed by a signer trusted in the preceding policy: {reason}"
    return ""


def bootstrap_ssh_signer(root: Path, *, identity: str, principal: str, public_key: str,
                         confirmed_fingerprint: str) -> tuple[Path, str]:
    """Record first-signer TOFU after an external fingerprint comparison."""
    policy = root / "harness/permissions.yml"
    if not policy.exists() or has_uncommitted_changes(policy, root):
        raise PermissionError("bootstrap requires a clean committed harness/permissions.yml")
    data = yaml.safe_load(policy.read_text(encoding="utf-8")) or {}
    human = data.setdefault("human_approval", {})
    if human.get("trusted_signers"):
        raise PermissionError("trust is already bootstrapped; rotate it with a commit signed by the old signer")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
        handle.write(public_key.strip() + "\n"); handle.flush()
        result = subprocess.run(["ssh-keygen", "-lf", handle.name, "-E", "sha256"], text=True, capture_output=True, timeout=20)
    parts = result.stdout.split() if result.returncode == 0 else []
    fingerprint = parts[1] if len(parts) > 1 else ""
    if not fingerprint or confirmed_fingerprint.strip() != fingerprint:
        raise PermissionError("fingerprint confirmation does not match the supplied SSH public key")
    approvers = [str(item).strip() for item in human.get("approver_identity") or []]
    if identity not in approvers:
        raise PermissionError("bootstrap identity must already be listed in approver_identity")
    human["trusted_signers"] = [{"identity": identity, "principal": principal, "ssh_public_key": public_key.strip()}]
    human["trust_bootstrap"] = {
        "method": "interactive_fingerprint_confirmation",
        "fingerprint": fingerprint,
        "confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "boundary": "TOFU ceremony; does not independently prove real-world identity",
    }
    policy.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return policy, fingerprint


def evaluate_authority(root: Path, artifact: Path, level: str) -> AuthorityEvidence:
    level = str(level or "local_authorship").strip()
    try:
        rel = str(artifact.resolve().relative_to(root.resolve()))
    except ValueError:
        return AuthorityEvidence(level, False, artifact=str(artifact), reason="authority artifact is outside the project")
    if level not in AUTHORITY_LEVELS:
        return AuthorityEvidence(level, False, artifact=rel, reason=f"unknown authority evidence level: {level}")
    human, policy_error = _committed_policy(root)
    if policy_error:
        return AuthorityEvidence(level, False, artifact=rel, verification_method="committed_permissions_policy", reason=policy_error)
    evolution_error = _policy_evolution_error(root, human)
    if evolution_error:
        return AuthorityEvidence(level, False, artifact=rel, verification_method="signed_policy_evolution", reason=evolution_error)
    if not artifact.exists() or has_uncommitted_changes(artifact, root):
        return AuthorityEvidence(level, False, artifact=rel, verification_method="committed_artifact", reason="approval artifact is missing, untracked, or modified after commit")
    actor = last_commit_author(artifact, root) or ""
    approvers = {str(item).strip() for item in human.get("approver_identity") or [] if str(item).strip()}
    agents = {str(item).strip() for item in human.get("agent_identity") or [] if str(item).strip()}
    if not actor or actor not in approvers or actor in agents:
        return AuthorityEvidence(level, False, actor, rel, "committed_approver_allowlist", f"artifact committer {actor!r} is not an eligible approver")
    if level == "local_authorship":
        return AuthorityEvidence(level, True, actor, rel, "configured_local_git_authorship", "configured local approver authored the clean committed artifact; real-world human identity is not proven")
    if level == "signed_commit":
        commit = _git(root, "log", "-1", "--format=%H", "--", rel)
        commit_hash = commit.stdout.strip() if commit.returncode == 0 else ""
        if not commit_hash:
            return AuthorityEvidence(level, False, actor, rel, "signed_commit", "approval commit cannot be resolved")
        granted, method, reason = _verify_signed_commit(root, commit_hash, actor, human)
        return AuthorityEvidence(level, granted, actor, rel, method, reason)
    return AuthorityEvidence(level, False, actor, rel, "external_verifier_required", "external_human_approval is reserved; no independent verifier is configured")


def evaluate_for_action(root: Path, artifact: Path, action: str) -> AuthorityEvidence:
    requested = load_requested_level(artifact)
    minimum, error = minimum_authority(root, action)
    if error:
        return AuthorityEvidence(requested, False, artifact=str(artifact), verification_method="minimum_authority_policy", reason=error)
    if not authority_meets(requested, minimum):
        return AuthorityEvidence(requested, False, artifact=str(artifact), verification_method="minimum_authority_floor", reason=f"{action} requires at least {minimum}; artifact requested {requested or '<missing>'}")
    return evaluate_authority(root, artifact, requested)


def load_requested_level(artifact: Path) -> str:
    try:
        text = artifact.read_text(encoding="utf-8")
        if text.startswith("---\n") and "\n---\n" in text[4:]:
            text = text.split("\n---\n", 1)[0][4:]
        data = yaml.safe_load(text) or {}
    except Exception:
        return ""
    if not isinstance(data, dict):
        return "local_authorship"
    return str(data.get("authority_evidence") or "local_authorship").strip()
