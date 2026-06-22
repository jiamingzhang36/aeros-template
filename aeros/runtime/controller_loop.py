"""Bounded autonomous controller loop for AEROS.

The loop consumes the deterministic ``aeros next`` projection. It is not an
LLM planner and it does not create new authority. By default it executes only
safe/zero-cost preview or check commands; real task runs require an explicit
``--allow-task-runs`` opt-in.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any

from .action_spec import validate_action_spec
from .next_action import NextAction, compute_next_action


UNTIL_CHOICES = {"human-gate", "blocked", "no-progress", "max-steps"}
LANE_CHOICES = {"", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"}

SUBSTANTIVE_ROOTS = [
    "data",
    "discovery/literature/extraction_cards",
    "discovery/literature/synthesis",
    "evidence",
    "outputs/source_snapshots",
    "outputs/tables",
    "outputs/figures",
    "outputs/model_outputs",
    "paper",
    "replication",
]

SUBSTANTIVE_FILES = [
    "decisions/human_gate_queue.yml",
    "decisions/decision_log.csv",
    "aeros_state.yml",
]

SAFE_AEROS_COMMANDS = {
    "status",
    "context",
    "cockpit",
    "next",
    "check",
    "literature",
    "stale",
    "graph",
    "paper-ci",
    "data",
    "adopt",
    "iterate",
}

NO_WRITE_AEROS_COMMANDS = {"status", "check"}


@dataclass(frozen=True)
class ControllerLoopArgs:
    until: str = "human-gate"
    lane: str = ""
    max_steps: int = 3
    no_progress_limit: int = 1
    max_wall_time_seconds: int = 300
    max_provider_calls: int = 0
    max_cost_usd: float = 0.0
    dry_run: bool = False
    allow_task_runs: bool = False
    task_timeout: int | None = None
    max_retries: int | None = None


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _substantive_snapshot(root: Path) -> str:
    """Hash only research-substantive surfaces, not logs/check chatter."""
    rows: list[str] = []
    for rel in SUBSTANTIVE_FILES:
        path = root / rel
        if path.is_file():
            rows.append(f"{rel}:{_hash_file(path)}")
    for rel in SUBSTANTIVE_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            if "__pycache__" in path.parts or path.name == ".DS_Store":
                continue
            try:
                rel_path = path.relative_to(root).as_posix()
            except ValueError:
                rel_path = path.as_posix()
            rows.append(f"{rel_path}:{_hash_file(path)}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _semantic_state_hash(root: Path) -> str:
    """Hash coarse semantic control state, not every log/check artifact.

    This is intentionally smaller than a full artifact hash. It should flip when
    runtime state, blocker queues, data/literature/claim/result state, or paper
    readiness surfaces change. It should not flip because a chatty log file grew.
    """
    semantic_files = [
        "aeros_state.yml",
        "CURRENT_STATE.md",
        "decisions/human_gate_queue.yml",
        "decisions/decision_log.csv",
        "data/data_state.yml",
        "data/data_gap_plan.yml",
        "data/backfill/backfill_queue.yml",
        "discovery/data_inventory.csv",
        "discovery/literature/paper_registry.csv",
        "discovery/literature/search_log.csv",
        "discovery/literature/missing_fulltext_queue.csv",
        "evidence/claim_registry.md",
        "evidence/result_index.csv",
        "evidence/result_registry.csv",
        "evidence/research_graph.yml",
        "paper/draft.md",
        "replication/aea_data_package_manifest.yml",
    ]
    rows: list[str] = []
    for rel in semantic_files:
        path = root / rel
        if path.is_file():
            rows.append(f"{rel}:{_hash_file(path)}")
        elif path.exists():
            rows.append(f"{rel}:exists")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _frontier_hash(action: NextAction, spec_data: dict[str, Any]) -> str:
    rows = [
        str(action.lane),
        str(action.status_label),
        str(spec_data.get("id", "")),
        str(spec_data.get("kind", "")),
        str(spec_data.get("effect_class", "")),
        str(spec_data.get("requires_decision", "")),
        str(action.source),
    ]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _action_signature(spec_data: dict[str, Any]) -> str:
    rows = [
        str(spec_data.get("id", "")),
        str(spec_data.get("kind", "")),
        str(spec_data.get("effect_class", "")),
        str(spec_data.get("command", "")),
        str(spec_data.get("idempotency_key", "")),
    ]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _estimated_provider_calls(spec_data: dict[str, Any]) -> int:
    if spec_data.get("effect_class") == "task_run":
        return 1
    return 0


def _estimated_cost_usd(spec_data: dict[str, Any]) -> float:
    budget = spec_data.get("resource_budget") or {}
    try:
        return float(budget.get("estimated_cost_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _run_post_run_hooks(root: Path, spec_data: dict[str, Any], timeout_seconds: int) -> str:
    hooks = spec_data.get("post_run_hooks") or []
    if not isinstance(hooks, list):
        return "post_run_hooks_malformed"
    if "reconcile" in hooks:
        from .reconcile import run_reconcile
        report = run_reconcile(root, timeout_seconds=max(timeout_seconds, 1))
        if not report.ok:
            return "post_run_hook_failed: reconcile"
    if "session_scope" in hooks or "check:lane_scope" in hooks:
        from .session_guard import audit_session
        audit = audit_session(root)
        if audit.active and not audit.ok:
            return "post_run_hook_failed: session_scope_drift"
    return ""


def _has_placeholder(command: str) -> bool:
    placeholders = [
        "<your research idea>",
        "<topic keywords>",
        "<topic>",
        "<project>",
    ]
    return any(token in command for token in placeholders)


def _is_shelly(command: str) -> bool:
    return any(token in command for token in [";", "|", "&&", "||", "`", "$(", "\n"])


def _action_requires_authority(action: NextAction) -> bool:
    command = action.command or ""
    return bool(action.blocked) or action.lane == "human_gate" or " gate " in f" {command} "


def _is_read_only_aeros_command(parts: list[str]) -> bool:
    command = parts[3] if len(parts) > 3 else ""
    if command in NO_WRITE_AEROS_COMMANDS:
        return True
    if command in {"context", "cockpit", "next"}:
        return "--write" not in parts
    if command == "literature":
        return len(parts) > 4 and parts[4] == "status"
    if command == "stale":
        return len(parts) > 4 and parts[4] == "triage" and "--write" not in parts
    return False


def _command_args(action: NextAction, args: ControllerLoopArgs) -> tuple[list[str], str]:
    command = action.command.strip()
    if not command:
        return [], "missing command"
    if _has_placeholder(command):
        return [], "command contains a placeholder that needs human input"
    if _is_shelly(command):
        return [], "command contains shell control syntax; controller refuses to run it"
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return [], f"command cannot be parsed safely: {exc}"
    if not parts:
        return [], "empty command"
    if parts[0] in {"python", "python3"}:
        parts[0] = sys.executable
    if parts[0] != sys.executable:
        return [], "controller only executes Python/AEROS/check commands"

    is_aeros = len(parts) >= 4 and parts[1:3] == ["-m", "aeros.cli"]
    is_check_script = len(parts) >= 2 and parts[1].startswith("checks/")
    if not is_aeros and not is_check_script:
        return [], "controller only executes aeros.cli or checks/*.py commands"

    if is_check_script:
        return parts, ""

    aeros_command = parts[3] if len(parts) > 3 else ""
    if aeros_command not in SAFE_AEROS_COMMANDS:
        return [], f"aeros command {aeros_command!r} is not controller-safe"

    dry_run_command = "--dry-run" in parts
    if aeros_command == "iterate":
        if args.allow_task_runs:
            parts = [part for part in parts if part != "--dry-run"]
            if args.task_timeout is not None and "--task-timeout" not in parts:
                parts.extend(["--task-timeout", str(args.task_timeout)])
            if args.max_retries is not None and "--max-retries" not in parts:
                parts.extend(["--max-retries", str(args.max_retries)])
            return parts, ""
        if dry_run_command:
            return parts, ""
        return [], "real iterate/task runs require --allow-task-runs"

    if _is_read_only_aeros_command(parts):
        return parts, ""
    if dry_run_command:
        return parts, ""
    return [], f"aeros command {aeros_command!r} requires --dry-run unless a narrower executor is added"


def _step_record(step: int, action: NextAction, *, status: str, reason: str = "", rc: int | None = None,
                 artifact_changed: bool = False, substantive_changed: bool = False,
                 semantic_progress: bool = False,
                 primary_stop_reason: str = "",
                 semantic_state_hash_before: str = "",
                 semantic_state_hash_after: str = "",
                 frontier_hash: str = "",
                 action_signature: str = "",
                 action_spec: dict[str, Any] | None = None) -> dict[str, Any]:
    action_data = action.to_dict()
    if action_spec is not None:
        action_data["action_spec"] = action_spec
    return {
        "step": step,
        "status": status,
        "reason": reason,
        "return_code": rc,
        "artifact_changed": artifact_changed,
        "substantive_changed": substantive_changed,
        "semantic_progress": semantic_progress,
        "primary_stop_reason": primary_stop_reason or reason,
        "semantic_state_hash_before": semantic_state_hash_before,
        "semantic_state_hash_after": semantic_state_hash_after,
        "frontier_hash": frontier_hash,
        "action_signature": action_signature,
        "action": action_data,
        "action_spec": action_data.get("action_spec"),
    }


def run_until(root: Path, args: ControllerLoopArgs) -> tuple[int, list[dict[str, Any]]]:
    until = (args.until or "human-gate").strip()
    if until not in UNTIL_CHOICES:
        raise ValueError(f"invalid --until {until!r}; expected one of {sorted(UNTIL_CHOICES)}")
    lane = (args.lane or "").strip()
    if lane not in LANE_CHOICES:
        raise ValueError(f"invalid --lane {lane!r}")
    max_steps = max(int(args.max_steps or 1), 1)
    no_progress_limit = max(int(args.no_progress_limit or 1), 1)
    max_wall_time = max(int(args.max_wall_time_seconds or 1), 1)
    max_provider_calls = max(int(args.max_provider_calls or 0), 0)
    max_cost_usd = max(float(args.max_cost_usd or 0.0), 0.0)

    records: list[dict[str, Any]] = []
    no_progress_count = 0
    provider_calls_used = 0
    cost_used = 0.0
    seen_cycles: set[tuple[str, str, str]] = set()
    started_at = time.monotonic()

    for step in range(1, max_steps + 1):
        action = compute_next_action(root, lane=lane)
        spec_data = (action.to_dict().get("action_spec") or {})
        semantic_before = _semantic_state_hash(root)
        frontier = _frontier_hash(action, spec_data)
        signature = _action_signature(spec_data)
        cycle_key = (semantic_before, frontier, signature)
        if cycle_key in seen_cycles:
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason="controller_cycle_detected",
                primary_stop_reason="controller_cycle_detected",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records
        seen_cycles.add(cycle_key)

        spec_failures = validate_action_spec(spec_data)
        if spec_failures:
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason="invalid_action_spec: " + "; ".join(spec_failures),
                primary_stop_reason="invalid_action_spec",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records

        if time.monotonic() - started_at >= max_wall_time:
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason="wall_time_budget_exceeded",
                primary_stop_reason="wall_time_budget_exceeded",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records

        projected_provider_calls = provider_calls_used + _estimated_provider_calls(spec_data)
        if projected_provider_calls > max_provider_calls:
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason="provider_call_budget_exceeded",
                primary_stop_reason="provider_call_budget_exceeded",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records

        projected_cost = cost_used + _estimated_cost_usd(spec_data)
        if projected_cost > max_cost_usd:
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason="cost_budget_exceeded",
                primary_stop_reason="cost_budget_exceeded",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records

        effect_class = str(spec_data.get("effect_class", ""))
        if _action_requires_authority(action) or effect_class in {"blocked", "human_decision"} or _has_placeholder(action.command):
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason="action_spec_requires_decision",
                primary_stop_reason="action_spec_requires_decision",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records

        command_args, refusal = _command_args(action, args)
        if refusal:
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason=refusal,
                primary_stop_reason="command_refused",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records

        if args.dry_run:
            records.append(_step_record(
                step,
                action,
                status="would_run",
                reason="dry-run controller",
                primary_stop_reason="dry_run",
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 0, records

        before = _substantive_snapshot(root)
        remaining_wall_time = max(1, int(max_wall_time - (time.monotonic() - started_at)))
        try:
            proc = subprocess.run(  # noqa: S603 - argv-only allowlisted commands
                command_args,
                cwd=root,
                text=True,
                timeout=remaining_wall_time,
            )
        except subprocess.TimeoutExpired:
            semantic_after = _semantic_state_hash(root)
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason="wall_time_budget_exceeded_during_command",
                primary_stop_reason="wall_time_budget_exceeded",
                artifact_changed=before != _substantive_snapshot(root),
                semantic_progress=semantic_after != semantic_before,
                semantic_state_hash_before=semantic_before,
                semantic_state_hash_after=semantic_after,
                frontier_hash=frontier,
                action_signature=signature,
                action_spec=spec_data,
            ))
            return 124, records
        after = _substantive_snapshot(root)
        semantic_after = _semantic_state_hash(root)
        artifact_changed = before != after
        semantic_progress = semantic_after != semantic_before
        substantive_changed = semantic_progress and action.status_label in {"SUBSTANTIVE_PRODUCED", "SUBSTANTIVE_DONE"}
        provider_calls_used = projected_provider_calls
        cost_used = projected_cost
        records.append(_step_record(
            step,
            action,
            status="ran",
            rc=proc.returncode,
            artifact_changed=artifact_changed,
            substantive_changed=substantive_changed,
            semantic_progress=semantic_progress,
            semantic_state_hash_before=semantic_before,
            semantic_state_hash_after=semantic_after,
            frontier_hash=frontier,
            action_signature=signature,
            action_spec=spec_data,
        ))
        if proc.returncode != 0:
            return proc.returncode, records
        hook_failure = _run_post_run_hooks(root, spec_data, remaining_wall_time)
        if hook_failure:
            records[-1]["primary_stop_reason"] = hook_failure
            records[-1]["reason"] = hook_failure
            return 1, records

        if semantic_progress:
            no_progress_count = 0
        else:
            no_progress_count += 1

        if no_progress_count >= no_progress_limit:
            records[-1]["primary_stop_reason"] = "no_semantic_progress"
            return 0, records
        if until == "max-steps" and step >= max_steps:
            records[-1]["primary_stop_reason"] = "max_actions_reached"
            return 0, records
        if until == "blocked":
            continue
        if until == "human-gate":
            continue

    return 0, records


def format_run_until(records: list[dict[str, Any]]) -> str:
    lines = ["AEROS bounded controller run"]
    if not records:
        lines.append("no steps recorded")
        return "\n".join(lines)
    for record in records:
        action = record.get("action") or {}
        lines.append(
            f"- step {record.get('step')}: {record.get('status')} "
            f"lane={action.get('lane')} label={action.get('status_label')} "
            f"reason={record.get('reason') or 'ok'}"
        )
        lines.append(f"  action: {action.get('recommended_next_action')}")
        spec = record.get("action_spec") or action.get("action_spec") or {}
        if spec:
            lines.append(
                f"  action_spec: {spec.get('id')} kind={spec.get('kind')} "
                f"effect={spec.get('effect_class')} requires_decision={spec.get('requires_decision')}"
            )
        lines.append(f"  command: {action.get('command')}")
        if record.get("return_code") is not None:
            lines.append(f"  return_code: {record.get('return_code')}")
        lines.append(f"  artifact_changed: {record.get('artifact_changed')}")
        lines.append(f"  semantic_progress: {record.get('semantic_progress')}")
        lines.append(f"  substantive_changed: {record.get('substantive_changed')}")
        if record.get("primary_stop_reason"):
            lines.append(f"  primary_stop_reason: {record.get('primary_stop_reason')}")
    lines.append("does_not_prove: controller execution does not approve gates, upgrade claims, certify identification, or prove paper readiness")
    return "\n".join(lines)


def run_until_json(records: list[dict[str, Any]]) -> str:
    return json.dumps({"records": records}, indent=2, ensure_ascii=False)
