"""Compact context bundle generation for AEROS agents.

`aeros context` is a deterministic context assembly layer. It compresses the
current project situation into a small, auditable bundle so agents do not have
to rediscover state from a long chat or blindly read many files.

It does not execute tasks, approve gates, certify claims, or replace checks.
"""
from __future__ import annotations

from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .next_action import compute_next_action


DEFAULT_DOES_NOT_PROVE = (
    "This context bundle does not prove data access, full-text literature review, "
    "empirical validity, claim support, paper readiness, or gate approval."
)

LANE_READS = {
    "data": [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "data/data_state.yml",
        "data/data_gap_plan.yml",
        "discovery/data_inventory.csv",
        "audits/data_probe_report.md",
    ],
    "literature": [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "discovery/literature/search_log.csv",
        "discovery/literature/paper_registry.csv",
        "discovery/literature/citation_audit.md",
        "discovery/literature/extraction_cards/",
        "discovery/literature/synthesis/",
    ],
    "method": [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "docs/method_card.md",
        "templates/estimand_card.yml",
        "templates/spec_run_index.csv",
        "harness/econ_method_advisory_policy.yml",
    ],
    "analysis": [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "evidence/result_registry.csv",
        "evidence/result_index.csv",
        "outputs/.provenance/",
    ],
    "claim": [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "evidence/claim_registry.md",
        "evidence/research_graph.yml",
        "discovery/literature/citation_audit.md",
    ],
    "writing": [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "paper/draft.md",
        "paper/numbers.yml",
        "evidence/claim_registry.md",
    ],
    "compliance": [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "replication/aea_data_package_manifest.yml",
        "audits/aea_replication_alignment.md",
        "decisions/human_gate_queue.yml",
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    if not path.exists() or path.is_dir():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or path.is_dir():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists() or path.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows[-max(limit, 0):]


def _csv_count(path: Path) -> int:
    if not path.exists() or path.is_dir():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for row in csv.DictReader(handle) if any(str(v).strip() for v in row.values()))


def _sha256(path: Path) -> str:
    if not path.exists() or path.is_dir():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_sources(root: Path, paths: list[str], *, max_hashes: int = 0) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in paths:
        path = root / rel
        if path.exists() and path.is_file():
            out[rel] = _sha256(path)
            if max_hashes and len(out) >= max_hashes:
                break
    return out


def _context_staleness(root: Path, lane: str, current_hashes: dict[str, str]) -> dict[str, Any]:
    previous_path = root / "outputs/context/context_bundle.json"
    if not previous_path.exists():
        return {
            "status": "not_written",
            "stale": False,
            "message": "No written context bundle exists yet; run `aeros context --write` or `aeros cockpit --write` when you want a reusable bundle.",
            "changed_sources": [],
        }
    try:
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "unreadable_previous_bundle",
            "stale": True,
            "message": "Previous context bundle could not be read; regenerate it before relying on it.",
            "changed_sources": [],
        }
    previous_hashes = previous.get("source_hashes") or {}
    previous_lane = str(previous.get("lane", "project"))
    changed = sorted(
        rel for rel, digest in current_hashes.items()
        if previous_hashes.get(rel) and previous_hashes.get(rel) != digest
    )
    added = sorted(rel for rel in current_hashes if rel not in previous_hashes)
    removed = sorted(rel for rel in previous_hashes if rel not in current_hashes)
    lane_changed = previous_lane != lane
    stale = bool(changed or removed or lane_changed)
    status = "stale" if stale else "fresh"
    if lane_changed and not changed and not removed:
        status = "different_lane"
    return {
        "status": status,
        "stale": stale,
        "previous_generated_at": previous.get("generated_at", ""),
        "previous_lane": previous_lane,
        "changed_sources": changed,
        "added_sources": added,
        "removed_sources": removed,
        "message": "Context source hashes changed; regenerate before relying on old bundle." if stale else "Written context bundle matches current source hashes for this lane.",
    }


def _parse_current_state(root: Path) -> dict[str, str]:
    text = _read_text(root / "CURRENT_STATE.md")
    out: dict[str, str] = {}
    for raw in text.splitlines():
        if ":" not in raw or raw.lstrip().startswith("#"):
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        if key in {
            "current_goal",
            "latest_substantive_artifact",
            "current_blocker",
            "next_command",
            "does_not_prove",
            "last_validation",
        }:
            out[key] = value.strip().strip("`")
    return out


def _latest_revision(root: Path) -> str:
    text = _read_text(root / "decisions/revision_log.md")
    for line in text.splitlines():
        if line.startswith("| 20"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 6:
                return f"{cells[1]} {cells[3]}: {cells[5]}"
    return ""


def _human_gate_summary(root: Path, limit: int) -> list[dict[str, str]]:
    data = _read_yaml(root / "decisions/human_gate_queue.yml")
    rows = []
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).strip() in {"pending", "blocked"}:
            rows.append({
                "project": str(item.get("project", "")),
                "request": str(item.get("request", "")),
                "why_human_needed": str(item.get("why_human_needed", "")),
                "status": str(item.get("status", "")),
            })
    return rows[:max(limit, 0)]


def _lane_snapshot(root: Path, lane: str) -> dict[str, Any]:
    if lane == "data":
        return {
            "inventory_rows": _csv_count(root / "discovery/data_inventory.csv"),
            "has_data_state": (root / "data/data_state.yml").exists(),
            "has_gap_plan": (root / "data/data_gap_plan.yml").exists(),
            "has_probe_report": (root / "audits/data_probe_report.md").exists(),
        }
    if lane == "literature":
        return {
            "search_log_rows": _csv_count(root / "discovery/literature/search_log.csv"),
            "paper_registry_rows": _csv_count(root / "discovery/literature/paper_registry.csv"),
            "snowball_queue_rows": _csv_count(root / "discovery/literature/citation_snowball_queue.csv"),
            "extraction_cards": len(list((root / "discovery/literature/extraction_cards").glob("*.md"))) if (root / "discovery/literature/extraction_cards").exists() else 0,
        }
    if lane == "method":
        return {
            "has_method_card": (root / "docs/method_card.md").exists(),
            "has_econ_method_policy": (root / "harness/econ_method_advisory_policy.yml").exists(),
            "spec_run_template_exists": (root / "templates/spec_run_index.csv").exists(),
        }
    if lane == "claim":
        return {
            "has_claim_registry": (root / "evidence/claim_registry.md").exists(),
            "has_research_graph": (root / "evidence/research_graph.yml").exists(),
        }
    if lane == "writing":
        return {
            "has_paper_draft": (root / "paper/draft.md").exists(),
            "has_number_registry": (root / "paper/numbers.yml").exists(),
        }
    return {}


def _budget(root: Path) -> dict[str, Any]:
    data = _read_yaml(root / "harness/context_budget.yml")
    return data or {
        "brief_max_lines": 40,
        "max_recent_deltas": 5,
        "max_human_gate_items": 3,
        "max_source_hashes": 12,
    }


def build_context_bundle(root: Path, *, lane: str = "", brief: bool = False) -> dict[str, Any]:
    root = root.resolve()
    lane = (lane or "project").strip()
    budget = _budget(root)
    state = _read_yaml(root / "aeros_state.yml")
    current = _parse_current_state(root)
    next_action = compute_next_action(root, lane="" if lane == "project" else lane).to_dict()
    source_paths = [
        "CURRENT_STATE.md",
        "NEXT_ACTION.md",
        "aeros_state.yml",
        "decisions/human_gate_queue.yml",
        "decisions/revision_log.md",
        "evidence/delta_log.jsonl",
        "harness/context_budget.yml",
    ] + LANE_READS.get(lane, [])
    try:
        from .project_adapter import context_anchor_paths, detect_project_adapter

        adapter = detect_project_adapter(root)
        adapter_paths = context_anchor_paths(root, adapter=adapter, lane=lane)
    except Exception:  # Adapter discovery is advisory context only.
        adapter = {}
        adapter_paths = []
    source_paths = list(dict.fromkeys(source_paths + adapter_paths))
    max_hashes = int(budget.get("max_source_hashes", 12) or 12)
    source_hashes = _hash_sources(root, source_paths, max_hashes=max_hashes)
    bundle = {
        "version": "0.1",
        "policy": "AEROS-CONTEXT-001",
        "generated_at": _now(),
        "project_root": str(root),
        "lane": lane,
        "current_goal": current.get("current_goal", ""),
        "current_gate": state.get("current_gate", "G0"),
        "candidate_gate": state.get("candidate_gate", "G0"),
        "gate_status": state.get("gate_status", "open"),
        "next_action": next_action,
        "current_blocker": current.get("current_blocker", ""),
        "latest_substantive_artifact": current.get("latest_substantive_artifact", ""),
        "last_validation": current.get("last_validation", ""),
        "does_not_prove": current.get("does_not_prove", DEFAULT_DOES_NOT_PROVE),
        "open_human_gate_items": _human_gate_summary(root, int(budget.get("max_human_gate_items", 3) or 3)),
        "recent_evidence_deltas": _read_jsonl_tail(root / "evidence/delta_log.jsonl", int(budget.get("max_recent_deltas", 5) or 5)),
        "latest_revision": _latest_revision(root),
        "lane_snapshot": _lane_snapshot(root, lane),
        "files_to_read_if_needed": list(dict.fromkeys(
            LANE_READS.get(lane, ["CURRENT_STATE.md", "NEXT_ACTION.md", "AGENTS.md"]) + adapter_paths
        )),
        "project_adapter": {
            "project_kind": adapter.get("project_kind", "unknown"),
            "runtime_mode": adapter.get("runtime_mode", "unknown"),
            "adapter_present": bool(adapter),
        },
        "source_hashes": source_hashes,
        "context_staleness": _context_staleness(root, lane, source_hashes),
        "stop_rule": next_action.get("stop_condition", "Stop before switching lanes, claiming substantive progress, or changing gates without evidence."),
        "context_boundary": "Brief context only. Read referenced files only when the next action requires them.",
    }
    if brief:
        bundle["brief"] = True
    return bundle


def format_context_bundle(bundle: dict[str, Any], *, brief: bool = False) -> str:
    next_action = bundle.get("next_action") or {}
    lines = [
        "# CONTEXT_BUNDLE",
        "",
        f"generated_at: {bundle.get('generated_at', '')}",
        f"lane: {bundle.get('lane', '')}",
        f"current_goal: {bundle.get('current_goal', '')}",
        f"current_gate: {bundle.get('current_gate', '')}",
        f"candidate_gate: {bundle.get('candidate_gate', '')}",
        f"gate_status: {bundle.get('gate_status', '')}",
        f"recommended_next_action: {next_action.get('recommended_next_action', '')}",
        f"status_label: {next_action.get('status_label', '')}",
        f"next_command: {next_action.get('command', '')}",
        f"current_blocker: {bundle.get('current_blocker', '')}",
        f"latest_substantive_artifact: {bundle.get('latest_substantive_artifact', '')}",
        f"last_validation: {bundle.get('last_validation', '')}",
        f"does_not_prove: {bundle.get('does_not_prove', '')}",
        f"context_stale: {(bundle.get('context_staleness') or {}).get('stale', False)}",
        f"context_stale_reason: {(bundle.get('context_staleness') or {}).get('message', '')}",
        f"stop_rule: {bundle.get('stop_rule', '')}",
        f"latest_revision: {bundle.get('latest_revision', '')}",
        f"project_kind: {(bundle.get('project_adapter') or {}).get('project_kind', 'unknown')}",
        f"runtime_mode: {(bundle.get('project_adapter') or {}).get('runtime_mode', 'unknown')}",
        "",
        "## Lane Snapshot",
    ]
    snapshot = bundle.get("lane_snapshot") or {}
    if snapshot:
        for key, value in snapshot.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")
    gates = bundle.get("open_human_gate_items") or []
    lines.extend(["", "## Open Human Gate Items"])
    if gates:
        for item in gates:
            lines.append(f"- {item.get('project', '')}: {item.get('request', '')} ({item.get('status', '')})")
    else:
        lines.append("- none")
    lines.extend(["", "## Files To Read If Needed"])
    for rel in bundle.get("files_to_read_if_needed") or []:
        lines.append(f"- {rel}")
    if not brief:
        lines.extend(["", "## Context Staleness"])
        stale = bundle.get("context_staleness") or {}
        lines.append(f"- status: {stale.get('status', 'unknown')}")
        changed = stale.get("changed_sources") or []
        if changed:
            for rel in changed:
                lines.append(f"- changed: {rel}")
        else:
            lines.append("- changed: none")
        lines.extend(["", "## Source Hashes"])
        hashes = bundle.get("source_hashes") or {}
        if hashes:
            for rel, digest in hashes.items():
                lines.append(f"- {rel}: {digest}")
        else:
            lines.append("- none")
        lines.extend(["", "## Recent Evidence Deltas"])
        deltas = bundle.get("recent_evidence_deltas") or []
        if deltas:
            for delta in deltas:
                lines.append(f"- {delta.get('delta_id', '?')}: {delta.get('summary', '')}")
        else:
            lines.append("- none")
    lines.append("")
    lines.append("This bundle is context, not completion evidence, gate approval, claim support, or validation.")
    return "\n".join(lines)


def write_context_bundle(root: Path, bundle: dict[str, Any]) -> tuple[Path, Path]:
    md_path = root / "CONTEXT_BUNDLE.md"
    json_path = root / "outputs/context/context_bundle.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(format_context_bundle(bundle), encoding="utf-8")
    json_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path, json_path
