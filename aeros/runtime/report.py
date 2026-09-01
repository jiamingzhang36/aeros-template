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
from .completion_review import classify_completion_review


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
    run_calls: int = 0           # agent calls in THIS run (not cumulative)
    run_cost_usd: float = 0.0
    run_input_tokens: int = 0
    run_output_tokens: int = 0
    # Provenance schema (STARD-AI / PROV-AGENT): record enough to reproduce and audit.
    agent_provider: str = ""
    agent_model: str = ""
    temperature: float | None = None
    tools_used: list[str] = field(default_factory=list)
    skill_receipt_path: str = ""
    context_episode_id: str = ""
    context_hash: str = ""
    context_binding_path: str = ""


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
    review_plan = classify_completion_review(c, c.allowed_outputs)
    now = datetime.now(timezone.utc)
    date = now.date().isoformat()
    run_id = f"{c.task_id}-{now.strftime('%Y%m%dT%H%M%SZ')}"
    out_dir = project_root / "agent_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{c.task_id}_{now.strftime('%Y%m%d_%H%M%S')}.md"

    files_read = "\n".join(f"- {p}" for p in c.inputs) or "- (none)"
    allowed_outputs = "\n".join(f"- {p}" for p in c.allowed_outputs) or "- (none)"
    any_agent_completed = any(rec.agent_ok for rec in run.attempts)
    if any_agent_completed:
        files_mod = (
            "- Not mechanically diffed by the runtime; inspect allowed outputs below "
            "and the attempt feedback log."
        )
    else:
        files_mod = "- (none observed; agent did not complete)"
    human_needed = (
        "- Review escalation in decisions/escalations/ and choose "
        "approve / revise / pause / drop."
        if run.final_status == "escalated" else "- None"
    )
    # Honest usage rendering: some providers (e.g. codex-cli) do not report token
    # or cost usage back to the runtime. Showing "$0.0000 / 0 in / 0 out" for a run
    # that actually did substantial work falsely reads as a no-op and erodes trust
    # in the audit trail. Distinguish "not reported" from a real zero.
    usage_reported = bool(run.run_input_tokens or run.run_output_tokens or run.run_cost_usd)
    if any_agent_completed and not usage_reported:
        cost_str = f"not reported by provider ({run.agent_provider or 'agent'})"
        tokens_str = f"not reported by provider ({run.agent_provider or 'agent'})"
    else:
        cost_str = f"${run.run_cost_usd:.4f}"
        tokens_str = f"{run.run_input_tokens} in / {run.run_output_tokens} out"

    body = f"""# Agent Run Report: {c.task_id}

## Run Metadata

- Task ID: {c.task_id}
- Run ID: {run_id}
- Agent: aeros-runtime (claude -p)
- Date: {date}
- Mode: {c.stage}
- Work mode: runtime
- Completion Status: {run.final_status}
- Context episode: {run.context_episode_id or 'not recorded'}
- Context binding: {run.context_binding_path or 'not recorded'}
- Critic required: {"yes" if review_plan.required else "no"}
- Completion review risk: {review_plan.risk}
- Human gate required: {"yes" if review_plan.human_gate_required or run.final_status == "escalated" else "no"}
- Attempts: {len(run.attempts)}
- Agent calls (this run): {run.run_calls}
- Cost (this run): {cost_str}
- Tokens (this run): {tokens_str}
- Provenance: provider={run.agent_provider or 'n/a'}, model={run.agent_model or 'n/a'}, temperature={run.temperature if run.temperature is not None else 'n/a'}
- Tools used: {", ".join(run.tools_used) if run.tools_used else "n/a"}
- Skill invocation receipt: {run.skill_receipt_path or 'n/a'}

## Objective

{c.goal}

## Files Read

{files_read}

## Files Modified

{files_mod}

## Allowed Outputs

{allowed_outputs}

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
