"""Execution mode selector for right-sized AEROS governance.

Modes are advisory control profiles. They help choose how heavy the governance
shell should be for the next action; they do not approve gates, run tasks,
weaken checks, or certify research progress.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import subprocess

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - system python may not have PyYAML
    yaml = None


POLICY_PATH = Path("harness/execution_mode_policy.yml")

DEFAULT_MODES: dict[str, dict[str, Any]] = {
    "smoke_test": {
        "governance_shell": "light",
        "check_profile": "smoke",
        "max_provider_calls": 0,
        "max_cost_usd": 0,
        "requires_human_decision": False,
        "allowed_progress_label": "CHECK_PASS",
        "stop_condition": "Stop after fast checks or first failure.",
    },
    "bounded_probe": {
        "governance_shell": "medium",
        "check_profile": "lane:data",
        "max_provider_calls": 0,
        "max_cost_usd": 0,
        "requires_human_decision": False,
        "allowed_progress_label": "ROUTE_READY",
        "stop_condition": "Stop after one bounded probe, blocker, or queue update.",
    },
    "broad_capture": {
        "governance_shell": "light",
        "check_profile": "lane:data",
        "max_provider_calls": 0,
        "max_cost_usd": 0,
        "requires_human_decision": False,
        "allowed_progress_label": "CAPTURE_LOGGED",
        "receipt_level": "lightweight",
        "audit_level": "batch_only",
        "claim_surface": "none_by_construction",
        "promotion_required_for": ["data/intermediate", "data/processed", "canonical", "claim_registry"],
        "stop_condition": "Collect leads/queues only; stop before promotion, processed data, claims, or paper-facing outputs.",
    },
    "source_capture": {
        "governance_shell": "medium",
        "check_profile": "lane:data",
        "max_provider_calls": 0,
        "max_cost_usd": 0,
        "requires_human_decision": False,
        "allowed_progress_label": "ROUTE_READY",
        "stop_condition": "Capture staging sources only; do not promote to canonical evidence without review.",
    },
    "paper_release": {
        "governance_shell": "strict",
        "check_profile": "lane:compliance",
        "max_provider_calls": 0,
        "max_cost_usd": 0,
        "requires_human_decision": True,
        "allowed_progress_label": "DECISION_RECORDED",
        "stop_condition": "Stop at human release gate; do not assert paper-ready automatically.",
    },
    "expensive_api_run": {
        "governance_shell": "strict",
        "check_profile": "lane:data",
        "max_provider_calls": 1,
        "max_cost_usd": 1,
        "requires_human_decision": True,
        "allowed_progress_label": "ROUTE_READY",
        "stop_condition": "Stop for explicit cost/credential/source-date approval before execution.",
    },
    "waiting_on_external_input": {
        "governance_shell": "blocked",
        "check_profile": "smoke",
        "max_provider_calls": 0,
        "max_cost_usd": 0,
        "requires_human_decision": True,
        "allowed_progress_label": "ROUTE_READY",
        "stop_condition": "Do not continue running; record blocker and wait for external input.",
    },
}

DOES_NOT_PROVE = [
    "that the recommended mode is scientifically optimal",
    "that a task is complete",
    "that data access exists",
    "that a human gate is approved",
]


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / POLICY_PATH
    if not path.exists() or yaml is None:
        return {"modes": DEFAULT_MODES}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"modes": DEFAULT_MODES}


def _git_changed_files(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    out: list[str] = []
    for line in proc.stdout.splitlines():
        rel = line[3:].strip() if len(line) > 3 else ""
        if rel:
            out.append(rel)
    return out


def _has_pending_human_queue(root: Path) -> bool:
    path = root / "decisions" / "human_gate_queue.yml"
    if not path.exists() or yaml is None:
        return False
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for item in data.get("items") or []:
        if isinstance(item, dict) and str(item.get("status", "")).strip() == "pending":
            return True
    return False


def _infer_mode(root: Path, *, lane: str = "", intent: str = "") -> tuple[str, str]:
    value = f"{lane} {intent}".lower()
    if "smoke" in value:
        return "smoke_test", "intent mentions smoke"
    if any(token in value for token in ("broad search", "lead sweep", "lead queue", "candidate queue", "wide capture", "撒网", "线索")):
        return "broad_capture", "intent is early lead capture, not evidence promotion"
    if any(token in value for token in ("api", "credential", "expensive", "provider", "nielsen")):
        return "expensive_api_run", "intent mentions API/credential/cost-sensitive work"
    if any(token in value for token in ("wait", "blocked", "external", "receipt", "fulltext")) or _has_pending_human_queue(root):
        return "waiting_on_external_input", "external input or human receipt is pending"
    if any(token in value for token in ("release", "submission", "paper ready", "replication package")) or lane in {"writing", "compliance"}:
        return "paper_release", "paper/release-facing lane or intent"
    changed = _git_changed_files(root)
    if any(path.startswith(("work/recapture_", "work/chrome_review/", "source_snapshots/")) for path in changed):
        return "source_capture", "staging source capture files are present"
    if lane == "data" or any(token in value for token in ("probe", "bounded", "denominator")):
        return "bounded_probe", "data lane should start with bounded probe governance"
    return "smoke_test", "default to the lightest safe mode"


def recommend_execution_mode(root: Path, *, lane: str = "", intent: str = "", mode: str = "") -> dict[str, Any]:
    policy = _load_policy(root)
    modes = policy.get("modes") or DEFAULT_MODES
    selected = str(mode or "").strip()
    reason = "explicit mode requested"
    if not selected:
        selected, reason = _infer_mode(root, lane=lane, intent=intent)
    if selected not in modes:
        selected = "smoke_test"
        reason = "unknown requested mode; fell back to smoke_test"
    spec = dict(modes.get(selected) or {})
    return {
        "status": "ADVISORY",
        "mode": selected,
        "lane": lane or "project",
        "intent": intent,
        "reason": reason,
        "governance_shell": spec.get("governance_shell", ""),
        "check_profile": spec.get("check_profile", "smoke"),
        "max_provider_calls": int(spec.get("max_provider_calls", 0) or 0),
        "max_cost_usd": float(spec.get("max_cost_usd", 0) or 0),
        "requires_human_decision": bool(spec.get("requires_human_decision", False)),
        "allowed_progress_label": spec.get("allowed_progress_label", "CHECK_PASS"),
        "receipt_level": spec.get("receipt_level", "standard"),
        "audit_level": spec.get("audit_level", "per_action"),
        "claim_surface": spec.get("claim_surface", "possible"),
        "promotion_required_for": list(spec.get("promotion_required_for") or []),
        "stop_condition": spec.get("stop_condition", ""),
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_execution_mode(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Execution Mode",
        "",
        f"mode: {report.get('mode')}",
        f"lane: {report.get('lane')}",
        f"governance_shell: {report.get('governance_shell')}",
        f"check_profile: {report.get('check_profile')}",
        f"requires_human_decision: {str(report.get('requires_human_decision')).lower()}",
        f"max_provider_calls: {report.get('max_provider_calls')}",
        f"max_cost_usd: {report.get('max_cost_usd')}",
        f"allowed_progress_label: {report.get('allowed_progress_label')}",
        f"receipt_level: {report.get('receipt_level')}",
        f"audit_level: {report.get('audit_level')}",
        f"claim_surface: {report.get('claim_surface')}",
        f"reason: {report.get('reason')}",
        f"stop_condition: {report.get('stop_condition')}",
        "",
        "does_not_prove:",
    ]
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
