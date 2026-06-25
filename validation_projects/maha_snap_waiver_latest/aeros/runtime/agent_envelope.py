"""Audit envelope for LLM/provider-backed agent task runs.

AgentEnvelope v1 is intentionally audit-first. It does not claim full sandboxing
for Claude/Codex/provider agents. It observes writes after an agent call and
blocks task acceptance when those writes violate the task contract or protected
authority boundaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


DEFAULT_DENY_ROOTS = (
    "data/raw/",
    "decisions/approvals/",
    "aeros/state/",
)

SENSITIVE_FILES = (
    "aeros_state.yml",
    "evidence/claim_registry.md",
    "decisions/decision_log.csv",
)


@dataclass(frozen=True)
class AgentEnvelopeSnapshot:
    dirty_paths: tuple[str, ...]
    sensitive_hashes: dict[str, str]


@dataclass(frozen=True)
class AgentEnvelopeAudit:
    task_id: str
    mode: str
    observed_writes: tuple[str, ...]
    allowed_writes: tuple[str, ...]
    denied_writes: tuple[str, ...]
    undeclared_writes: tuple[str, ...]
    sensitive_writes: tuple[str, ...]
    preexisting_dirty_paths: tuple[str, ...]
    violations: tuple[str, ...]
    does_not_prove: tuple[str, ...] = (
        "full LLM-agent sandboxing",
        "safe provider/network behavior",
        "scientific validity",
        "claim support",
        "gate approval",
    )

    @property
    def ok(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in (
            "observed_writes",
            "allowed_writes",
            "denied_writes",
            "undeclared_writes",
            "sensitive_writes",
            "preexisting_dirty_paths",
            "violations",
            "does_not_prove",
        ):
            data[key] = list(data.get(key) or [])
        data["ok"] = self.ok
        return data


def _git_status_paths(root: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return ()
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        path = path.strip('"').lstrip("./")
        if path:
            paths.append(path)
    return tuple(sorted(dict.fromkeys(paths)))


def _hash_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _under(path: str, roots: tuple[str, ...]) -> bool:
    path = path.strip().lstrip("./")
    for root in roots:
        root = root.strip().lstrip("./")
        if not root:
            continue
        if root in {".", "*"}:
            return True
        if root.endswith("/") and path.startswith(root):
            return True
        if path == root or path.startswith(root + "/"):
            return True
    return False


def _allowed(path: str, allowed_outputs: tuple[str, ...]) -> bool:
    return _under(path, allowed_outputs)


def load_agent_envelope_policy(root: Path) -> dict[str, Any]:
    path = root / "harness/agent_envelope_policy.yml"
    if not path.exists():
        return {"mode": "audit", "block_on_violation": True}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"mode": "audit", "block_on_violation": True}


def snapshot_agent_envelope(root: Path) -> AgentEnvelopeSnapshot:
    return AgentEnvelopeSnapshot(
        dirty_paths=_git_status_paths(root),
        sensitive_hashes={rel: _hash_file(root / rel) for rel in SENSITIVE_FILES},
    )


def audit_agent_writes(
    root: Path,
    contract: Any,
    before: AgentEnvelopeSnapshot,
    *,
    policy: dict[str, Any] | None = None,
) -> AgentEnvelopeAudit:
    policy = policy or load_agent_envelope_policy(root)
    mode = str(policy.get("mode") or "audit")
    allowed_outputs = tuple(str(path).strip() for path in getattr(contract, "allowed_outputs", []) if str(path).strip())
    deny_roots = tuple(str(path).strip() for path in (policy.get("deny_roots") or DEFAULT_DENY_ROOTS) if str(path).strip())
    after_dirty = set(_git_status_paths(root))
    before_dirty = set(before.dirty_paths)
    observed = set(after_dirty - before_dirty)

    sensitive_writes: set[str] = set()
    for rel, before_hash in before.sensitive_hashes.items():
        after_hash = _hash_file(root / rel)
        if after_hash != before_hash:
            sensitive_writes.add(rel)
            observed.add(rel)

    denied = tuple(sorted(path for path in observed if _under(path, deny_roots)))
    undeclared = tuple(
        sorted(
            path for path in observed
            if path not in denied and not _allowed(path, allowed_outputs)
        )
    )
    allowed = tuple(sorted(path for path in observed if path not in denied and path not in undeclared))
    violations: list[str] = []
    if denied:
        violations.append("denied_writes: " + ", ".join(denied))
    if undeclared:
        violations.append("undeclared_writes: " + ", ".join(undeclared))
    if sensitive_writes:
        for rel in sorted(sensitive_writes):
            if not _allowed(rel, allowed_outputs):
                violations.append(f"sensitive_write_without_declared_output: {rel}")

    return AgentEnvelopeAudit(
        task_id=str(getattr(contract, "task_id", "unknown")),
        mode=mode,
        observed_writes=tuple(sorted(observed)),
        allowed_writes=allowed,
        denied_writes=denied,
        undeclared_writes=undeclared,
        sensitive_writes=tuple(sorted(sensitive_writes)),
        preexisting_dirty_paths=before.dirty_paths,
        violations=tuple(dict.fromkeys(violations)),
    )


def format_agent_envelope_audit(audit: AgentEnvelopeAudit) -> str:
    if audit.ok:
        return (
            f"AgentEnvelope audit passed for {audit.task_id}: "
            f"{len(audit.allowed_writes)} declared write(s)."
        )
    lines = [f"AgentEnvelope audit failed for {audit.task_id}:"]
    lines.extend(f"- {violation}" for violation in audit.violations)
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in audit.does_not_prove)
    return "\n".join(lines)


def write_agent_envelope_audit(root: Path, audit: AgentEnvelopeAudit) -> Path:
    out_dir = root / "agent_runs" / "agent_envelope_audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"{audit.task_id}_{stamp}.json"
    path.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
