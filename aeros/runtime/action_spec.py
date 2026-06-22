"""Typed action specifications for deterministic AEROS control.

``aeros next`` may still render a command for human convenience, but the command
string is not the authority boundary. The controller should reason from this
typed ActionSpec first, then use the command only as a backward-compatible
executor preview.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any


EFFECT_CLASSES = {
    "read_only",
    "local_write_preview",
    "local_write",
    "task_run",
    "human_decision",
    "blocked",
}


@dataclass(frozen=True)
class ActionSpec:
    id: str
    kind: str
    lane: str
    effect_class: str
    capabilities: tuple[str, ...] = ()
    requires_decision: bool = False
    expected_outputs: tuple[str, ...] = ()
    acceptance_checks: tuple[str, ...] = ()
    command: str = ""
    stop_condition: str = ""
    source: str = "deterministic"
    risk: str = ""
    idempotency_key: str = ""
    producer_mode: str = "declared"
    resource_budget: dict[str, str] = field(default_factory=dict)
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    does_not_prove: tuple[str, ...] = (
        "scientific validity",
        "claim support",
        "gate approval",
        "paper readiness",
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in (
            "capabilities",
            "expected_outputs",
            "acceptance_checks",
            "preconditions",
            "postconditions",
            "does_not_prove",
        ):
            data[key] = list(data.get(key) or [])
        return data


def _stable_id(kind: str, lane: str, command: str, source: str) -> str:
    digest = sha256(f"{kind}\0{lane}\0{command}\0{source}".encode("utf-8")).hexdigest()[:12]
    return f"AS-{digest}"


def _contains_gate_command(command: str) -> bool:
    padded = f" {command} "
    return " gate " in padded or " decide " in padded


def _infer_kind(command: str, text: str, lane: str) -> str:
    normalized = command.strip()
    lower = f"{text} {normalized}".lower()
    if not normalized:
        return "none"
    if "adopt --idea" in normalized or "aeros.cli adopt" in normalized:
        return "adopt_idea"
    if "literature status" in normalized:
        return "literature_status"
    if "literature search" in normalized:
        return "literature_search"
    if "stale triage" in normalized:
        return "stale_triage"
    if "graph build" in normalized:
        return "graph_build"
    if "paper-ci sync-result-index" in normalized:
        return "paper_ci_sync"
    if "aeros.cli next" in normalized:
        return "next_action_write" if "--write" in normalized else "next_action_preview"
    if "run_harness_checks.py" in normalized or "/check_" in normalized or "checks/check_" in normalized:
        return "check_profile"
    if "aeros.cli iterate" in normalized:
        return "iterate_preview" if "--dry-run" in normalized else "task_iteration"
    if _contains_gate_command(normalized):
        return "human_decision"
    if "data scan" in normalized:
        return "data_scan"
    if "data gaps" in normalized:
        return "data_gap_plan"
    if "data probe" in normalized:
        return "data_probe_plan"
    if "data backfill" in normalized:
        return "data_backfill_plan"
    if "skills plan" in normalized or "method" in lower:
        return "method_advisory"
    if lane == "writing" or "draft" in lower:
        return "writing_route"
    return "generic_controller_action"


def _infer_effect_class(command: str, *, blocked: bool, kind: str) -> str:
    if blocked:
        return "blocked"
    if kind == "human_decision":
        return "human_decision"
    if kind == "task_iteration":
        return "task_run"
    if "--dry-run" in command:
        return "local_write_preview"
    if kind in {"literature_status", "stale_triage", "check_profile", "next_action_preview"}:
        return "read_only"
    if kind in {"graph_build", "paper_ci_sync", "adopt_idea", "literature_search", "next_action_write"}:
        return "local_write"
    return "read_only"


def _capabilities_for(kind: str, effect_class: str) -> tuple[str, ...]:
    capabilities = ["read_project_state"]
    if kind.startswith("literature"):
        capabilities.extend(["read_literature_registry", "read_literature_queue"])
    if kind.startswith("data"):
        capabilities.extend(["read_data_inventory", "plan_data_work"])
    if kind in {"graph_build", "stale_triage"}:
        capabilities.append("read_research_graph")
    if kind in {"paper_ci_sync"}:
        capabilities.append("read_result_registry")
    if kind in {"check_profile"}:
        capabilities.append("run_checks")
    if effect_class in {"local_write", "local_write_preview"}:
        capabilities.append("write_candidate_artifact")
    if effect_class == "task_run":
        capabilities.append("run_task")
    if effect_class in {"human_decision", "blocked"}:
        capabilities.append("request_human_decision")
    return tuple(dict.fromkeys(capabilities))


def _expected_outputs_for(kind: str) -> tuple[str, ...]:
    mapping = {
        "adopt_idea": ("adoption/", "decisions/adoption/"),
        "literature_search": ("discovery/literature/search_log.csv", "discovery/literature/paper_registry.csv"),
        "graph_build": ("evidence/research_graph.yml",),
        "paper_ci_sync": ("evidence/result_index.csv", "outputs/.provenance/"),
        "data_scan": ("data/data_state.yml", "discovery/data_inventory.csv"),
        "data_gap_plan": ("data/data_gap_plan.yml",),
        "data_probe_plan": ("audits/data_probe_report.md",),
        "data_backfill_plan": ("data/backfill/backfill_queue.yml",),
    }
    return mapping.get(kind, ())


def _acceptance_checks_for(kind: str) -> tuple[str, ...]:
    mapping = {
        "literature_search": ("checks/check_literature_tools.py",),
        "literature_status": ("checks/check_literature_fulltext_execution.py",),
        "graph_build": ("checks/check_research_graph.py",),
        "paper_ci_sync": ("checks/check_result_registry.py",),
        "check_profile": ("requested check exits 0",),
        "data_scan": ("checks/check_data_inventory.py",),
        "data_gap_plan": ("checks/check_data_first_readiness.py",),
        "data_probe_plan": ("checks/check_data_probe.py",),
    }
    return mapping.get(kind, ())


def action_spec_from_next(action: Any) -> ActionSpec:
    command = str(getattr(action, "command", "") or "")
    lane = str(getattr(action, "lane", "") or "project")
    text = " ".join(
        str(getattr(action, field_name, "") or "")
        for field_name in ("recommended_next_action", "why_this_next", "stop_condition")
    )
    kind = _infer_kind(command, text, lane)
    blocked = bool(getattr(action, "blocked", False))
    effect_class = _infer_effect_class(command, blocked=blocked, kind=kind)
    requires_decision = blocked or effect_class in {"task_run", "human_decision", "blocked"} or "<" in command or _contains_gate_command(command)
    source = str(getattr(action, "source", "") or "deterministic")
    risk = "requires human authority or missing input" if requires_decision else "bounded deterministic controller action"
    if effect_class == "task_run":
        risk = "real task execution; requires explicit --allow-task-runs"
    budget = {"max_provider_calls": "0", "max_cost_usd": "0"}
    if effect_class == "task_run":
        budget = {"requires_explicit_allow_task_runs": "true"}
    return ActionSpec(
        id=_stable_id(kind, lane, command, source),
        kind=kind,
        lane=lane,
        effect_class=effect_class,
        capabilities=_capabilities_for(kind, effect_class),
        requires_decision=requires_decision,
        expected_outputs=_expected_outputs_for(kind),
        acceptance_checks=_acceptance_checks_for(kind),
        command=command,
        stop_condition=str(getattr(action, "stop_condition", "") or ""),
        source=source,
        risk=risk,
        idempotency_key=_stable_id(kind, lane, command, source),
        producer_mode="inferred_compat",
        resource_budget=budget,
        preconditions=("project root resolved", "command parsed only through controller allowlist"),
        postconditions=("write run record or blocker", "do not approve gates or upgrade claims"),
    )


def declared_action_spec(
    *,
    kind: str,
    effect_class: str,
    lane: str,
    command: str,
    stop_condition: str,
    source: str = "deterministic",
    blocked: bool = False,
    requires_decision: bool | None = None,
    capabilities: tuple[str, ...] | None = None,
    expected_outputs: tuple[str, ...] | None = None,
    acceptance_checks: tuple[str, ...] | None = None,
    risk: str = "",
    preconditions: tuple[str, ...] | None = None,
    postconditions: tuple[str, ...] | None = None,
) -> ActionSpec:
    """Build an ActionSpec from producer-known semantics.

    This is the Phase 2 path: next-action branches declare kind/effect directly
    instead of inferring them from rendered command text.
    """
    if requires_decision is None:
        requires_decision = (
            blocked
            or effect_class in {"task_run", "human_decision", "blocked"}
            or "<" in command
            or _contains_gate_command(command)
        )
    budget = {"max_provider_calls": "0", "max_cost_usd": "0"}
    if effect_class == "task_run":
        budget = {"requires_explicit_allow_task_runs": "true"}
    merged_capabilities = tuple(dict.fromkeys((capabilities or ()) + _capabilities_for(kind, effect_class)))
    return ActionSpec(
        id=_stable_id(kind, lane, command, source),
        kind=kind,
        lane=lane,
        effect_class=effect_class,
        capabilities=merged_capabilities,
        requires_decision=bool(requires_decision),
        expected_outputs=expected_outputs if expected_outputs is not None else _expected_outputs_for(kind),
        acceptance_checks=acceptance_checks if acceptance_checks is not None else _acceptance_checks_for(kind),
        command=command,
        stop_condition=stop_condition,
        source=source,
        risk=risk or ("requires human authority or missing input" if requires_decision else "bounded deterministic controller action"),
        idempotency_key=_stable_id(kind, lane, command, source),
        producer_mode="declared",
        resource_budget=budget,
        preconditions=preconditions or ("project root resolved", "command rendered from declared ActionSpec"),
        postconditions=postconditions or ("write run record or blocker", "do not approve gates or upgrade claims"),
    )


def validate_action_spec(spec: ActionSpec | dict[str, Any]) -> list[str]:
    data = spec.to_dict() if isinstance(spec, ActionSpec) else dict(spec)
    failures: list[str] = []
    for key in ("id", "kind", "lane", "effect_class", "source", "command", "stop_condition"):
        if not str(data.get(key, "")).strip():
            failures.append(f"ActionSpec missing {key}")
    if data.get("effect_class") not in EFFECT_CLASSES:
        failures.append(f"ActionSpec has invalid effect_class {data.get('effect_class')!r}")
    if data.get("producer_mode") not in {"declared", "inferred_compat"}:
        failures.append(f"ActionSpec has invalid producer_mode {data.get('producer_mode')!r}")
    if not isinstance(data.get("capabilities"), list) or not data.get("capabilities"):
        failures.append("ActionSpec capabilities must be a non-empty list")
    if data.get("effect_class") in {"task_run", "human_decision", "blocked"} and not data.get("requires_decision"):
        failures.append("ActionSpec must require a decision for task_run/human_decision/blocked effects")
    if data.get("effect_class") == "read_only" and data.get("expected_outputs"):
        failures.append("read_only ActionSpec must not declare expected_outputs")
    return failures
