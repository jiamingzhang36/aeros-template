"""Compile ActionSpec semantics into monotonic runtime environment profiles.

This is intentionally a compiler, not an additional agent-role system.  The
profile is derived from typed ActionSpec fields and can only narrow a supplied
ExecutionEnvelope.  Current local worktree enforcement makes write boundaries
real for deterministic actions; network, credential, and read-root fields are
durable policy inputs for runtimes that can enforce them.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml


POLICY_NAME = "AEROS-ENV-PROFILE-001"
POLICY_FILE = Path("harness/environment_profiles.yml")
PROFILE_NAMES = frozenset({"capture", "analysis", "manuscript", "reviewer", "promotion"})


def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _clean_paths(values: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values or () if str(value).strip()))


def _under(path: str, root: str) -> bool:
    path = str(path).strip().lstrip("./")
    root = str(root).strip().lstrip("./")
    if root in {"", ".", "*"}:
        return True
    if root.endswith("/"):
        return path.startswith(root)
    return path == root or path.startswith(root + "/")


def _narrow_roots(requested: tuple[str, ...], allowed: tuple[str, ...]) -> tuple[str, ...]:
    """Return the path-root intersection without granting a broader root."""
    narrowed: list[str] = []
    for request in requested:
        for permit in allowed:
            if _under(request, permit):
                narrowed.append(request)
            elif _under(permit, request):
                narrowed.append(permit)
    return tuple(dict.fromkeys(narrowed))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def load_environment_profiles(root: Path | None = None) -> dict[str, Any]:
    candidates = []
    if root is not None:
        candidates.append(Path(root).resolve() / POLICY_FILE)
    candidates.append(_source_root() / POLICY_FILE)
    for path in candidates:
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                return data
    raise FileNotFoundError(f"missing {POLICY_FILE}")


def select_environment_profile(data: dict[str, Any]) -> str:
    boundary = data.get("authority_boundary") if isinstance(data.get("authority_boundary"), dict) else {}
    effect = str(data.get("effect_class") or "").strip()
    lane = str(data.get("lane") or "").strip().lower()
    kind = str(data.get("kind") or "").strip().lower()
    capabilities = {str(item).strip().lower() for item in data.get("capabilities") or ()}
    boundary_values = {str(value).strip().lower() for value in boundary.values()}

    if effect in {"human_decision", "blocked"} or boundary_values & {"canonical", "promote", "release", "approve", "apply"}:
        return "promotion"
    if any(item.startswith("network_") for item in capabilities) or any(token in kind for token in ("capture", "search", "probe", "fetch", "recover")):
        return "capture"
    if lane in {"writing", "manuscript", "paper"} or any(token in kind for token in ("draft", "manuscript", "writing")):
        return "manuscript"
    if effect == "read_only" or any(token in kind for token in ("review", "audit", "check", "validate")):
        return "reviewer"
    return "analysis"


def compile_environment_profile(data: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    policy = load_environment_profiles(root)
    profile_id = select_environment_profile(data)
    profiles = policy.get("profiles") if isinstance(policy.get("profiles"), dict) else {}
    source = profiles.get(profile_id) if isinstance(profiles, dict) else None
    if not isinstance(source, dict):
        raise ValueError(f"environment profile {profile_id!r} is unavailable")
    policy_view = {
        "policy": str(policy.get("policy") or POLICY_NAME),
        "version": int(policy.get("version") or 1),
        "profile": profile_id,
        "network_policy": str(source.get("network_policy") or "deny"),
        "credential_policy": str(source.get("credential_policy") or "scrub_all"),
        "shell_environment_policy": str(source.get("shell_environment_policy") or "clean_allowlist"),
        "read_roots": list(_clean_paths(source.get("read_roots"))),
        "write_roots": list(_clean_paths(source.get("write_roots"))),
        "deny_roots": list(_clean_paths(source.get("deny_roots"))),
        "requires_human_decision": bool(source.get("requires_human_decision", False)),
        "does_not_prove": list(_clean_paths(source.get("does_not_prove"))),
    }
    policy_digest = _digest(policy_view)
    approval_identity = {
        "policy_digest": policy_digest,
        "kind": str(data.get("kind") or ""),
        "lane": str(data.get("lane") or ""),
        "effect_class": str(data.get("effect_class") or ""),
        "campaign_id": str(data.get("campaign_id") or ""),
        "expected_outputs": list(_clean_paths(data.get("expected_outputs"))),
        "authority_boundary": data.get("authority_boundary") if isinstance(data.get("authority_boundary"), dict) else {},
    }
    return {
        **policy_view,
        "policy_digest": policy_digest,
        "approval_fingerprint": _digest(approval_identity),
        "compiled_from": "ActionSpec",
    }


def validate_environment_profile(profile: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not isinstance(profile, dict):
        return ["environment_profile must be a mapping"]
    if str(profile.get("profile") or "") not in PROFILE_NAMES:
        failures.append("environment_profile has an unknown profile")
    for field in ("policy", "policy_digest", "approval_fingerprint", "network_policy", "credential_policy"):
        if not str(profile.get(field) or "").strip():
            failures.append(f"environment_profile missing {field}")
    expected = {
        key: profile.get(key)
        for key in (
            "policy", "version", "profile", "network_policy", "credential_policy",
            "shell_environment_policy", "read_roots", "write_roots", "deny_roots",
            "requires_human_decision", "does_not_prove",
        )
    }
    if str(profile.get("policy_digest") or "") and _digest(expected) != str(profile.get("policy_digest")):
        failures.append("environment_profile policy_digest does not match policy fields")
    return failures


def effective_envelope_data(base: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Intersect existing envelope authority with a compiled profile."""
    merged = dict(base)
    requested_read = _clean_paths(merged.get("read_roots") or (".",))
    requested_write = _clean_paths(merged.get("write_roots"))
    profile_read = _clean_paths(profile.get("read_roots"))
    profile_write = _clean_paths(profile.get("write_roots"))
    merged["read_roots"] = list(_narrow_roots(requested_read, profile_read))
    merged["write_roots"] = list(_narrow_roots(requested_write, profile_write))
    merged["deny_roots"] = list(dict.fromkeys((*_clean_paths(merged.get("deny_roots")), *_clean_paths(profile.get("deny_roots")))))
    merged["environment_profile"] = str(profile.get("profile") or "")
    merged["environment_policy_digest"] = str(profile.get("policy_digest") or "")
    merged["environment_approval_fingerprint"] = str(profile.get("approval_fingerprint") or "")
    merged["network_policy"] = str(profile.get("network_policy") or "deny")
    merged["credential_policy"] = str(profile.get("credential_policy") or "scrub_all")
    merged["shell_environment_policy"] = str(profile.get("shell_environment_policy") or "clean_allowlist")
    return merged


def environment_profile_errors(data: dict[str, Any], envelope: dict[str, Any]) -> list[str]:
    profile = data.get("environment_profile") if isinstance(data.get("environment_profile"), dict) else compile_environment_profile(data)
    failures = validate_environment_profile(profile)
    if profile.get("requires_human_decision") and not bool(data.get("requires_decision")):
        failures.append("promotion environment requires a human decision")
    write_roots = _clean_paths(envelope.get("write_roots"))
    for output in _clean_paths(data.get("expected_outputs")):
        if not any(_under(output, root) for root in write_roots):
            failures.append(f"environment profile denies expected output: {output}")
    return failures


def policy_digest_for_action(data: dict[str, Any]) -> str:
    profile = data.get("environment_profile") if isinstance(data.get("environment_profile"), dict) else compile_environment_profile(data)
    return str(profile.get("policy_digest") or "")
