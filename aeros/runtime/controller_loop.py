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
from typing import Any

from .next_action import NextAction, compute_next_action


UNTIL_CHOICES = {"human-gate", "blocked", "no-progress", "budget"}
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
                 substantive_changed: bool = False) -> dict[str, Any]:
    return {
        "step": step,
        "status": status,
        "reason": reason,
        "return_code": rc,
        "substantive_changed": substantive_changed,
        "action": action.to_dict(),
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

    records: list[dict[str, Any]] = []
    no_progress_count = 0

    for step in range(1, max_steps + 1):
        action = compute_next_action(root, lane=lane)
        if _action_requires_authority(action):
            records.append(_step_record(step, action, status="stopped", reason="human_authority_or_blocker"))
            return 0, records

        command_args, refusal = _command_args(action, args)
        if refusal:
            records.append(_step_record(step, action, status="stopped", reason=refusal))
            return 0, records

        if args.dry_run:
            records.append(_step_record(step, action, status="would_run", reason="dry-run controller"))
            return 0, records

        before = _substantive_snapshot(root)
        proc = subprocess.run(command_args, cwd=root, text=True)  # noqa: S603 - argv-only allowlisted commands
        after = _substantive_snapshot(root)
        substantive_changed = before != after and action.status_label == "SUBSTANTIVE_DONE"
        records.append(_step_record(
            step,
            action,
            status="ran",
            rc=proc.returncode,
            substantive_changed=substantive_changed,
        ))
        if proc.returncode != 0:
            return proc.returncode, records

        if substantive_changed:
            no_progress_count = 0
        else:
            no_progress_count += 1

        if until == "no-progress" and no_progress_count >= no_progress_limit:
            return 0, records
        if until == "budget" and step >= max_steps:
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
        lines.append(f"  command: {action.get('command')}")
        if record.get("return_code") is not None:
            lines.append(f"  return_code: {record.get('return_code')}")
        lines.append(f"  substantive_changed: {record.get('substantive_changed')}")
    lines.append("does_not_prove: controller execution does not approve gates, upgrade claims, certify identification, or prove paper readiness")
    return "\n".join(lines)


def run_until_json(records: list[dict[str, Any]]) -> str:
    return json.dumps({"records": records}, indent=2, ensure_ascii=False)
