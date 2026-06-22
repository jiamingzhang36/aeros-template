"""Session scope guard for AEROS chat-driven work.

The guard records the active lane/objective and audits the current diff against
lane-scoped file boundaries. It does not execute work, approve gates, revert
files, or decide research validity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
from typing import Any

import yaml


SESSION_PATH = Path("SESSION_CONTRACT.yml")
POLICY_PATH = Path("harness/session_scope.yml")

LANES = ("data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness")

DOES_NOT_PROVE = [
    "that any task is complete",
    "that any research artifact is valid",
    "that a claim is supported",
    "that a human gate is approved",
    "that off-scope changes are acceptable",
]


@dataclass(frozen=True)
class SessionAudit:
    active: bool
    lane: str
    objective: str
    changed_files: list[str]
    allowed_files: list[str]
    off_scope_files: list[str]
    issues: list[str]

    @property
    def ok(self) -> bool:
        return not self.issues and not self.off_scope_files


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def default_policy() -> dict[str, Any]:
    common = [
        "SESSION_CONTRACT.yml",
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "CONTEXT_BUNDLE.md",
        "agent_runs/",
        "outputs/logs/",
        "outputs/context/",
        "decisions/revision_log.md",
        "decisions/update_ledger.md",
        "harness/improvement_backlog.yml",
    ]
    return {
        "version": "0.1",
        "policy": "AEROS-SESSION-SCOPE-001",
        "common_allowed_prefixes": common,
        "lanes": {
            "data": {
                "allowed_prefixes": [
                    "data/",
                    "discovery/data_inventory.csv",
                    "discovery/feasibility_matrix.md",
                    "docs/data_contract.yml",
                    "docs/data_dictionary.md",
                    "docs/data_sources.md",
                    "code/00_setup/",
                    "code/01_ingest/",
                    "code/02_clean/",
                    "code/03_construct/",
                    "data/backfill/",
                ],
                "forbidden_prefixes": ["paper/", "discovery/literature/", "evidence/claim_registry.md"],
            },
            "literature": {
                "allowed_prefixes": ["discovery/literature/", "docs/related_work", "paper/references"],
                "forbidden_prefixes": ["data/raw/", "data/clean/", "evidence/claim_registry.md", "paper/draft"],
            },
            "method": {
                "allowed_prefixes": ["design/", "docs/method", "code/04_analysis/", "code/05_robustness/", "templates/estimand", "evidence/estimand"],
                "forbidden_prefixes": ["data/raw/", "paper/draft", "evidence/claim_registry.md"],
            },
            "analysis": {
                "allowed_prefixes": [
                    "code/04_analysis/",
                    "code/05_robustness/",
                    "code/06_tables/",
                    "code/07_figures/",
                    "outputs/tables/",
                    "outputs/figures/",
                    "outputs/model_outputs/",
                    "evidence/result_index.csv",
                    "evidence/result_registry.csv",
                    "outputs/.provenance/",
                ],
                "forbidden_prefixes": ["paper/draft", "evidence/claim_registry.md"],
            },
            "claim": {
                "allowed_prefixes": ["evidence/", "audits/", "decisions/gates/", "docs/design/falsification"],
                "forbidden_prefixes": ["data/raw/", "paper/draft"],
            },
            "writing": {
                "allowed_prefixes": ["paper/", "docs/", "outputs/tables/", "outputs/figures/"],
                "forbidden_prefixes": ["data/raw/", "evidence/claim_registry.md"],
            },
            "compliance": {
                "allowed_prefixes": ["replication/", "compliance/", "docs/data_availability", "paper/supplement", "outputs/logs/"],
                "forbidden_prefixes": ["data/raw/", "evidence/claim_registry.md"],
            },
            "harness": {
                "allowed_prefixes": ["aeros/", "checks/", "harness/", "templates/", "tools/", "docs/design/", "project_manifest.yml", "AGENTS.md"],
                "forbidden_prefixes": ["data/raw/", "paper/draft.md", "evidence/claim_registry.md"],
            },
        },
    }


def load_policy(project_root: Path) -> dict[str, Any]:
    policy = _load_yaml(project_root / POLICY_PATH)
    return policy if policy else default_policy()


def load_session(project_root: Path) -> dict[str, Any]:
    return _load_yaml(project_root / SESSION_PATH)


def start_session(
    project_root: Path,
    *,
    lane: str,
    objective: str,
    max_actions: int = 2,
    allowed_actions: list[str] | None = None,
    dry_run: bool = False,
) -> tuple[Path, dict[str, Any]]:
    if lane not in LANES:
        raise ValueError(f"unknown lane: {lane}")
    policy = load_policy(project_root)
    lane_policy = (policy.get("lanes") or {}).get(lane) or {}
    payload = {
        "version": "0.1",
        "policy": "AEROS-SESSION-SCOPE-001",
        "active": True,
        "started_at": _now(),
        "active_lane": lane,
        "objective": objective,
        "max_actions": max(1, int(max_actions or 1)),
        "allowed_actions": allowed_actions or ["aeros cockpit", "aeros next", "lane-scoped action"],
        "allowed_prefixes": list(policy.get("common_allowed_prefixes") or []) + list(lane_policy.get("allowed_prefixes") or []),
        "forbidden_prefixes": list(lane_policy.get("forbidden_prefixes") or []),
        "stop_condition": "Stop at human gate, blocker, no-progress, max_actions, or first off-scope diff.",
        "completion_label_rule": "Use CHECK_PASS, ROUTE_READY, or SUBSTANTIVE_PRODUCED.",
        "does_not_prove": DOES_NOT_PROVE,
    }
    path = project_root / SESSION_PATH
    if not dry_run:
        path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path, payload


def _git_changed_files(project_root: Path) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    changed: set[str] = set()
    commands = [
        ["git", "diff", "--name-only", "HEAD", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    for argv in commands:
        try:
            proc = subprocess.run(argv, cwd=project_root, text=True, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            issues.append(f"could not inspect git changes via {' '.join(argv)}: {exc}")
            continue
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            issues.append(f"git change inspection failed via {' '.join(argv)}: {msg}")
            continue
        for line in proc.stdout.splitlines():
            rel = line.strip()
            if rel:
                changed.add(rel)
    return sorted(changed), issues


def _matches(rel: str, prefixes: list[str]) -> bool:
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in prefixes)


def audit_session(project_root: Path) -> SessionAudit:
    session = load_session(project_root)
    if not session or not session.get("active", False):
        return SessionAudit(False, "", "", [], [], [], [])
    lane = str(session.get("active_lane") or "")
    objective = str(session.get("objective") or "")
    allowed = [str(p) for p in session.get("allowed_prefixes") or [] if str(p)]
    forbidden = [str(p) for p in session.get("forbidden_prefixes") or [] if str(p)]
    changed, issues = _git_changed_files(project_root)
    allowed_files: list[str] = []
    off_scope: list[str] = []
    for rel in changed:
        if _matches(rel, forbidden):
            off_scope.append(rel)
        elif _matches(rel, allowed):
            allowed_files.append(rel)
        else:
            off_scope.append(rel)
    return SessionAudit(True, lane, objective, changed, allowed_files, off_scope, issues)


def format_session_status(session: dict[str, Any]) -> str:
    if not session:
        return "No active SESSION_CONTRACT.yml. Start one with `aeros session start --lane ... --objective ...`.\n"
    lines = [
        "# AEROS Session",
        "",
        f"active: {session.get('active', False)}",
        f"active_lane: {session.get('active_lane', '')}",
        f"objective: {session.get('objective', '')}",
        f"max_actions: {session.get('max_actions', '')}",
        f"stop_condition: {session.get('stop_condition', '')}",
        "",
        "does_not_prove:",
    ]
    for item in session.get("does_not_prove") or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def format_audit(audit: SessionAudit, *, as_json: bool = False) -> str:
    if as_json:
        return json.dumps({
            "active": audit.active,
            "lane": audit.lane,
            "objective": audit.objective,
            "changed_files": audit.changed_files,
            "allowed_files": audit.allowed_files,
            "off_scope_files": audit.off_scope_files,
            "issues": audit.issues,
            "ok": audit.ok,
        }, indent=2, ensure_ascii=False) + "\n"
    if not audit.active:
        return "No active session; scope audit skipped.\n"
    lines = [
        "# AEROS Session Scope Audit",
        "",
        f"lane: {audit.lane}",
        f"objective: {audit.objective}",
        f"status: {'PASS' if audit.ok else 'SCOPE_DRIFT'}",
        "",
        "allowed_changed_files:",
    ]
    lines.extend([f"- {rel}" for rel in audit.allowed_files] or ["- none"])
    lines.append("")
    lines.append("off_scope_files:")
    lines.extend([f"- {rel}" for rel in audit.off_scope_files] or ["- none"])
    if audit.issues:
        lines.append("")
        lines.append("inspection_issues:")
        lines.extend(f"- {issue}" for issue in audit.issues)
    lines.extend(["", "does_not_prove: scope audit does not approve gates, revert files, or certify research substance."])
    return "\n".join(lines) + "\n"
