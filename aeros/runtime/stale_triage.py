"""Deterministic stale-task triage for AEROS.

This module classifies stale controller steps into three buckets:
- rerun_required: preview a real rerun path with iterate --dry-run
- revalidate_free: refresh fingerprints/checks without provider/API spend
- suppress_as_irrelevant: hide only when irrelevance is deterministically proven

It is intentionally not an LLM planner and does not mutate runtime state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from .controller import build_iterate_plan
from .kernel import (
    _dependency_fingerprint,
    _fingerprint_paths,
    discover_contracts,
)
from .research_graph import parse_claim_registry, split_ids
from .state import load_state

BUCKETS = {"rerun_required", "revalidate_free", "suppress_as_irrelevant"}
LANES = ["", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"]
STAGES = ["discovery", "execution"]


def _gate_rank(gate: str) -> int:
    import re
    match = re.match(r"^G(\d+)$", str(gate or "G0").split()[0])
    return int(match.group(1)) if match else -1

CLAIM_BOUND_OUTPUTS = {
    "evidence/claim_registry.md",
    "evidence/evidence_ledger.csv",
    "evidence/result_index.csv",
    "evidence/result_registry.csv",
    "evidence/research_graph.yml",
}

PAPER_OUTPUT_PREFIXES = ("paper/", "tex/")
VOLATILE_OUTPUT_PREFIXES = ("agent_runs/", "outputs/logs/", "outputs/context/")
VOLATILE_OUTPUT_FILES = {
    "decisions/revision_log.md",
    "decisions/update_ledger.md",
}
HIGH_IMPACT_SCOPES = {"specific_claims", "claim_registry_unknown", "registry_unknown"}


@dataclass(frozen=True)
class StaleTriageItem:
    task_id: str
    stage: str
    lane: str
    gate: str
    stale_reason: str
    bucket: str
    impact_level: str
    impact_scope: str
    command: str
    rationale: str
    output_changed: bool
    volatile_only_outputs: bool
    input_changed: bool
    dependency_changed: bool
    frontier_connected: bool
    claim_bound: bool
    impacted_claims: list[str]
    downstream_frontier_tasks: list[str]
    allowed_outputs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StaleTriageResult:
    frontier_gate: str
    frontier_rank: int
    stage: str
    lane: str
    items: list[StaleTriageItem]
    does_not_prove: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frontier_gate": self.frontier_gate,
            "frontier_rank": self.frontier_rank,
            "stage": self.stage,
            "lane": self.lane,
            "items": [item.to_dict() for item in self.items],
            "does_not_prove": list(self.does_not_prove),
        }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def _norm(path: str) -> str:
    return str(path or "").strip().lstrip("./")


def _path_matches(output: str, candidate: str) -> bool:
    out = _norm(output)
    cand = _norm(candidate)
    if not out or not cand:
        return False
    return cand == out or cand.startswith(out.rstrip("/") + "/") or out.startswith(cand.rstrip("/") + "/")


def _is_volatile_output(output: str) -> bool:
    out = _norm(output)
    return out in VOLATILE_OUTPUT_FILES or any(out.startswith(prefix) for prefix in VOLATILE_OUTPUT_PREFIXES)


def _frontier_gate(state: dict[str, Any]) -> str:
    current = str(state.get("current_gate", "G0")).split()[0]
    candidate = str(state.get("candidate_gate", current)).split()[0]
    return candidate if _gate_rank(candidate) >= _gate_rank(current) else current


def _dependency_descendants(contracts: dict[str, tuple[Any, Path]]) -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = {task_id: set() for task_id in contracts}
    for task_id, (contract, _path) in contracts.items():
        for dep in contract.depends_on or []:
            reverse.setdefault(dep, set()).add(task_id)
    descendants: dict[str, set[str]] = {task_id: set() for task_id in contracts}
    for task_id in contracts:
        stack = list(reverse.get(task_id, set()))
        seen: set[str] = set()
        while stack:
            child = stack.pop()
            if child in seen:
                continue
            seen.add(child)
            stack.extend(reverse.get(child, set()))
        descendants[task_id] = seen
    return descendants


def _task_outputs(contract: Any) -> list[str]:
    return [_norm(path) for path in (contract.allowed_outputs or []) if str(path).strip()]


def _output_fingerprint_changed(root: Path, state: dict[str, Any], task_id: str, contract: Any) -> bool:
    entry = (state.get("tasks") or {}).get(task_id, {})
    previous = str(entry.get("output_fingerprint", ""))
    current = _fingerprint_paths(root, contract.allowed_outputs)
    return previous != current


def _input_fingerprint_changed(root: Path, state: dict[str, Any], task_id: str, contract: Any) -> bool:
    entry = (state.get("tasks") or {}).get(task_id, {})
    previous = str(entry.get("input_fingerprint", ""))
    current = _fingerprint_paths(root, contract.inputs)
    return bool(previous) and previous != current


def _dependency_fingerprint_changed(root: Path, state: dict[str, Any], task_id: str, contract: Any, contracts: dict[str, tuple[Any, Path]]) -> bool:
    entry = (state.get("tasks") or {}).get(task_id, {})
    previous = str(entry.get("dependency_fingerprint", ""))
    current = _dependency_fingerprint(root, contract, contracts)
    return bool(previous) and previous != current


def _claim_links(root: Path) -> dict[str, Any]:
    claims = parse_claim_registry(root)
    active_claims = sorted(c.get("claim_id", "") for c in claims if c.get("claim_id"))
    result_to_claims: dict[str, set[str]] = {}
    evidence_to_claims: dict[str, set[str]] = {}
    for claim in claims:
        cid = str(claim.get("claim_id", "")).strip()
        for rid in claim.get("result_ids") or []:
            result_to_claims.setdefault(rid, set()).add(cid)
        for eid in claim.get("evidence_ids") or []:
            evidence_to_claims.setdefault(eid, set()).add(cid)
    result_rows = _read_csv(root / "evidence/result_index.csv")
    result_paths: list[tuple[str, str, str]] = []
    for row in result_rows:
        rid = row.get("result_id", "")
        for cid in split_ids(row.get("linked_claims", "")):
            if rid and cid:
                result_to_claims.setdefault(rid, set()).add(cid)
        if rid:
            result_paths.append((rid, row.get("path", ""), row.get("script_or_source", "")))
    evidence_rows = _read_csv(root / "evidence/evidence_ledger.csv")
    evidence_paths: list[tuple[str, str]] = []
    for row in evidence_rows:
        eid = row.get("evidence_id", "")
        for cid in split_ids(row.get("claim_id", "")):
            if eid and cid:
                evidence_to_claims.setdefault(eid, set()).add(cid)
        if eid:
            evidence_paths.append((eid, row.get("source_or_path", "")))
    return {
        "active_claims": active_claims,
        "result_to_claims": result_to_claims,
        "result_paths": result_paths,
        "evidence_to_claims": evidence_to_claims,
        "evidence_paths": evidence_paths,
    }


def _output_claim_impact(outputs: list[str], links: dict[str, Any]) -> tuple[bool, list[str], str]:
    impacted: set[str] = set()
    registry_unknown = False
    claim_registry_unknown = False
    paper_global_review = False
    for output in outputs:
        normalized = _norm(output)
        if normalized == "evidence/claim_registry.md":
            claim_registry_unknown = True
        elif normalized in CLAIM_BOUND_OUTPUTS:
            registry_unknown = True
        elif normalized.startswith(PAPER_OUTPUT_PREFIXES):
            paper_global_review = True
        for rid, result_path, script_path in links.get("result_paths") or []:
            if _path_matches(output, result_path) or _path_matches(output, script_path):
                impacted.update(links.get("result_to_claims", {}).get(rid, set()))
        for eid, source_path in links.get("evidence_paths") or []:
            if _path_matches(output, source_path):
                impacted.update(links.get("evidence_to_claims", {}).get(eid, set()))
    impacted_claims = sorted(cid for cid in impacted if cid)
    if impacted_claims:
        return True, impacted_claims, "specific_claims"
    if claim_registry_unknown:
        return True, [], "claim_registry_unknown"
    if registry_unknown:
        return True, [], "registry_unknown"
    if paper_global_review:
        return False, [], "paper_global_review"
    return False, [], "none"


def _frontier_connected(
    task_id: str,
    contract: Any,
    descendants: dict[str, set[str]],
    contracts: dict[str, tuple[Any, Path]],
    state: dict[str, Any],
    frontier_rank: int,
    claim_bound: bool,
) -> tuple[bool, list[str]]:
    connected: list[str] = []
    if claim_bound:
        connected.append("claim_bound_output")
    for downstream_id in sorted(descendants.get(task_id, set())):
        downstream_contract = contracts.get(downstream_id, (None, None))[0]
        if downstream_contract is None:
            continue
        entry = (state.get("tasks") or {}).get(downstream_id, {})
        downstream_rank = _gate_rank(str(downstream_contract.gate or "G0"))
        downstream_outputs = " ".join(_task_outputs(downstream_contract)).lower()
        output_is_frontier = any(token in downstream_outputs for token in [
            "evidence/result", "evidence/claim", "paper/", "outputs/tables", "outputs/model_outputs"
        ])
        if entry.get("status") == "passed" and downstream_rank >= frontier_rank:
            connected.append(downstream_id)
        elif output_is_frontier:
            connected.append(downstream_id)
    own_rank = _gate_rank(str(contract.gate or "G0"))
    if own_rank >= frontier_rank:
        connected.append(task_id)
    return bool(connected), sorted(set(connected))


def _classify(
    *,
    output_changed: bool,
    volatile_only_outputs: bool,
    frontier_connected: bool,
    claim_bound: bool,
    impacted_claims: list[str],
    impact_scope: str,
) -> tuple[str, str, str]:
    effective_output_changed = output_changed and not volatile_only_outputs
    high_impact = bool(impacted_claims) or impact_scope in HIGH_IMPACT_SCOPES
    if output_changed and volatile_only_outputs:
        return (
            "revalidate_free",
            "high" if high_impact else "medium",
            "python3 -m aeros.cli recover {task_id} --check",
        )
    if not frontier_connected and not effective_output_changed:
        return (
            "suppress_as_irrelevant",
            "low",
            "No action: stale task is disconnected from the current frontier and allowed-output fingerprint is unchanged.",
        )
    if not effective_output_changed:
        level = "high" if high_impact else "medium"
        return (
            "revalidate_free",
            level,
            "python3 -m aeros.cli recover {task_id} --check",
        )
    level = "high" if high_impact or (frontier_connected and impact_scope != "paper_global_review") else "medium"
    return (
        "rerun_required",
        level,
        "python3 -m aeros.cli iterate --stage {stage}{lane_part} --to-next-gate --dry-run",
    )


def triage_stale_tasks(root: Path, *, stage: str = "discovery", lane: str = "") -> StaleTriageResult:
    root = root.resolve()
    state = load_state(root)
    frontier = _frontier_gate(state)
    frontier_rank = _gate_rank(frontier)
    contracts = discover_contracts(root)
    descendants = _dependency_descendants(contracts)
    links = _claim_links(root)
    stages = STAGES if stage == "all" else [stage]
    items: list[StaleTriageItem] = []
    seen: set[tuple[str, str, str]] = set()
    for stage_name in stages:
        plan = build_iterate_plan(root, stage_name, to_next_gate=True, lane=lane)
        for step in plan.steps:
            if step.action != "rerun":
                continue
            key = (stage_name, step.lane or lane or "", step.task_id)
            if key in seen:
                continue
            seen.add(key)
            contract = contracts.get(step.task_id, (None, None))[0]
            if contract is None:
                continue
            outputs = _task_outputs(contract)
            output_changed = _output_fingerprint_changed(root, state, step.task_id, contract)
            volatile_only_outputs = bool(outputs) and all(_is_volatile_output(output) for output in outputs)
            input_changed = _input_fingerprint_changed(root, state, step.task_id, contract)
            dependency_changed = _dependency_fingerprint_changed(root, state, step.task_id, contract, contracts)
            claim_bound, impacted_claims, impact_scope = _output_claim_impact(outputs, links)
            connected, downstream = _frontier_connected(
                step.task_id,
                contract,
                descendants,
                contracts,
                state,
                frontier_rank,
                claim_bound,
            )
            bucket, impact_level, command_template = _classify(
                output_changed=output_changed,
                volatile_only_outputs=volatile_only_outputs,
                frontier_connected=connected,
                claim_bound=claim_bound,
                impacted_claims=impacted_claims,
                impact_scope=impact_scope,
            )
            lane_value = step.lane or lane or ""
            lane_part = f" --lane {lane_value}" if lane_value else ""
            command = command_template.format(task_id=step.task_id, stage=stage_name, lane_part=lane_part)
            if bucket == "rerun_required":
                rationale = "Stale item remains visible because output changed or frontier/claim irrelevance cannot be proven. Preview only."
            elif bucket == "revalidate_free":
                rationale = "Allowed-output fingerprint is unchanged; refresh via checks before spending provider/API budget."
            else:
                rationale = "Deterministically suppressed: no frontier/claim path and allowed-output fingerprint unchanged."
            if claim_bound or impacted_claims:
                if impact_scope == "specific_claims":
                    rationale += " Specific claim-bound/result-bound path detected; human review may be needed if checks fail."
                else:
                    rationale += " Claim-bound registry changed but impacted claims cannot be localized; run claim/graph consistency checks before interpreting impact."
            elif impact_scope == "paper_global_review":
                rationale += " Paper artifact changed without a deterministic claim link; review paper-level consistency but do not assume all claims are impacted."
            if volatile_only_outputs and output_changed:
                rationale += " Only volatile allowed outputs changed; do not call a provider/API before free revalidation."
            items.append(StaleTriageItem(
                task_id=step.task_id,
                stage=stage_name,
                lane=lane_value or "project",
                gate=step.gate,
                stale_reason=step.stale_reason,
                bucket=bucket,
                impact_level=impact_level,
                impact_scope=impact_scope,
                command=command,
                rationale=rationale,
                output_changed=output_changed,
                volatile_only_outputs=volatile_only_outputs,
                input_changed=input_changed,
                dependency_changed=dependency_changed,
                frontier_connected=connected,
                claim_bound=claim_bound,
                impacted_claims=impacted_claims,
                downstream_frontier_tasks=downstream,
                allowed_outputs=outputs,
            ))
    bucket_order = {"rerun_required": 0, "revalidate_free": 1, "suppress_as_irrelevant": 2}
    impact_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda item: (bucket_order.get(item.bucket, 9), impact_order.get(item.impact_level, 9), item.stage, item.lane, item.task_id))
    return StaleTriageResult(
        frontier_gate=frontier,
        frontier_rank=frontier_rank,
        stage=stage,
        lane=lane or "project",
        items=items,
        does_not_prove=[
            "checks pass",
            "rerun necessity beyond deterministic dependencies",
            "scientific validity",
            "claim support",
            "gate approval",
        ],
    )



def triage_item_for_task(root: Path, *, stage: str, lane: str = "", task_id: str) -> StaleTriageItem | None:
    result = triage_stale_tasks(root, stage=stage, lane=lane)
    for item in result.items:
        if item.task_id == task_id:
            return item
    return None

def first_visible_stale_item(root: Path, *, stage: str, lane: str = "") -> StaleTriageItem | None:
    result = triage_stale_tasks(root, stage=stage, lane=lane)
    for item in result.items:
        if item.bucket in {"rerun_required", "revalidate_free"}:
            return item
    return None


def format_stale_triage(result: StaleTriageResult) -> str:
    lines = [
        "# STALE_TRIAGE",
        "",
        f"frontier_gate: {result.frontier_gate}",
        f"stage: {result.stage}",
        f"lane: {result.lane}",
        f"items: {len(result.items)}",
        "",
    ]
    if not result.items:
        lines.append("No stale tasks found in the selected controller frontier.")
    for item in result.items:
        lines.extend([
            f"## {item.task_id}",
            f"bucket: {item.bucket}",
            f"impact_level: {item.impact_level}",
            f"impact_scope: {item.impact_scope}",
            f"stage: {item.stage}",
            f"lane: {item.lane}",
            f"gate: {item.gate}",
            f"stale_reason: {item.stale_reason}",
            f"command: {item.command}",
            f"volatile_only_outputs: {item.volatile_only_outputs}",
            f"frontier_connected: {item.frontier_connected}",
            f"claim_bound: {item.claim_bound}",
            f"impacted_claims: {'unknown' if item.impact_scope in {'claim_registry_unknown', 'registry_unknown'} else ', '.join(item.impacted_claims) if item.impacted_claims else 'none'}",
            f"downstream_frontier_tasks: {', '.join(item.downstream_frontier_tasks) if item.downstream_frontier_tasks else 'none'}",
            f"rationale: {item.rationale}",
            "",
        ])
    lines.append("does_not_prove: " + "; ".join(result.does_not_prove))
    lines.append("This is deterministic triage only; it does not run agents, refresh fingerprints, alter state, or adjudicate claims.")
    return "\n".join(lines)


def stale_triage_json(result: StaleTriageResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def write_stale_triage(root: Path, result: StaleTriageResult) -> tuple[Path, Path]:
    out_dir = root / "outputs/context"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "stale_triage.md"
    json_path = out_dir / "stale_triage.json"
    md_path.write_text(format_stale_triage(result), encoding="utf-8")
    json_path.write_text(stale_triage_json(result) + "\n", encoding="utf-8")
    return md_path, json_path
