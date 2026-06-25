"""Lightweight derived context graph for AEROS cockpit/navigation.

This is not the research graph. It is a small context index that connects the
current gate, lane, blocker, next action, recent deltas, and human-gate queue so
agents can orient quickly without rereading long logs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import yaml

from .context_bundle import build_context_bundle


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _node(node_id: str, node_type: str, label: str, **attrs: Any) -> dict[str, Any]:
    data = {"id": node_id, "type": node_type, "label": label}
    data.update({k: v for k, v in attrs.items() if v not in (None, "", [], {})})
    return data


def _edge(source: str, target: str, relation: str, **attrs: Any) -> dict[str, Any]:
    data = {"source": source, "target": target, "relation": relation}
    data.update({k: v for k, v in attrs.items() if v not in (None, "", [], {})})
    return data


def build_context_graph(root: Path, *, lane: str = "project") -> dict[str, Any]:
    root = root.resolve()
    bundle = build_context_bundle(root, lane=lane, brief=True)
    next_action = bundle.get("next_action") or {}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    nodes.append(_node("project", "project", root.name, path=str(root)))
    lane_id = f"lane:{bundle.get('lane', 'project')}"
    nodes.append(_node(lane_id, "lane", str(bundle.get("lane", "project"))))
    edges.append(_edge("project", lane_id, "lane_focus"))

    current_gate = str(bundle.get("current_gate", "G0"))
    candidate_gate = str(bundle.get("candidate_gate", "G0"))
    current_gate_id = f"gate:{current_gate}"
    candidate_gate_id = f"gate:{candidate_gate}"
    nodes.append(_node(current_gate_id, "gate", current_gate, status=bundle.get("gate_status", "open")))
    if candidate_gate_id != current_gate_id:
        nodes.append(_node(candidate_gate_id, "gate", candidate_gate, status="candidate"))
    edges.append(_edge("project", current_gate_id, "current_gate"))
    edges.append(_edge("project", candidate_gate_id, "candidate_gate"))

    nodes.append(_node(
        "next_action",
        "next_action",
        str(next_action.get("recommended_next_action", "")),
        lane=next_action.get("lane", ""),
        status_label=next_action.get("status_label", ""),
        command=next_action.get("command", ""),
        blocked=bool(next_action.get("blocked")),
    ))
    edges.append(_edge(lane_id, "next_action", "recommends"))

    blocker = str(bundle.get("current_blocker", "")).strip()
    if blocker and blocker.lower() not in {"none", "none.", "not recorded", ""}:
        nodes.append(_node("blocker:current", "blocker", blocker))
        edges.append(_edge("next_action", "blocker:current", "blocked_by"))

    artifact = str(bundle.get("latest_substantive_artifact", "")).strip()
    if artifact and artifact.lower() not in {"none", "none.", "none yet.", ""}:
        artifact_id = "artifact:" + artifact
        nodes.append(_node(artifact_id, "artifact_pointer", artifact))
        edges.append(_edge("project", artifact_id, "mentions"))

    for idx, item in enumerate(bundle.get("open_human_gate_items") or [], 1):
        node_id = f"human_gate:{idx}"
        label = str(item.get("request", "human gate item"))
        nodes.append(_node(node_id, "human_gate_item", label, status=item.get("status", ""), project=item.get("project", "")))
        edges.append(_edge("project", node_id, "blocked_by"))

    for idx, delta in enumerate(bundle.get("recent_evidence_deltas") or [], 1):
        delta_id = str(delta.get("delta_id") or f"delta:{idx}")
        node_id = f"evidence_delta:{delta_id}"
        nodes.append(_node(node_id, "evidence_delta", str(delta.get("summary", delta_id)), lane=delta.get("lane", "")))
        edges.append(_edge("project", node_id, "recent_delta"))

    return {
        "version": "0.1",
        "policy": "AEROS-CONTEXT-GRAPH-001",
        "generated_at": _now(),
        "project_root": str(root),
        "lane": bundle.get("lane", lane),
        "source_bundle_generated_at": bundle.get("generated_at", ""),
        "nodes": nodes,
        "edges": edges,
        "does_not_prove": [
            "research graph support",
            "claim support",
            "gate approval",
            "substantive progress",
            "task completion",
        ],
    }


def write_context_graph(root: Path, *, lane: str = "project") -> Path:
    graph = build_context_graph(root, lane=lane)
    path = root / "outputs/context/context_graph.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(graph, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def format_context_graph(graph: dict[str, Any]) -> str:
    lines = [
        "# CONTEXT_GRAPH",
        "",
        f"generated_at: {graph.get('generated_at', '')}",
        f"lane: {graph.get('lane', '')}",
        f"nodes: {len(graph.get('nodes') or [])}",
        f"edges: {len(graph.get('edges') or [])}",
        "",
        "## Nodes",
    ]
    for node in graph.get("nodes") or []:
        lines.append(f"- {node.get('id')} [{node.get('type')}]: {node.get('label', '')}")
    lines.extend(["", "## Edges"])
    for edge in graph.get("edges") or []:
        lines.append(f"- {edge.get('source')} --{edge.get('relation')}--> {edge.get('target')}")
    lines.append("")
    lines.append("This is a context/navigation graph, not the research evidence graph.")
    return "\n".join(lines)


def graph_to_json(graph: dict[str, Any]) -> str:
    return json.dumps(graph, indent=2, ensure_ascii=False)
