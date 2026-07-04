"""Context compiler for AEROS.

The compiler turns existing project state into a high-signal attention brief.
It is not storage, memory, evidence, or authority. It decides what should enter
the main agent context, what should remain in ledgers, and what must be treated
as noise until compressed into evidence, uncertainty, blockers, or next action.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import yaml

from .context_bundle import build_context_bundle


POLICY = "AEROS-CONTEXT-COMPILER-001"
DEFAULT_DOES_NOT_PROVE = [
    "data access",
    "full-text literature review",
    "empirical validity",
    "claim support",
    "paper readiness",
    "gate approval",
    "task completion",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_list(value: Any, *, limit: int = 5) -> list[Any]:
    if value in (None, "", {}, []):
        return []
    if isinstance(value, list):
        return value[: max(limit, 0)]
    return [value]


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / "harness/context_governance.yml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def build_context_brief(root: Path, *, lane: str = "project") -> dict[str, Any]:
    """Compile an attention brief from existing source-of-truth files."""

    root = root.resolve()
    lane = (lane or "project").strip()
    policy = _load_policy(root)
    bundle = build_context_bundle(root, lane=lane, brief=True)
    next_action = bundle.get("next_action") or {}
    staleness = bundle.get("context_staleness") or {}
    source_hashes = bundle.get("source_hashes") or {}
    source_anchors = [{"path": rel, "sha256": digest} for rel, digest in source_hashes.items()]
    recent_deltas = []
    for delta in _as_list(bundle.get("recent_evidence_deltas"), limit=int(policy.get("max_recent_deltas", 5) or 5)):
        if isinstance(delta, dict):
            recent_deltas.append({
                "delta_id": _text(delta.get("delta_id"), "?"),
                "lane": _text(delta.get("lane"), ""),
                "summary": _text(delta.get("summary"), ""),
                "judgment_implications": _text(delta.get("judgment_implications"), ""),
            })
    gate_items = []
    for item in _as_list(bundle.get("open_human_gate_items"), limit=int(policy.get("max_human_gate_items", 3) or 3)):
        if isinstance(item, dict):
            gate_items.append({
                "project": _text(item.get("project"), ""),
                "request": _text(item.get("request"), ""),
                "status": _text(item.get("status"), ""),
                "why_human_needed": _text(item.get("why_human_needed"), ""),
            })

    latest_artifact = _text(bundle.get("latest_substantive_artifact"), "None recorded.")
    blocker = _text(bundle.get("current_blocker"), "None recorded.")
    status_label = _text(next_action.get("status_label"), "ROUTE_READY")

    brief = {
        "version": "0.1",
        "policy": POLICY,
        "principle": "Context is not storage. Context is active attention allocation.",
        "generated_at": _now(),
        "project_root": str(root),
        "lane": lane,
        "goal_context": {
            "current_goal": _text(bundle.get("current_goal"), "Not recorded."),
            "acceptance_signal": _text(next_action.get("stop_condition"), _text(bundle.get("stop_rule"), "")),
            "must_not_do": [
                "do not treat route-ready work as substantive evidence",
                "do not approve gates or upgrade claims from context",
                "do not bulk-read raw outputs unless the next action requires them",
                "do not switch lanes silently when context and user request conflict",
            ],
        },
        "state_context": {
            "current_gate": _text(bundle.get("current_gate"), "G0"),
            "candidate_gate": _text(bundle.get("candidate_gate"), "G0"),
            "gate_status": _text(bundle.get("gate_status"), "open"),
            "current_blocker": blocker,
            "last_validation": _text(bundle.get("last_validation"), "Not recorded."),
            "lane_snapshot": bundle.get("lane_snapshot") or {},
        },
        "evidence_context": {
            "latest_substantive_artifact": latest_artifact,
            "recent_evidence_deltas": recent_deltas,
            "source_anchors": source_anchors[: int(policy.get("max_source_anchors", 12) or 12)],
            "evidence_rule": "Only source-anchored files, hashes, extraction cards, receipts, result records, or official artifacts may support judgments.",
        },
        "decision_context": {
            "latest_revision": _text(bundle.get("latest_revision"), ""),
            "open_human_gate_items": gate_items,
            "decision_rule": "Past decisions constrain next actions but do not certify new evidence.",
        },
        "noise_context": {
            "context_stale": bool(staleness.get("stale", False)),
            "context_stale_reason": _text(staleness.get("message"), ""),
            "files_to_read_if_needed": _as_list(bundle.get("files_to_read_if_needed"), limit=int(policy.get("max_files_to_read", 12) or 12)),
            "raw_output_policy": "Raw tool output, failed logs, broad search dumps, and temporary files stay out of main context until compressed into claims, evidence, uncertainty, blockers, or next action.",
            "excluded_by_default": [
                "raw command logs",
                "large source dumps",
                "duplicate search results",
                "failed fetch bodies",
                "unreviewed staging files",
            ],
        },
        "next_action": {
            "recommended_next_action": _text(next_action.get("recommended_next_action"), ""),
            "why_this_next": _text(next_action.get("why_this_next"), ""),
            "status_label": status_label,
            "lane": _text(next_action.get("lane"), lane),
            "command": _text(next_action.get("command"), ""),
            "stop_condition": _text(next_action.get("stop_condition"), ""),
            "blocked": bool(next_action.get("blocked", False)),
            "action_spec": next_action.get("action_spec") or {},
        },
        "attention_contract": {
            "main_context_admits": [
                "current goal and stop condition",
                "verified state summary",
                "source-anchored evidence pointers",
                "human decisions and blockers",
                "deterministic next action",
            ],
            "ledger_only": [
                "raw check output",
                "full command transcripts",
                "bulk search results",
                "intermediate failures after compression",
            ],
            "requires_reverification": [
                "stale source hashes",
                "network-derived facts",
                "official status pages",
                "claim-affecting artifacts",
            ],
        },
        "communication_budget": {
            "mode": _text((policy.get("communication_budget") or {}).get("default_mode"), "dense"),
            "principle": _text((policy.get("communication_budget") or {}).get("principle"), "Compress communication, not evidence."),
            "target": _text((policy.get("communication_budget") or {}).get("target"), "output_only"),
            "applies_to": _as_list((policy.get("communication_budget") or {}).get("applies_to"), limit=8),
            "preserve_exact": _as_list((policy.get("communication_budget") or {}).get("preserve_exact"), limit=16),
            "do_not_compress": _as_list((policy.get("communication_budget") or {}).get("do_not_compress"), limit=12),
            "risk_note": _text((policy.get("communication_budget") or {}).get("risk_note"), ""),
        },
        "does_not_prove": DEFAULT_DOES_NOT_PROVE,
    }
    return brief


def audit_context_brief(brief: dict[str, Any]) -> list[str]:
    """Return governance failures for a compiled brief."""

    failures: list[str] = []
    if brief.get("policy") != POLICY:
        failures.append("context brief has wrong policy marker")
    for key in [
        "goal_context",
        "state_context",
        "evidence_context",
        "decision_context",
        "noise_context",
        "next_action",
        "attention_contract",
        "communication_budget",
        "does_not_prove",
    ]:
        if key not in brief:
            failures.append(f"context brief missing {key}")
    principle = _text(brief.get("principle")).lower()
    if "active attention allocation" not in principle:
        failures.append("context brief missing active-attention principle")
    next_action = brief.get("next_action") or {}
    if not isinstance(next_action.get("action_spec"), dict) or not next_action.get("action_spec"):
        failures.append("context brief next_action missing ActionSpec")
    if next_action.get("status_label") in {"SUBSTANTIVE_DONE", "SUBSTANTIVE_PRODUCED"}:
        latest = ((brief.get("evidence_context") or {}).get("latest_substantive_artifact") or "").lower()
        if latest in {"", "none", "none.", "none recorded."}:
            failures.append("context brief cannot imply substantive progress without latest_substantive_artifact")
    noise = brief.get("noise_context") or {}
    raw_policy = _text(noise.get("raw_output_policy")).lower()
    if "compressed" not in raw_policy or "raw tool output" not in raw_policy:
        failures.append("context brief missing raw-output compression policy")
    communication = brief.get("communication_budget") or {}
    if _text(communication.get("target")) != "output_only":
        failures.append("context communication budget must target output_only")
    exact = {str(item).lower() for item in communication.get("preserve_exact") or []}
    for required in ["code", "commands", "errors", "hashes"]:
        if required not in exact:
            failures.append(f"context communication budget must preserve {required} exactly")
    do_not = " ".join(str(item).lower() for item in communication.get("do_not_compress") or [])
    if "source evidence" not in do_not:
        failures.append("context communication budget must not compress source evidence")
    if not brief.get("does_not_prove"):
        failures.append("context brief missing does_not_prove")
    return failures


def format_context_brief(brief: dict[str, Any]) -> str:
    """Render the compiled context brief as a short Markdown artifact."""

    goal = brief.get("goal_context") or {}
    state = brief.get("state_context") or {}
    evidence = brief.get("evidence_context") or {}
    decision = brief.get("decision_context") or {}
    noise = brief.get("noise_context") or {}
    next_action = brief.get("next_action") or {}
    attention = brief.get("attention_contract") or {}
    communication = brief.get("communication_budget") or {}
    lines = [
        "# CONTEXT_BRIEF",
        "",
        f"generated_at: {brief.get('generated_at', '')}",
        f"lane: {brief.get('lane', '')}",
        f"principle: {brief.get('principle', '')}",
        "",
        "## Goal Context",
        f"- current_goal: {goal.get('current_goal', '')}",
        f"- acceptance_signal: {goal.get('acceptance_signal', '')}",
        "- must_not_do:",
    ]
    lines.extend(f"  - {item}" for item in goal.get("must_not_do") or [])
    lines.extend([
        "",
        "## State Context",
        f"- current_gate: {state.get('current_gate', '')}",
        f"- candidate_gate: {state.get('candidate_gate', '')}",
        f"- gate_status: {state.get('gate_status', '')}",
        f"- current_blocker: {state.get('current_blocker', '')}",
        f"- last_validation: {state.get('last_validation', '')}",
        f"- lane_snapshot: {json.dumps(state.get('lane_snapshot') or {}, ensure_ascii=False)}",
        "",
        "## Evidence Context",
        f"- latest_substantive_artifact: {evidence.get('latest_substantive_artifact', '')}",
        f"- evidence_rule: {evidence.get('evidence_rule', '')}",
        "- recent_evidence_deltas:",
    ])
    deltas = evidence.get("recent_evidence_deltas") or []
    lines.extend([f"  - {item.get('delta_id', '?')}: {item.get('summary', '')}" for item in deltas] or ["  - none"])
    lines.append("- source_anchors:")
    anchors = evidence.get("source_anchors") or []
    lines.extend([f"  - {item.get('path', '')}: {item.get('sha256', '')}" for item in anchors] or ["  - none"])
    lines.extend([
        "",
        "## Decision Context",
        f"- latest_revision: {decision.get('latest_revision', '')}",
        f"- decision_rule: {decision.get('decision_rule', '')}",
        "- open_human_gate_items:",
    ])
    gates = decision.get("open_human_gate_items") or []
    lines.extend([f"  - {item.get('project', '')}: {item.get('request', '')} ({item.get('status', '')})" for item in gates] or ["  - none"])
    lines.extend([
        "",
        "## Noise Context",
        f"- context_stale: {noise.get('context_stale', False)}",
        f"- context_stale_reason: {noise.get('context_stale_reason', '')}",
        f"- raw_output_policy: {noise.get('raw_output_policy', '')}",
        "- files_to_read_if_needed:",
    ])
    lines.extend(f"  - {item}" for item in noise.get("files_to_read_if_needed") or [])
    lines.extend([
        "- excluded_by_default:",
    ])
    lines.extend(f"  - {item}" for item in noise.get("excluded_by_default") or [])
    lines.extend([
        "",
        "## Next Action",
        f"- recommended_next_action: {next_action.get('recommended_next_action', '')}",
        f"- why_this_next: {next_action.get('why_this_next', '')}",
        f"- status_label: {next_action.get('status_label', '')}",
        f"- command: {next_action.get('command', '')}",
        f"- stop_condition: {next_action.get('stop_condition', '')}",
        f"- action_spec_kind: {(next_action.get('action_spec') or {}).get('kind', '')}",
        f"- action_spec_effect_class: {(next_action.get('action_spec') or {}).get('effect_class', '')}",
        "",
        "## Attention Contract",
        "- main_context_admits:",
    ])
    lines.extend(f"  - {item}" for item in attention.get("main_context_admits") or [])
    lines.append("- ledger_only:")
    lines.extend(f"  - {item}" for item in attention.get("ledger_only") or [])
    lines.append("- requires_reverification:")
    lines.extend(f"  - {item}" for item in attention.get("requires_reverification") or [])
    lines.extend([
        "",
        "## Communication Budget",
        f"- mode: {communication.get('mode', '')}",
        f"- principle: {communication.get('principle', '')}",
        f"- target: {communication.get('target', '')}",
        "- applies_to:",
    ])
    lines.extend(f"  - {item}" for item in communication.get("applies_to") or [])
    lines.append("- preserve_exact:")
    lines.extend(f"  - {item}" for item in communication.get("preserve_exact") or [])
    lines.append("- do_not_compress:")
    lines.extend(f"  - {item}" for item in communication.get("do_not_compress") or [])
    lines.extend([
        f"- risk_note: {communication.get('risk_note', '')}",
        "",
        "## Does Not Prove",
    ])
    lines.extend(f"- {item}" for item in brief.get("does_not_prove") or [])
    lines.append("")
    lines.append("This brief is compiled context, not storage, evidence, completion, gate approval, or claim support.")
    return "\n".join(lines) + "\n"


def write_context_brief(root: Path, brief: dict[str, Any]) -> tuple[Path, Path]:
    md_path = root / "CONTEXT_BRIEF.md"
    json_path = root / "outputs/context/context_brief.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(format_context_brief(brief), encoding="utf-8")
    json_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path, json_path
