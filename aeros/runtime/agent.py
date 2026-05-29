"""Drive a Claude Code agent via the `claude -p` headless CLI.

The kernel stays model-agnostic: it builds a prompt from the task contract and
hands it to whatever `claude` binary is on PATH. Claude Code automatically loads
the project's .claude/settings.json (including the data/raw write-block hook),
so permission enforcement happens at the agent layer, not on trust.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .contract import Contract


@dataclass
class AgentResult:
    ok: bool
    output: str
    error: str


def build_prompt(contract: Contract, inputs_text: str, feedback: str | None) -> str:
    cols = contract.output_contract.get("registry_columns")
    col_block = ""
    if cols:
        col_block = (
            "\nThe primary CSV output MUST have exactly these columns, in order:\n"
            + ", ".join(cols)
            + "\n"
        )
    parts = [
        f"You are an AEROS worker agent executing task {contract.task_id} "
        f"(stage: {contract.stage}).",
        "",
        "## Goal",
        contract.goal,
        "",
        "## You may write ONLY these files",
        "\n".join(f"- {p}" for p in contract.allowed_outputs),
        "",
        "## Forbidden",
        "\n".join(f"- {a}" for a in contract.forbidden_actions),
        col_block,
        "## Inputs (read-only context)",
        inputs_text,
    ]
    if feedback:
        parts += [
            "",
            "## Your previous attempt FAILED these mechanical checks. Fix exactly these:",
            feedback,
        ]
    parts += [
        "",
        "When done, the file(s) above must pass the AEROS checks. "
        "Do not explain; just produce conformant files.",
    ]
    return "\n".join(parts)


def run_agent(prompt: str, project_root: Path, timeout: int = 1800) -> AgentResult:
    binary = shutil.which("claude")
    if not binary:
        return AgentResult(False, "", "`claude` CLI not found on PATH.")
    try:
        proc = subprocess.run(
            [binary, "-p", prompt, "--output-format", "text"],
            cwd=str(project_root), text=True, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return AgentResult(False, "", f"agent timed out after {timeout}s")
    ok = proc.returncode == 0
    return AgentResult(ok, (proc.stdout or "").strip(), (proc.stderr or "").strip())
