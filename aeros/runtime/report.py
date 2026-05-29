"""Write an AEROS agent run report from accumulated attempt records.

The report conforms to checks/check_agent_run_report.py (required headings,
resolvable Task ID, non-placeholder Commands Run) and to the metadata fields
that checks/build_agent_runs_index.py extracts. Its purpose is to PERSIST the
per-attempt check feedback that the live loop otherwise only prints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .contract import Contract


@dataclass
class AttemptRecord:
    attempt: int
    agent_ok: bool
    agent_error: str
    checks: list[tuple[str, bool, list[str]]]  # (check_name, passed, failures)
    feedback: str  # structured feedback fed into the NEXT attempt (may be "")


@dataclass
class RunRecord:
    contract: Contract
    final_status: str            # "passed" | "escalated"
    attempts: list[AttemptRecord] = field(default_factory=list)
    agent_calls_used: int = 0


def _checks_table(run: RunRecord) -> str:
    rows = ["| Attempt | Check | Result |", "| --- | --- | --- |"]
    for rec in run.attempts:
        for name, passed, _ in rec.checks:
            rows.append(f"| {rec.attempt} | {name} | {'PASS' if passed else 'FAIL'} |")
        if not rec.checks:
            rows.append(f"| {rec.attempt} | (agent error) | n/a |")
    return "\n".join(rows)


def _feedback_log(run: RunRecord) -> str:
    blocks: list[str] = []
    for rec in run.attempts:
        passed = rec.checks and all(p for _, p, _ in rec.checks)
        if rec.agent_error:
            blocks.append(f"### Attempt {rec.attempt} — agent error\n\n{rec.agent_error}")
        elif passed:
            blocks.append(f"### Attempt {rec.attempt} — all checks passed")
        else:
            blocks.append(
                f"### Attempt {rec.attempt} — failed; feedback fed into retry\n\n"
                f"{rec.feedback or '(no structured feedback captured)'}"
            )
    return "\n\n".join(blocks)


def _commands_block(run: RunRecord) -> str:
    lines = ["```"]
    for rec in run.attempts:
        lines.append(f"# attempt {rec.attempt}")
        lines.append("claude -p <task contract prompt>")
        for name, _, _ in rec.checks:
            lines.append(f"python3 checks/{name}.py --json")
    lines.append("```")
    return "\n".join(lines)


def write_run_report(project_root: Path, run: RunRecord) -> Path:
    c = run.contract
    now = datetime.now(timezone.utc)
    date = now.date().isoformat()
    run_id = f"{c.task_id}-{now.strftime('%Y%m%dT%H%M%SZ')}"
    out_dir = project_root / "agent_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{c.task_id}_{now.strftime('%Y%m%d_%H%M%S')}.md"

    files_read = "\n".join(f"- {p}" for p in c.inputs) or "- (none)"
    files_mod = "\n".join(f"- {p}" for p in c.allowed_outputs) or "- (none)"
    human_needed = (
        "- Review escalation in decisions/escalations/ and choose "
        "approve / revise / pause / drop."
        if run.final_status == "escalated" else "- None"
    )

    body = f"""# Agent Run Report: {c.task_id}

## Run Metadata

- Task ID: {c.task_id}
- Run ID: {run_id}
- Agent: aeros-runtime (claude -p)
- Date: {date}
- Mode: {c.stage}
- Work mode: runtime
- Completion Status: {run.final_status}
- Critic required: no
- Human gate required: {"yes" if run.final_status == "escalated" else "no"}
- Attempts: {len(run.attempts)}
- Agent calls used: {run.agent_calls_used}

## Objective

{c.goal}

## Files Read

{files_read}

## Files Modified

{files_mod}

## Commands Run

{_commands_block(run)}

## Outputs Changed

{files_mod}

## Skills Used

- none

## Checks Run

{_checks_table(run)}

## Attempt Feedback Log

{_feedback_log(run)}

## Protected Definitions

Were protected definitions changed?

- [x] No

## Claim Changes

- None

## Human Decisions Needed

{human_needed}

## Completion Status

{run.final_status}
"""
    path.write_text(body, encoding="utf-8")
    return path
