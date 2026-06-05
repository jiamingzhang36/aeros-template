"""Drive a Claude Code agent via the `claude -p` headless CLI.

The kernel stays model-agnostic: it builds a prompt from the task contract and
hands it to whatever `claude` binary is on PATH. Claude Code automatically loads
the project's .claude/settings.json (including the data/raw write-block hook),
so permission enforcement happens at the agent layer, not on trust.
"""

from __future__ import annotations

import json
import os
import re
import select
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import request

import yaml

from .contract import Contract


def _load_corrections(project_root: Path, contract: Contract) -> str:
    """Return injectable past-correction lessons whose scope matches the contract.

    This is the evolving-constraint mechanism: agent-lesson entries from the
    correction ledger are fed into the prompt so the agent does not repeat a
    mistake the harness already corrected.
    """
    ledger = project_root / "harness" / "correction_ledger.yml"
    if not ledger.exists():
        return ""
    try:
        data = yaml.safe_load(ledger.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return ""
    scopes = set(contract.correction_scopes)
    lessons: list[str] = []
    for c in data.get("corrections", []) or []:
        if not isinstance(c, dict) or c.get("type") != "agent-lesson":
            continue
        if scopes.intersection(set(c.get("scope", []) or [])):
            lessons.append(f"- [{c.get('id','?')}] {c.get('lesson','').strip()}")
    if not lessons:
        return ""
    return ("## Past corrections — do not repeat these mistakes\n"
            + "\n".join(lessons))


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


def _agent_provider(project_root: Path) -> str:
    """Select the worker backend.

    Env wins so validation runs can switch provider without editing a project:
    AEROS_AGENT_PROVIDER=claude|openai|manual.
    """
    provider = os.getenv("AEROS_AGENT_PROVIDER", "").strip().lower()
    if provider:
        return provider
    manifest = project_root / "project_manifest.yml"
    if manifest.exists():
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        automation = data.get("automation", {}) if isinstance(data, dict) else {}
        if isinstance(automation, dict):
            provider = str(automation.get("agent_provider", "") or "").strip().lower()
            if provider:
                return provider
    return "claude"


def _agent_permission_flags(project_root: Path) -> list[str]:
    """Permission mode for the headless `claude -p` worker.

    In headless mode a tool that needs approval has no TTY to prompt on, so the
    worker hangs until timeout. The worker therefore runs with an explicit
    permission mode. Safety does NOT come from interactive prompts here -- it
    comes from the project .claude/settings.json deny-hooks (e.g. the data/raw
    write block) and the allowed_outputs enforcement. Configurable via
    AEROS_AGENT_PERMISSION_MODE or automation.agent_permission_mode.

    Values: acceptEdits (default; auto-accept file writes, other tools gated) |
    bypass / dangerous (--dangerously-skip-permissions, for fully unattended runs
    that also need bash) | default | plan.
    """
    mode = os.getenv("AEROS_AGENT_PERMISSION_MODE", "").strip().lower()
    if not mode:
        manifest = project_root / "project_manifest.yml"
        if manifest.exists():
            try:
                data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                data = {}
            automation = data.get("automation", {}) if isinstance(data, dict) else {}
            if isinstance(automation, dict):
                mode = str(automation.get("agent_permission_mode", "") or "").strip().lower()
    if not mode:
        mode = "acceptedits"
    if mode in {"bypass", "dangerous", "dangerously-skip-permissions", "skip"}:
        return ["--dangerously-skip-permissions"]
    canonical = {"acceptedits": "acceptEdits", "default": "default", "plan": "plan"}.get(mode)
    if canonical:
        return ["--permission-mode", canonical]
    return ["--permission-mode", "acceptEdits"]


def _task_id_from_prompt(prompt: str) -> str:
    match = re.search(r"executing task\s+([A-Za-z0-9_.-]+)", prompt)
    return match.group(1) if match else "task"


def _allowed_outputs_from_prompt(prompt: str) -> list[str]:
    match = re.search(
        r"## You may write ONLY these files\n(?P<body>.*?)(?:\n\n## |\Z)",
        prompt,
        flags=re.S,
    )
    if not match:
        return []
    out: list[str] = []
    for line in match.group("body").splitlines():
        line = line.strip()
        if line.startswith("- "):
            rel = line[2:].strip()
            if rel:
                out.append(rel)
    return out


def _allowed_output_match(rel: str, allowed_outputs: list[str]) -> bool:
    """A write is allowed if it equals an allowed output exactly, OR falls under
    an allowed output that names a directory (trailing '/'). Without the prefix
    rule, contracts that allow a directory (e.g. 'agent_runs/') wrongly reject
    every file inside it."""
    for a in allowed_outputs:
        a = a.strip().lstrip("/")
        if rel == a:
            return True
        if a.endswith("/") and (rel.startswith(a) or rel == a.rstrip("/")):
            return True
    return False


def _safe_output_path(project_root: Path, rel: str, allowed_outputs: list[str]) -> Path:
    rel = rel.strip().lstrip("/")
    if not _allowed_output_match(rel, allowed_outputs):
        raise ValueError(f"provider attempted to write non-allowed output: {rel}")
    path = (project_root / rel).resolve()
    root = project_root.resolve()
    if root not in [path, *path.parents]:
        raise ValueError(f"provider attempted to write outside project root: {rel}")
    return path


def _write_manual_prompt(prompt: str, project_root: Path) -> Path:
    task_id = _task_id_from_prompt(prompt)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = project_root / "outputs" / "pending_tasks"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task_id}_{stamp}.md"
    path.write_text(
        "# Manual AEROS Task Prompt\n\n"
        "AEROS_AGENT_PROVIDER=manual wrote this prompt instead of calling an agent.\n\n"
        "Fill the allowed output files, then run `aeros check <task-contract>`.\n\n"
        "```text\n"
        f"{prompt}\n"
        "```\n",
        encoding="utf-8",
    )
    return path


def _extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("provider response JSON must be an object")
    return data


def _apply_file_response(project_root: Path, allowed_outputs: list[str], text: str) -> None:
    data = _extract_json_object(text)
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("provider response must include non-empty files[]")
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("each files[] item must be an object")
        rel = str(item.get("path", "") or "").strip()
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError(f"file {rel or '?'} content must be a string")
        path = _safe_output_path(project_root, rel, allowed_outputs)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _run_openai_agent(prompt: str, project_root: Path, timeout: int) -> AgentResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return AgentResult(False, "", "OPENAI_API_KEY is not set.")
    model = os.getenv("AEROS_OPENAI_MODEL", "gpt-5").strip() or "gpt-5"
    allowed_outputs = _allowed_outputs_from_prompt(prompt)
    file_instruction = (
        "\n\n## Output protocol for this provider\n"
        "Return ONLY valid JSON with this shape:\n"
        "{\"files\":[{\"path\":\"relative/path/from_allowed_outputs\",\"content\":\"full file content\"}]}\n"
        "Every path must be one of the allowed outputs. Do not include markdown fences.\n"
    )
    payload = {
        "model": model,
        "input": prompt + file_instruction,
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return AgentResult(False, "", f"OpenAI provider HTTP {exc.code}: {detail}")
    except (urlerror.URLError, TimeoutError) as exc:
        return AgentResult(False, "", f"OpenAI provider failed: {exc}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AgentResult(False, raw, "OpenAI provider returned non-JSON response")

    output_text = data.get("output_text")
    if not output_text:
        chunks: list[str] = []
        for item in data.get("output", []) or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []) or []:
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                    chunks.append(str(content.get("text", "")))
        output_text = "\n".join(chunks).strip()
    if not output_text:
        return AgentResult(False, raw, "OpenAI provider returned no output text")

    try:
        _apply_file_response(project_root, allowed_outputs, output_text)
    except Exception as exc:  # noqa: BLE001
        return AgentResult(False, output_text, f"OpenAI provider file application failed: {exc}")

    usage = data.get("usage", {}) or {}
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    return AgentResult(
        True,
        output_text,
        "",
        cost_usd=0.0,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


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
    corrections = _load_corrections(project_root, contract) if project_root is not None else ""
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
                ("<<CORRECTIONS>>", corrections),
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
    ]
    if corrections:
        parts += ["", corrections]
    parts += [
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
    provider = _agent_provider(project_root)
    if provider == "manual":
        path = _write_manual_prompt(prompt, project_root)
        return AgentResult(
            False,
            "",
            f"manual provider wrote prompt to {path.relative_to(project_root)}",
        )
    if provider == "openai":
        return _run_openai_agent(prompt, project_root, timeout)
    if provider != "claude":
        return AgentResult(
            False,
            "",
            f"unknown AEROS_AGENT_PROVIDER {provider!r}; expected claude, openai, or manual",
        )

    binary = shutil.which("claude")
    if not binary:
        return AgentResult(False, "", "`claude` CLI not found on PATH.")
    cmd = [binary, "-p", prompt, "--output-format", "stream-json", "--verbose"]
    cmd += _agent_permission_flags(project_root)
    if max_budget_usd is not None and max_budget_usd > 0:
        # Hard per-call dollar cap (claude --max-budget-usd). This is what makes
        # max_dollars an enforceable ceiling instead of a between-calls guardrail:
        # a single runaway call can no longer overshoot the budget.
        cmd += ["--max-budget-usd", f"{max_budget_usd:.2f}"]
    started = time.monotonic()
    last_heartbeat = started
    output_lines: list[str] = []
    final: dict | None = None
    rate_limited = False
    _dbg = os.getenv("AEROS_DEBUG_AGENT", "").strip() not in {"", "0", "false"}
    if _dbg:
        print(f"[agent-debug] cmd: {' '.join(repr(x) if ' ' in x else x for x in cmd[:6])} "
              f"... (+{len(cmd)-6} args)  total_len(prompt)={len(prompt)}", flush=True)
        print(f"[agent-debug] full flags: {[a for a in cmd if a.startswith('--')]}", flush=True)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env=_agent_env(), bufsize=1,
            # `claude -p` reads stdin (to support `echo x | claude -p`). If the
            # autonomous loop is launched with an open-but-empty stdin (no TTY,
            # e.g. a background daemon or `python -c`), claude blocks forever
            # waiting for input and never starts. Hand it EOF immediately.
            stdin=subprocess.DEVNULL,
        )
        assert proc.stdout is not None
        while True:
            elapsed = time.monotonic() - started
            if elapsed > timeout:
                proc.kill()
                proc.wait()
                suffix = " (rate limit event observed)" if rate_limited else ""
                return AgentResult(False, "\n".join(output_lines),
                                   f"agent timed out after {timeout}s{suffix}")
            ready, _, _ = select.select([proc.stdout], [], [], 1.0)
            if ready:
                line = proc.stdout.readline()
                if line:
                    line = line.rstrip("\n")
                    output_lines.append(line)
                    if _dbg:
                        print(f"[agent-debug] raw[{len(output_lines)}] ({int(time.monotonic()-started)}s): {line[:120]}", flush=True)
                    try:
                        event = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        print(f"[agent] {line}", flush=True)
                    else:
                        event_type = str(event.get("type", "event"))
                        if event_type == "assistant":
                            print("[agent] assistant response event", flush=True)
                        elif event_type == "result":
                            final = event
                            print("[agent] result event received", flush=True)
                        elif event_type == "rate_limit_event":
                            rate_limited = True
                            print("[agent] rate limit event observed", flush=True)
                        elif event_type in {"system", "user"}:
                            print(f"[agent] {event_type} event", flush=True)
                        else:
                            print(f"[agent] {event_type}", flush=True)
                elif proc.poll() is not None:
                    break
            if proc.poll() is not None:
                remainder = proc.stdout.read()
                if remainder:
                    for line in remainder.splitlines():
                        output_lines.append(line)
                        try:
                            event = json.loads(line)
                        except (json.JSONDecodeError, ValueError):
                            continue
                        if str(event.get("type", "")) == "result":
                            final = event
                break
            now = time.monotonic()
            if now - last_heartbeat >= 30:
                print(f"[agent] still running ({int(now - started)}s elapsed)...", flush=True)
                last_heartbeat = now
    except OSError as exc:
        return AgentResult(False, "", str(exc))

    # The CLI emits a result JSON even when it errors (is_error:true), and that
    # JSON still carries total_cost_usd. Parse it FIRST so a failed-but-billed
    # call (e.g. quota exhaustion, mid-run abort) is still accounted for -- a $0
    # cost on a failed call is exactly the "burned overnight" blind spot.
    data = final

    if data is None:
        # Non-JSON output (older CLI or hard crash): fall back to returncode.
        if proc.returncode != 0:
            return AgentResult(False, "", "\n".join(output_lines).strip())
        return AgentResult(True, "\n".join(output_lines).strip(), "")

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
