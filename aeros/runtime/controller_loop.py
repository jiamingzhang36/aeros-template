"""Bounded autonomous controller loop for AEROS.

The loop consumes the deterministic ``aeros next`` projection. It is not an
LLM planner and it does not create new authority. By default it executes only
safe/zero-cost preview or check commands; real task runs require an explicit
``--allow-task-runs`` opt-in.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any

from .action_spec import validate_action_spec
from .episode_watchdog import (
    EpisodeStep,
    WatchdogPolicy,
    action_fingerprint,
    artifact_hashes,
    artifact_state_fingerprint,
    assess_after,
    assess_before,
    blocker_fingerprints,
    changed_artifacts,
    frontier_fingerprint,
    input_fingerprint,
    load_episode_steps,
    new_episode_id,
    record_episode_step,
    research_value_events_since,
    semantic_state_fingerprint,
    tool_result_fingerprint,
)
from .next_action import NextAction, compute_next_action


UNTIL_CHOICES = {"human-gate", "blocked", "no-progress", "max-steps"}
LANE_CHOICES = {"", "data", "literature", "method", "analysis", "claim", "writing", "compliance", "harness"}

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
    "recover",
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


def _substantive_snapshot(root: Path) -> str:
    return artifact_state_fingerprint(root)


def _semantic_state_hash(root: Path) -> str:
    return semantic_state_fingerprint(root)


def _frontier_hash(action: NextAction, spec_data: dict[str, Any]) -> str:
    return frontier_fingerprint(action.to_dict(), spec_data)


def _action_signature(spec_data: dict[str, Any]) -> str:
    return action_fingerprint(spec_data)


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


def _estimated_tokens(spec_data: dict[str, Any]) -> tuple[int, int]:
    budget = spec_data.get("resource_budget") or {}
    try:
        input_tokens = int(budget.get("estimated_input_tokens") or 0)
        output_tokens = int(budget.get("estimated_output_tokens") or 0)
    except (TypeError, ValueError):
        return 0, 0
    return max(input_tokens, 0), max(output_tokens, 0)


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

    if aeros_command == "recover":
        if "--check" in parts:
            return parts, ""
        return [], "recover without --check is not controller-safe"

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
                 input_fingerprint_value: str = "",
                 expected_artifacts: tuple[str, ...] = (),
                 accepted_artifacts: tuple[str, ...] = (),
                 research_value_events: tuple[dict[str, Any], ...] = (),
                 tokens_input: int = 0,
                 tokens_output: int = 0,
                 cost: float = 0.0,
                 wall_time: float = 0.0,
                 watchdog: dict[str, Any] | None = None,
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
        "input_fingerprint": input_fingerprint_value,
        "expected_artifacts": list(expected_artifacts),
        "accepted_artifacts": list(accepted_artifacts),
        "research_value_events": list(research_value_events),
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost": cost,
        "wall_time": wall_time,
        "watchdog": watchdog or {},
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
    provider_calls_used = 0
    cost_used = 0.0
    started_at = time.monotonic()
    episode_id = new_episode_id(root, lane)
    episode_history = load_episode_steps(root)
    watchdog_policy = WatchdogPolicy(no_state_change_limit=max(no_progress_limit, 2))

    for step in range(1, max_steps + 1):
        action = compute_next_action(root, lane=lane)
        spec_data = (action.to_dict().get("action_spec") or {})
        semantic_before = _semantic_state_hash(root)
        frontier = _frontier_hash(action, spec_data)
        signature = _action_signature(spec_data)
        input_hash = input_fingerprint(root, spec_data)
        expected_artifacts = tuple(str(item) for item in spec_data.get("expected_outputs") or [] if str(item).strip())
        blockers_before = blocker_fingerprints(root)
        objective_id = str(spec_data.get("campaign_id") or action.source or action.lane or frontier)
        assistant_text = f"{action.recommended_next_action}\n{action.why_this_next}"
        draft_step = EpisodeStep(
            episode_id=episode_id,
            objective_id=objective_id,
            frontier_id=frontier,
            step=step,
            action_signature=signature,
            input_fingerprint=input_hash,
            state_fingerprint_before=semantic_before,
            state_fingerprint_after=semantic_before,
            expected_artifacts=expected_artifacts,
            blockers_before=blockers_before,
            blockers_after=blockers_before,
            assistant_text=assistant_text,
        )
        preflight_watchdog = assess_before(root, episode_history, draft_step, watchdog_policy)
        if preflight_watchdog.stop:
            records.append(_step_record(
                step,
                action,
                status="stopped",
                reason=preflight_watchdog.reason,
                primary_stop_reason=preflight_watchdog.reason,
                semantic_state_hash_before=semantic_before,
                frontier_hash=frontier,
                action_signature=signature,
                input_fingerprint_value=input_hash,
                expected_artifacts=expected_artifacts,
                accepted_artifacts=preflight_watchdog.previous_artifacts,
                watchdog=preflight_watchdog.to_dict(),
                action_spec=spec_data,
            ))
            return 0, records

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
        expected_before = artifact_hashes(root, expected_artifacts)
        action_started_epoch = time.time()
        action_started_monotonic = time.monotonic()
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
            accepted_hashes = changed_artifacts(root, expected_artifacts, expected_before)
            watchdog_step = EpisodeStep(
                episode_id=episode_id,
                objective_id=objective_id,
                frontier_id=frontier,
                step=step,
                action_signature=signature,
                input_fingerprint=input_hash,
                state_fingerprint_before=semantic_before,
                state_fingerprint_after=semantic_after,
                expected_artifacts=expected_artifacts,
                accepted_artifacts=tuple(accepted_hashes),
                accepted_artifact_hashes=accepted_hashes,
                research_value_events=research_value_events_since(root, action_started_epoch),
                blockers_before=blockers_before,
                blockers_after=blocker_fingerprints(root),
                tool_result_hash=tool_result_fingerprint(124, semantic_after, accepted_hashes),
                error_code="TIMEOUT",
                cost=_estimated_cost_usd(spec_data),
                wall_time=time.monotonic() - action_started_monotonic,
                assistant_text=assistant_text,
            )
            watchdog_decision = assess_after(episode_history, watchdog_step, watchdog_policy)
            record_episode_step(root, watchdog_step, watchdog_decision)
            episode_history.append(watchdog_step)
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
                input_fingerprint_value=input_hash,
                expected_artifacts=expected_artifacts,
                accepted_artifacts=watchdog_step.accepted_artifacts,
                research_value_events=watchdog_step.research_value_events,
                cost=watchdog_step.cost,
                wall_time=watchdog_step.wall_time,
                watchdog=watchdog_decision.to_dict(),
                action_spec=spec_data,
            ))
            return 124, records
        hook_failure = ""
        if proc.returncode == 0:
            hook_failure = _run_post_run_hooks(root, spec_data, remaining_wall_time)
        after = _substantive_snapshot(root)
        semantic_after = _semantic_state_hash(root)
        artifact_changed = before != after
        semantic_progress = semantic_after != semantic_before
        substantive_changed = semantic_progress and action.status_label in {"SUBSTANTIVE_PRODUCED", "SUBSTANTIVE_DONE"}
        provider_calls_used = projected_provider_calls
        cost_used = projected_cost
        accepted_hashes = changed_artifacts(root, expected_artifacts, expected_before)
        value_events = research_value_events_since(root, action_started_epoch)
        tokens_input, tokens_output = _estimated_tokens(spec_data)
        error_code = f"EXIT_{proc.returncode}" if proc.returncode != 0 else hook_failure
        watchdog_step = EpisodeStep(
            episode_id=episode_id,
            objective_id=objective_id,
            frontier_id=frontier,
            step=step,
            action_signature=signature,
            input_fingerprint=input_hash,
            state_fingerprint_before=semantic_before,
            state_fingerprint_after=semantic_after,
            expected_artifacts=expected_artifacts,
            accepted_artifacts=tuple(accepted_hashes),
            accepted_artifact_hashes=accepted_hashes,
            research_value_events=value_events,
            blockers_before=blockers_before,
            blockers_after=blocker_fingerprints(root),
            tool_result_hash=tool_result_fingerprint(proc.returncode, semantic_after, accepted_hashes),
            error_code=error_code,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=_estimated_cost_usd(spec_data),
            wall_time=time.monotonic() - action_started_monotonic,
            assistant_text=assistant_text,
        )
        watchdog_decision = assess_after(episode_history, watchdog_step, watchdog_policy)
        record_episode_step(root, watchdog_step, watchdog_decision)
        episode_history.append(watchdog_step)
        stop_reason = ""
        if proc.returncode != 0:
            stop_reason = watchdog_decision.reason if watchdog_decision.stop else "command_failed"
        elif hook_failure:
            stop_reason = hook_failure
        elif watchdog_decision.stop:
            stop_reason = watchdog_decision.reason
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
            input_fingerprint_value=input_hash,
            expected_artifacts=expected_artifacts,
            accepted_artifacts=watchdog_step.accepted_artifacts,
            research_value_events=value_events,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=watchdog_step.cost,
            wall_time=watchdog_step.wall_time,
            watchdog=watchdog_decision.to_dict(),
            action_spec=spec_data,
        ))
        if stop_reason:
            records[-1]["primary_stop_reason"] = stop_reason
            records[-1]["reason"] = stop_reason
        if proc.returncode != 0:
            return proc.returncode, records
        if hook_failure:
            return 1, records
        if watchdog_decision.stop:
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
        watchdog = record.get("watchdog") or {}
        if watchdog:
            lines.append(
                f"  watchdog: {watchdog.get('reason')} disposition={watchdog.get('disposition')}"
            )
    lines.append("does_not_prove: controller execution does not approve gates, upgrade claims, certify identification, or prove paper readiness")
    return "\n".join(lines)


def run_until_json(records: list[dict[str, Any]]) -> str:
    return json.dumps({"records": records}, indent=2, ensure_ascii=False)
