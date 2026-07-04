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
    changed_artifacts: list[dict[str, str]]
    verdict: str
    issues: list[str]

    @property
    def ok(self) -> bool:
        if not self.active:
            return True
        return not self.issues and self.verdict in {"no_changes", "bookkeeping_only", "expected_lane_change", "supporting_cross_lane_change"}


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
        "evidence/delta_log.jsonl",
        "aeros/state/global_state.yml",
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
        "workflow_presets": {
            "recapture_source_pool": {
                "description": "Recover and review candidate source pools without promoting them to canonical evidence.",
                "allowed_prefixes": [
                    "work/recapture_",
                    "audits/source_recapture/",
                    "quality_reports/source_recapture/",
                    "source_snapshots/",
                    "evidence/delta_log.jsonl",
                ],
                "allowed_actions": ["source recapture", "chrome-assisted review", "source-promotion queue"],
                "forbidden_prefixes": ["evidence/claim_registry.md", "decisions/approvals/"],
            },
            "claim_audit": {
                "description": "Audit claim support and deltas without collecting new raw data.",
                "allowed_prefixes": [
                    "audits/claim/",
                    "audits/advisory/",
                    "evidence/research_graph.yml",
                    "evidence/delta_log.jsonl",
                    "quality_reports/claim_audit/",
                ],
                "allowed_actions": ["claim audit", "support-chain review", "delta audit"],
                "forbidden_prefixes": ["data/raw/", "decisions/approvals/"],
            },
            "writing_guardrail": {
                "description": "Bounded paper/TeX edits and guardrail reports tied to existing claims and numbers.",
                "allowed_prefixes": [
                    "paper/",
                    "output/tex/",
                    "outputs/tex/",
                    "quality_reports/writing/",
                    "audits/writing/",
                    "evidence/delta_log.jsonl",
                ],
                "allowed_actions": ["bounded writing edit", "number/claim guardrail", "tex compile review"],
                "forbidden_prefixes": ["data/raw/", "evidence/claim_registry.md", "decisions/approvals/"],
            },
            "chrome_assisted_review": {
                "description": "Browser-assisted source review that produces staging notes, screenshots, or queues.",
                "allowed_prefixes": [
                    "work/chrome_review/",
                    "work/recapture_",
                    "audits/chrome_assisted_review/",
                    "quality_reports/chrome_assisted_review/",
                    "source_snapshots/",
                    "evidence/delta_log.jsonl",
                ],
                "allowed_actions": ["chrome-assisted review", "source locator check", "manual page audit"],
                "forbidden_prefixes": ["evidence/claim_registry.md", "decisions/approvals/"],
            },
            "source_promotion_queue": {
                "description": "Promote reviewed staging sources into explicit queues without claiming final evidence.",
                "allowed_prefixes": [
                    "work/source_promotion/",
                    "audits/source_promotion/",
                    "quality_reports/source_promotion/",
                    "data/backfill/",
                    "discovery/data_inventory.csv",
                    "docs/data_sources.md",
                    "evidence/delta_log.jsonl",
                    "aeros/state/global_state.yml",
                ],
                "allowed_actions": ["source promotion queue", "backfill queue update", "global state refresh"],
                "forbidden_prefixes": ["paper/", "evidence/claim_registry.md", "decisions/approvals/"],
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
    workflow: str = "",
    max_actions: int = 2,
    allowed_actions: list[str] | None = None,
    dry_run: bool = False,
) -> tuple[Path, dict[str, Any]]:
    if lane not in LANES:
        raise ValueError(f"unknown lane: {lane}")
    policy = load_policy(project_root)
    lane_policy = (policy.get("lanes") or {}).get(lane) or {}
    workflow = str(workflow or "").strip()
    workflow_policy = {}
    if workflow:
        workflow_policy = ((policy.get("workflow_presets") or {}).get(workflow) or {})
        if not workflow_policy:
            known = ", ".join(sorted((policy.get("workflow_presets") or {}).keys()))
            raise ValueError(f"unknown workflow preset: {workflow}; known presets: {known}")

    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            value = str(item or "").strip()
            if value and value not in seen:
                seen.add(value)
                out.append(value)
        return out

    default_actions = ["aeros cockpit", "aeros next", "lane-scoped action"]
    merged_actions = _dedupe(
        list(allowed_actions or default_actions)
        + list(workflow_policy.get("allowed_actions") or [])
    )
    merged_allowed = _dedupe(
        list(policy.get("common_allowed_prefixes") or [])
        + list(lane_policy.get("allowed_prefixes") or [])
        + list(workflow_policy.get("allowed_prefixes") or [])
    )
    merged_forbidden = _dedupe(
        list(lane_policy.get("forbidden_prefixes") or [])
        + list(workflow_policy.get("forbidden_prefixes") or [])
    )
    payload = {
        "version": "0.1",
        "policy": "AEROS-SESSION-SCOPE-001",
        "active": True,
        "started_at": _now(),
        "active_lane": lane,
        "active_workflow": workflow,
        "workflow_description": str(workflow_policy.get("description", "") or ""),
        "objective": objective,
        "max_actions": max(1, int(max_actions or 1)),
        "allowed_actions": merged_actions,
        "allowed_prefixes": merged_allowed,
        "forbidden_prefixes": merged_forbidden,
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


def _classify_artifact(rel: str, active_lane: str, allowed: bool, forbidden: bool) -> dict[str, str]:
    if rel.startswith(("aeros/", "checks/", "harness/", "templates/", "tools/")) or rel in {"AGENTS.md", "project_manifest.yml"}:
        owner_lane = "aeros-dev"
        artifact_type = "harness_control"
    elif rel == "aeros/state/global_state.yml":
        owner_lane = "bookkeeping"
        artifact_type = "derived_state_view"
        semantic_class = "bookkeeping_only" if allowed else "scope_drift"
    elif rel == "evidence/delta_log.jsonl":
        owner_lane = "bookkeeping"
        artifact_type = "evidence_delta_log"
        semantic_class = "bookkeeping_only" if allowed else "scope_drift"
    elif rel.startswith("work/"):
        owner_lane = active_lane if allowed else "staging"
        artifact_type = "staging_artifact"
    elif rel.startswith("quality_reports/"):
        owner_lane = active_lane if allowed else "analysis"
        artifact_type = "quality_report"
    elif rel.startswith("audits/"):
        owner_lane = active_lane if allowed else "claim"
        artifact_type = "audit_artifact"
    elif rel.startswith(("output/tex/", "outputs/tex/")):
        owner_lane = "paper"
        artifact_type = "tex_artifact"
    elif rel.startswith(("data/", "docs/data")) or rel.startswith("discovery/data"):
        owner_lane = "data"
        artifact_type = "data_artifact"
    elif rel.startswith("discovery/literature/") or rel.startswith("docs/related_work"):
        owner_lane = "literature"
        artifact_type = "literature_artifact"
    elif rel.startswith(("code/04_analysis/", "code/05_robustness/", "code/06_tables/", "code/07_figures/", "outputs/tables/", "outputs/figures/", "outputs/model_outputs/")):
        owner_lane = "analysis"
        artifact_type = "analysis_artifact"
    elif rel.startswith("paper/"):
        owner_lane = "paper"
        artifact_type = "paper_artifact"
    elif rel.startswith("replication/") or rel.startswith("compliance/") or "data_availability" in rel:
        owner_lane = "compliance"
        artifact_type = "compliance_artifact"
    elif rel.startswith("evidence/claim_registry"):
        owner_lane = "claim"
        artifact_type = "claim_registry"
    elif rel.startswith("evidence/") or rel.startswith("outputs/.provenance/"):
        owner_lane = "claim"
        artifact_type = "evidence_or_result_artifact"
    elif rel.startswith(("agent_runs/", "outputs/logs/", "outputs/context/", "decisions/revision_log.md", "decisions/update_ledger.md")) or rel in {"SESSION_CONTRACT.yml", "CURRENT_STATE.md", "NEXT_ACTION.md", "CONTEXT_BUNDLE.md"}:
        owner_lane = "bookkeeping"
        artifact_type = "bookkeeping"
    elif rel.startswith("decisions/"):
        owner_lane = "authority"
        artifact_type = "decision_artifact"
    else:
        owner_lane = "unknown"
        artifact_type = "unknown"

    authority_risk = "none"
    semantic_class = "expected_lane_change" if allowed else "scope_drift"
    if artifact_type == "bookkeeping":
        semantic_class = "bookkeeping_only" if allowed else "scope_drift"
    if owner_lane not in {active_lane, "bookkeeping"} and allowed:
        semantic_class = "supporting_cross_lane_change"
    if forbidden:
        semantic_class = "scope_drift"
    if artifact_type in {"claim_registry"}:
        authority_risk = "claim"
        semantic_class = "authority_drift" if active_lane != "claim" else semantic_class
    elif artifact_type == "decision_artifact":
        authority_risk = "gate_or_decision"
        semantic_class = "authority_drift"
    elif artifact_type == "paper_artifact" and active_lane not in {"writing", "harness"}:
        authority_risk = "claim_language"
        semantic_class = "claim_scope_drift"
    elif owner_lane == "aeros-dev" and active_lane != "harness":
        authority_risk = "runtime"
        semantic_class = "authority_drift"

    return {
        "path": rel,
        "owner_lane": owner_lane,
        "artifact_type": artifact_type,
        "semantic_class": semantic_class,
        "authority_risk": authority_risk,
        "allowed_by_session_scope": str(bool(allowed and not forbidden)).lower(),
    }


def _verdict(changed_artifacts: list[dict[str, str]], issues: list[str]) -> str:
    if issues:
        return "inspection_failed"
    if not changed_artifacts:
        return "no_changes"
    classes = {item["semantic_class"] for item in changed_artifacts}
    if "authority_drift" in classes:
        return "AUTHORITY_DRIFT"
    if "claim_scope_drift" in classes:
        return "CLAIM_SCOPE_DRIFT"
    if "scope_drift" in classes:
        return "SCOPE_DRIFT"
    if classes == {"bookkeeping_only"}:
        return "bookkeeping_only"
    if "supporting_cross_lane_change" in classes:
        return "supporting_cross_lane_change"
    return "expected_lane_change"


def audit_session(project_root: Path) -> SessionAudit:
    session = load_session(project_root)
    if not session or not session.get("active", False):
        return SessionAudit(False, "", "", [], [], [], [], "inactive", [])
    lane = str(session.get("active_lane") or "")
    objective = str(session.get("objective") or "")
    allowed = [str(p) for p in session.get("allowed_prefixes") or [] if str(p)]
    forbidden = [str(p) for p in session.get("forbidden_prefixes") or [] if str(p)]
    changed, issues = _git_changed_files(project_root)
    allowed_files: list[str] = []
    off_scope: list[str] = []
    changed_artifacts: list[dict[str, str]] = []
    for rel in changed:
        forbidden_match = _matches(rel, forbidden)
        allowed_match = _matches(rel, allowed)
        if forbidden_match:
            off_scope.append(rel)
        elif allowed_match:
            allowed_files.append(rel)
        else:
            off_scope.append(rel)
        changed_artifacts.append(_classify_artifact(rel, lane, allowed_match, forbidden_match))
    return SessionAudit(True, lane, objective, changed, allowed_files, off_scope, changed_artifacts, _verdict(changed_artifacts, issues), issues)


def format_session_status(session: dict[str, Any]) -> str:
    if not session:
        return "No active SESSION_CONTRACT.yml. Start one with `aeros session start --lane ... --objective ...`.\n"
    lines = [
        "# AEROS Session",
        "",
        f"active: {session.get('active', False)}",
        f"active_lane: {session.get('active_lane', '')}",
        f"active_workflow: {session.get('active_workflow', '')}",
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
            "changed_artifacts": audit.changed_artifacts,
            "verdict": audit.verdict,
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
        f"status: {'PASS' if audit.ok else audit.verdict}",
        f"verdict: {audit.verdict}",
        "",
        "changed_artifacts:",
    ]
    if audit.changed_artifacts:
        for item in audit.changed_artifacts:
            lines.append(
                f"- {item['path']} "
                f"(owner_lane={item['owner_lane']}, type={item['artifact_type']}, "
                f"class={item['semantic_class']}, authority_risk={item['authority_risk']})"
            )
    else:
        lines.append("- none")
    lines.extend([
        "",
        "allowed_changed_files:",
    ])
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
