"""Observed-write audit for AEROS worktree changes.

This module compares observed git worktree writes with declared write roots and
protected-path policy. It is a dry-run audit/projection: it does not execute,
revert, approve gates, or certify research validity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import subprocess

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


DOES_NOT_PROVE = [
    "scientific validity",
    "claim support",
    "gate approval",
    "paper readiness",
    "that declared writes are desirable",
    "absence of off-repo side effects",
]

DEFAULT_PROTECTED_EXACT = {
    "docs/protected_definitions.yml",
    "docs/data_contract.yml",
    "evidence/claim_registry.md",
    "decisions/decision_log.csv",
    "harness/permissions.yml",
}

DEFAULT_PROTECTED_PREFIXES = {
    "data/raw/",
    "decisions/approvals/",
}


@dataclass(frozen=True)
class WriteAuditReport:
    status: str
    since: str
    observed_writes: tuple[str, ...]
    declared_writes: tuple[str, ...]
    undeclared_writes: tuple[str, ...]
    protected_writes: tuple[str, ...]
    recommended_action: str
    source_files: tuple[str, ...]
    does_not_prove: tuple[str, ...] = tuple(DOES_NOT_PROVE)

    @property
    def ok(self) -> bool:
        return self.status in {"PASS", "NO_WRITES"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "since": self.since,
            "observed_writes": list(self.observed_writes),
            "declared_writes": list(self.declared_writes),
            "undeclared_writes": list(self.undeclared_writes),
            "protected_writes": list(self.protected_writes),
            "recommended_action": self.recommended_action,
            "source_files": list(self.source_files),
            "does_not_prove": list(self.does_not_prove),
        }


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30, check=False)


def _normalize(path: str | Path) -> str:
    rel = str(path).strip().replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def _under(path: str, roots: tuple[str, ...]) -> bool:
    rel = _normalize(path)
    for raw in roots:
        root = _normalize(raw)
        if not root:
            continue
        if root in {".", "*"}:
            return True
        if root.endswith("/") and rel.startswith(root):
            return True
        if rel == root or rel.startswith(root + "/"):
            return True
    return False


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _protected_policy(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    policy = _load_yaml(root / "harness" / "protected_path_commit_policy.yml")
    protected = policy.get("protected_paths") if isinstance(policy, dict) else None
    exact = set(DEFAULT_PROTECTED_EXACT)
    prefixes = set(DEFAULT_PROTECTED_PREFIXES)
    if isinstance(protected, dict):
        exact.update(str(item).strip() for item in protected.get("exact") or [] if str(item).strip())
        prefixes.update(str(item).strip() for item in protected.get("prefixes") or [] if str(item).strip())
    return tuple(sorted(exact)), tuple(sorted(prefixes))


def _session_declared_writes(root: Path) -> tuple[str, ...]:
    session = _load_yaml(root / "SESSION_CONTRACT.yml")
    if not session:
        return ()
    values: list[str] = []
    for key in ["allowed_prefixes", "declared_write_roots", "declared_writes"]:
        raw = session.get(key)
        if isinstance(raw, list):
            values.extend(str(item).strip() for item in raw if str(item).strip())
    return tuple(sorted(dict.fromkeys(values)))


def _observed_writes(root: Path, since: str) -> tuple[str, ...]:
    root = root.resolve()
    diff = _run_git(root, ["diff", "--name-only", since, "--"])
    changed = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    untracked = _run_git(root, ["ls-files", "--others", "--exclude-standard"])
    changed.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
    return tuple(sorted(dict.fromkeys(_normalize(path) for path in changed if _normalize(path))))


def audit_writes(
    root: Path,
    *,
    since: str = "HEAD",
    declared_writes: list[str] | tuple[str, ...] = (),
    include_session: bool = True,
) -> WriteAuditReport:
    root = root.resolve()
    observed = _observed_writes(root, since)
    declared_values = list(declared_writes or [])
    source_files: list[str] = ["git diff --name-only", "git ls-files --others --exclude-standard"]
    if include_session:
        session_values = _session_declared_writes(root)
        if session_values:
            declared_values.extend(session_values)
            source_files.append("SESSION_CONTRACT.yml")
    declared = tuple(sorted(dict.fromkeys(_normalize(item) for item in declared_values if _normalize(item))))
    protected_exact, protected_prefixes = _protected_policy(root)
    source_files.append("harness/protected_path_commit_policy.yml")
    protected = tuple(
        path for path in observed
        if path in protected_exact or _under(path, protected_prefixes)
    )
    undeclared = tuple(
        path for path in observed
        if path not in protected and not _under(path, declared)
    )
    if not observed:
        status = "NO_WRITES"
        recommended = "No observed writes since the selected git ref. Nothing to review."
    elif protected:
        status = "FAIL"
        recommended = "Stop and request explicit protected-path review or move/revert protected writes before committing."
    elif undeclared:
        status = "REVIEW"
        recommended = "Review undeclared writes; either add an explicit declared-write root/session scope or move them out of scope."
    else:
        status = "PASS"
        recommended = "Observed writes are within declared roots and avoid protected paths. Proceed with normal checks."
    return WriteAuditReport(
        status=status,
        since=since,
        observed_writes=observed,
        declared_writes=declared,
        undeclared_writes=undeclared,
        protected_writes=protected,
        recommended_action=recommended,
        source_files=tuple(source_files),
    )


def format_write_audit(report: WriteAuditReport | dict[str, Any]) -> str:
    data = report.to_dict() if isinstance(report, WriteAuditReport) else report
    lines = [
        "# AEROS Writes Audit",
        "",
        f"status: {data.get('status')}",
        f"since: {data.get('since')}",
        f"recommended_action: {data.get('recommended_action')}",
        "",
        "## Observed Writes",
    ]
    for item in data.get("observed_writes") or []:
        lines.append(f"- {item}")
    if not data.get("observed_writes"):
        lines.append("- none")
    lines.append("")
    lines.append("## Declared Writes")
    for item in data.get("declared_writes") or []:
        lines.append(f"- {item}")
    if not data.get("declared_writes"):
        lines.append("- none")
    lines.append("")
    lines.append("## Undeclared Writes")
    for item in data.get("undeclared_writes") or []:
        lines.append(f"- {item}")
    if not data.get("undeclared_writes"):
        lines.append("- none")
    lines.append("")
    lines.append("## Protected Writes")
    for item in data.get("protected_writes") or []:
        lines.append(f"- {item}")
    if not data.get("protected_writes"):
        lines.append("- none")
    lines.append("")
    lines.append("## Does Not Prove")
    for item in data.get("does_not_prove") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Writes audit is a dry-run boundary view. It does not execute, revert, approve, or certify research substance.")
    return "\n".join(lines)


def write_write_audit(root: Path, report: WriteAuditReport | dict[str, Any]) -> tuple[Path, Path]:
    root = root.resolve()
    data = report.to_dict() if isinstance(report, WriteAuditReport) else report
    out_dir = root / "outputs" / "context"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "writes_audit.md"
    json_path = out_dir / "writes_audit.json"
    md_path.write_text(format_write_audit(data), encoding="utf-8")
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path, json_path
