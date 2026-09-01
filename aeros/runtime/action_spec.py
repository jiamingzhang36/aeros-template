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

from .environment_profile import compile_environment_profile, validate_environment_profile


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
    campaign_id: str = ""
    context_episode_id: str = ""
    context_hash: str = ""
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
    runtime_profile: str = ""
    environment_profile: dict[str, Any] = field(default_factory=dict)
    environment_approval_fingerprint: str = ""
    resource_budget: dict[str, str] = field(default_factory=dict)
    authority_boundary: dict[str, str] = field(default_factory=dict)
    preconditions: tuple[str, ...] = ()
    semantic_progress_predicate: tuple[str, ...] = ()
    post_run_hooks: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    execution_envelope: dict[str, Any] = field(default_factory=dict)
    reversal_policy: dict[str, str | bool] = field(default_factory=dict)
    does_not_prove: tuple[str, ...] = (
        "scientific validity",
        "claim support",
        "gate approval",
        "paper readiness",
    )

    def __post_init__(self) -> None:
        data = {
            "kind": self.kind,
            "lane": self.lane,
            "effect_class": self.effect_class,
            "campaign_id": self.campaign_id,
            "context_episode_id": self.context_episode_id,
            "capabilities": self.capabilities,
            "expected_outputs": self.expected_outputs,
            "authority_boundary": self.authority_boundary,
        }
        profile = self.environment_profile or compile_environment_profile(data)
        object.__setattr__(self, "environment_profile", profile)
        digest = str(profile.get("policy_digest") or "")
        fingerprint = str(profile.get("approval_fingerprint") or "")
        object.__setattr__(self, "environment_approval_fingerprint", self.environment_approval_fingerprint or fingerprint)
        base_key = self.idempotency_key or self.id
        if digest and not base_key.endswith(":" + digest[:12]):
            object.__setattr__(self, "idempotency_key", f"{base_key}:{digest[:12]}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in (
            "capabilities",
            "expected_outputs",
            "acceptance_checks",
            "preconditions",
            "semantic_progress_predicate",
            "post_run_hooks",
            "postconditions",
            "does_not_prove",
        ):
            data[key] = list(data.get(key) or [])
        return data


def _stable_id(kind: str, lane: str, command: str, source: str, campaign_id: str = "") -> str:
    identity = f"{kind}\0{lane}\0{command}\0{source}"
    if campaign_id:
        identity += f"\0campaign:{campaign_id}"
    digest = sha256(identity.encode("utf-8")).hexdigest()[:12]
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


def _default_authority_boundary(effect_class: str, requires_decision: bool) -> dict[str, str]:
    return {
        "claim": "none",
        "release": "none",
        "credentials": "none",
        "human_decision_required": str(bool(requires_decision)).lower(),
        "effect_class": effect_class,
    }


def _semantic_progress_for(kind: str, effect_class: str) -> tuple[str, ...]:
    if effect_class == "task_run":
        return ("contract_status:met", "artifact_contract_met")
    mapping = {
        "literature_search": ("registry_delta:literature_candidate",),
        "graph_build": ("projection_fresh:research_graph",),
        "paper_ci_sync": ("projection_fresh:result_index", "projection_fresh:provenance"),
        "data_scan": ("artifact_contract_met:data_inventory",),
        "data_gap_plan": ("route_ready:data_gap_plan",),
        "data_probe_plan": ("artifact_contract_met:data_probe",),
        "data_backfill_plan": ("route_ready:backfill_queue",),
    }
    return mapping.get(kind, ())


def _post_run_hooks_for(kind: str, effect_class: str) -> tuple[str, ...]:
    if effect_class == "task_run":
        return ("reconcile", "session_scope")
    if kind in {"paper_ci_sync"}:
        return ("reconcile",)
    return ()


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
    campaign_id = str(getattr(action, "campaign_id", "") or "").strip()
    risk = "requires human authority or missing input" if requires_decision else "bounded deterministic controller action"
    if effect_class == "task_run":
        risk = "real task execution; requires explicit --allow-task-runs"
    budget = {"max_provider_calls": "0", "max_cost_usd": "0"}
    if effect_class == "task_run":
        budget = {"requires_explicit_allow_task_runs": "true"}
    return ActionSpec(
        id=_stable_id(kind, lane, command, source, campaign_id),
        kind=kind,
        lane=lane,
        effect_class=effect_class,
        campaign_id=campaign_id,
        capabilities=_capabilities_for(kind, effect_class),
        requires_decision=requires_decision,
        expected_outputs=_expected_outputs_for(kind),
        acceptance_checks=_acceptance_checks_for(kind),
        command=command,
        stop_condition=str(getattr(action, "stop_condition", "") or ""),
        source=source,
        risk=risk,
        idempotency_key=_stable_id(kind, lane, command, source, campaign_id),
        producer_mode="inferred_compat",
        runtime_profile="",
        resource_budget=budget,
        authority_boundary=_default_authority_boundary(effect_class, requires_decision),
        preconditions=("project root resolved", "command parsed only through controller allowlist"),
        semantic_progress_predicate=_semantic_progress_for(kind, effect_class),
        post_run_hooks=_post_run_hooks_for(kind, effect_class),
        postconditions=("write run record or blocker", "do not approve gates or upgrade claims"),
        reversal_policy={"reversible": effect_class in {"read_only", "local_write_preview"}, "cleanup_handler": "manual_review"},
    )


def declared_action_spec(
    *,
    kind: str,
    effect_class: str,
    lane: str,
    campaign_id: str = "",
    context_episode_id: str = "",
    context_hash: str = "",
    command: str,
    stop_condition: str,
    source: str = "deterministic",
    blocked: bool = False,
    requires_decision: bool | None = None,
    capabilities: tuple[str, ...] | None = None,
    expected_outputs: tuple[str, ...] | None = None,
    acceptance_checks: tuple[str, ...] | None = None,
    risk: str = "",
    runtime_profile: str = "",
    authority_boundary: dict[str, str] | None = None,
    preconditions: tuple[str, ...] | None = None,
    semantic_progress_predicate: tuple[str, ...] | None = None,
    post_run_hooks: tuple[str, ...] | None = None,
    postconditions: tuple[str, ...] | None = None,
    reversal_policy: dict[str, str | bool] | None = None,
    execution_envelope: dict[str, Any] | None = None,
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
        id=_stable_id(kind, lane, command, source, campaign_id),
        kind=kind,
        lane=lane,
        effect_class=effect_class,
        campaign_id=str(campaign_id or "").strip(),
        context_episode_id=str(context_episode_id or "").strip(),
        context_hash=str(context_hash or "").strip(),
        capabilities=merged_capabilities,
        requires_decision=bool(requires_decision),
        expected_outputs=expected_outputs if expected_outputs is not None else _expected_outputs_for(kind),
        acceptance_checks=acceptance_checks if acceptance_checks is not None else _acceptance_checks_for(kind),
        command=command,
        stop_condition=stop_condition,
        source=source,
        risk=risk or ("requires human authority or missing input" if requires_decision else "bounded deterministic controller action"),
        idempotency_key=_stable_id(kind, lane, command, source, campaign_id),
        producer_mode="declared",
        runtime_profile=runtime_profile,
        resource_budget=budget,
        authority_boundary=authority_boundary or _default_authority_boundary(effect_class, bool(requires_decision)),
        preconditions=preconditions or ("project root resolved", "command rendered from declared ActionSpec"),
        semantic_progress_predicate=semantic_progress_predicate if semantic_progress_predicate is not None else _semantic_progress_for(kind, effect_class),
        post_run_hooks=post_run_hooks if post_run_hooks is not None else _post_run_hooks_for(kind, effect_class),
        postconditions=postconditions or ("write run record or blocker", "do not approve gates or upgrade claims"),
        execution_envelope=execution_envelope or {},
        reversal_policy=reversal_policy or {"reversible": effect_class in {"read_only", "local_write_preview"}, "cleanup_handler": "manual_review"},
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
    if not isinstance(data.get("campaign_id", ""), str):
        failures.append("ActionSpec campaign_id must be a string")
    if not isinstance(data.get("context_episode_id", ""), str):
        failures.append("ActionSpec context_episode_id must be a string")
    if not isinstance(data.get("context_hash", ""), str):
        failures.append("ActionSpec context_hash must be a string")
    if bool(data.get("context_episode_id")) != bool(data.get("context_hash")):
        failures.append("ActionSpec context episode identity and hash must be declared together")
    if not isinstance(data.get("capabilities"), list) or not data.get("capabilities"):
        failures.append("ActionSpec capabilities must be a non-empty list")
    if data.get("effect_class") in {"task_run", "human_decision", "blocked"} and not data.get("requires_decision"):
        failures.append("ActionSpec must require a decision for task_run/human_decision/blocked effects")
    if data.get("effect_class") == "read_only" and data.get("expected_outputs"):
        failures.append("read_only ActionSpec must not declare expected_outputs")
    boundary = data.get("authority_boundary")
    if not isinstance(boundary, dict) or not boundary:
        failures.append("ActionSpec must declare authority_boundary")
    if data.get("post_run_hooks") and not isinstance(data.get("post_run_hooks"), list):
        failures.append("ActionSpec post_run_hooks must be a list")
    if data.get("execution_envelope") and not isinstance(data.get("execution_envelope"), dict):
        failures.append("ActionSpec execution_envelope must be a mapping when present")
    profile = data.get("environment_profile")
    if profile:
        failures.extend(validate_environment_profile(profile))
    if not str(data.get("environment_approval_fingerprint") or "").strip():
        failures.append("ActionSpec missing environment_approval_fingerprint")
    return failures
