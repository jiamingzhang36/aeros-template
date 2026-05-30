"""Drive a Claude Code agent via the `claude -p` headless CLI.

The kernel stays model-agnostic: it builds a prompt from the task contract and
hands it to whatever `claude` binary is on PATH. Claude Code automatically loads
the project's .claude/settings.json (including the data/raw write-block hook),
so permission enforcement happens at the agent layer, not on trust.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .contract import Contract


def _agent_env() -> dict[str, str]:
    """Environment for the spawned agent.

    Claude Code refuses to launch nested inside another Claude Code session.
    When the AEROS runtime is itself invoked from within a Claude Code session,
    the spawned `claude -p` worker must not inherit CLAUDECODE, or it is blocked.
    """
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)
    return env


@dataclass
class AgentResult:
    ok: bool
    output: str
    error: str
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    num_turns: int = 0
    duration_ms: int = 0


def _column_block(contract: Contract) -> str:
    oc = contract.output_contract
    cols = oc.get("registry_columns") or oc.get("required_columns")
    if not cols:
        return ""
    return ("\nThe primary CSV output MUST have exactly these columns, in order:\n"
            + ", ".join(cols) + "\n")


def build_prompt(contract: Contract, inputs_text: str, feedback: str | None,
                 project_root: Path | None = None) -> str:
    """Assemble the agent prompt.

    If the contract names a prompt_template_file, that file is the prompt asset
    (with <<GOAL>>, <<OUTPUTS>>, <<FORBIDDEN>>, <<COLUMNS>>, <<INPUTS>>,
    <<FEEDBACK>> placeholders). Otherwise the built-in default template is used.
    This keeps the prompt a versioned, tunable asset outside the kernel code.
    """
    goal = contract.goal
    outputs = "\n".join(f"- {p}" for p in contract.allowed_outputs)
    forbidden = "\n".join(f"- {a}" for a in contract.forbidden_actions)
    columns = _column_block(contract)
    fb = ("\n## Your previous attempt FAILED these mechanical checks. Fix exactly these:\n"
          + feedback) if feedback else ""

    if contract.prompt_template_file and project_root is not None:
        tpl_path = project_root / contract.prompt_template_file
        if tpl_path.exists():
            tpl = tpl_path.read_text(encoding="utf-8")
            for token, value in (
                ("<<TASK_ID>>", contract.task_id), ("<<STAGE>>", contract.stage),
                ("<<GOAL>>", goal), ("<<OUTPUTS>>", outputs),
                ("<<FORBIDDEN>>", forbidden), ("<<COLUMNS>>", columns),
                ("<<INPUTS>>", inputs_text), ("<<FEEDBACK>>", fb),
            ):
                tpl = tpl.replace(token, value)
            return tpl

    parts = [
        f"You are an AEROS worker agent executing task {contract.task_id} "
        f"(stage: {contract.stage}).",
        "", "## Goal", goal,
        "", "## You may write ONLY these files", outputs,
        "", "## Forbidden", forbidden,
        columns,
        "## Inputs (read-only context)", inputs_text,
    ]
    if fb:
        parts.append(fb)
    parts += [
        "",
        "When done, the file(s) above must pass the AEROS checks. "
        "Do not explain; just produce conformant files.",
    ]
    return "\n".join(parts)


def run_agent(prompt: str, project_root: Path, timeout: int = 480,
              max_budget_usd: float | None = None) -> AgentResult:
    binary = shutil.which("claude")
    if not binary:
        return AgentResult(False, "", "`claude` CLI not found on PATH.")
    cmd = [binary, "-p", prompt, "--output-format", "json"]
    if max_budget_usd is not None and max_budget_usd > 0:
        # Hard per-call dollar cap (claude --max-budget-usd). This is what makes
        # max_dollars an enforceable ceiling instead of a between-calls guardrail:
        # a single runaway call can no longer overshoot the budget.
        cmd += ["--max-budget-usd", f"{max_budget_usd:.2f}"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_root), text=True, capture_output=True, timeout=timeout,
            env=_agent_env(),
        )
    except subprocess.TimeoutExpired:
        return AgentResult(False, "", f"agent timed out after {timeout}s")

    # The CLI emits a result JSON even when it errors (is_error:true), and that
    # JSON still carries total_cost_usd. Parse it FIRST so a failed-but-billed
    # call (e.g. quota exhaustion, mid-run abort) is still accounted for -- a $0
    # cost on a failed call is exactly the "burned overnight" blind spot.
    try:
        data = json.loads((proc.stdout or "").strip())
    except (json.JSONDecodeError, ValueError):
        data = None

    if data is None:
        # Non-JSON output (older CLI or hard crash): fall back to returncode.
        if proc.returncode != 0:
            return AgentResult(False, "", (proc.stderr or proc.stdout or "").strip())
        return AgentResult(True, (proc.stdout or "").strip(), "")

    usage = data.get("usage", {}) or {}
    cost = float(data.get("total_cost_usd", 0.0) or 0.0)
    in_tok = int(usage.get("input_tokens", 0) or 0)
    out_tok = int(usage.get("output_tokens", 0) or 0)
    failed = bool(data.get("is_error")) or proc.returncode != 0
    return AgentResult(
        ok=not failed,
        output="" if failed else str(data.get("result", "")),
        error=str(data.get("result", "")).strip() if failed else "",
        cost_usd=cost,
        input_tokens=in_tok,
        output_tokens=out_tok,
        num_turns=int(data.get("num_turns", 0) or 0),
        duration_ms=int(data.get("duration_ms", 0) or 0),
    )
