"""AEROS cockpit: one compact terminal dashboard for daily work."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .context_bundle import build_context_bundle, format_context_bundle, write_context_bundle
from .context_graph import build_context_graph, write_context_graph
from .milestones import format_simple_status


def build_cockpit(root: Path, *, lane: str = "project", check_profile: str = "smoke") -> dict[str, Any]:
    root = root.resolve()
    bundle = build_context_bundle(root, lane=lane, brief=True)
    graph = build_context_graph(root, lane=lane)
    next_action = bundle.get("next_action") or {}
    return {
        "version": "0.1",
        "policy": "AEROS-COCKPIT-001",
        "project_root": str(root),
        "lane": bundle.get("lane", lane),
        "milestone_status": format_simple_status(root),
        "context": bundle,
        "context_graph_summary": {
            "nodes": len(graph.get("nodes") or []),
            "edges": len(graph.get("edges") or []),
        },
        "next_action": next_action,
        "fast_check_command": f"python3 checks/run_harness_checks.py --profile {check_profile} --timeout 20",
        "does_not_prove": [
            "substantive progress",
            "gate approval",
            "claim support",
            "full harness pass",
            "paper readiness",
        ],
    }


def format_cockpit(cockpit: dict[str, Any]) -> str:
    context = cockpit.get("context") or {}
    next_action = cockpit.get("next_action") or {}
    stale = context.get("context_staleness") or {}
    lines = [
        "# AEROS COCKPIT",
        "",
        f"lane: {cockpit.get('lane', '')}",
        f"current_gate: {context.get('current_gate', '')}",
        f"candidate_gate: {context.get('candidate_gate', '')}",
        f"gate_status: {context.get('gate_status', '')}",
        f"status_label: {next_action.get('status_label', '')}",
        f"context_stale: {stale.get('stale', False)} ({stale.get('status', 'unknown')})",
        f"context_graph: {cockpit.get('context_graph_summary', {}).get('nodes', 0)} node(s), {cockpit.get('context_graph_summary', {}).get('edges', 0)} edge(s)",
        "",
        "## Recommended Next",
        f"action: {next_action.get('recommended_next_action', '')}",
        f"why: {next_action.get('why_this_next', '')}",
        f"command: {next_action.get('command', '')}",
        f"stop: {next_action.get('stop_condition', '')}",
        "",
        "## Fast Check",
        cockpit.get("fast_check_command", ""),
        "",
        "## Current Context",
        format_context_bundle(context, brief=True),
        "",
        "## Does Not Prove",
    ]
    for item in cockpit.get("does_not_prove") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Cockpit is a navigation view. It does not execute, approve, or certify research substance.")
    return "\n".join(lines)


def write_cockpit(root: Path, *, lane: str = "project", check_profile: str = "smoke") -> tuple[Path, Path, Path]:
    cockpit = build_cockpit(root, lane=lane, check_profile=check_profile)
    md_path = root / "outputs/context/cockpit.md"
    json_path = root / "outputs/context/cockpit.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(format_cockpit(cockpit), encoding="utf-8")
    json_path.write_text(json.dumps(cockpit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    bundle_path, _ = write_context_bundle(root, cockpit["context"])
    graph_path = write_context_graph(root, lane=lane)
    return md_path, bundle_path, graph_path
