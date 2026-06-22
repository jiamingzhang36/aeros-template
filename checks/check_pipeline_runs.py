#!/usr/bin/env python3
"""Run the project master script placeholder or project-specific pipeline."""

from __future__ import annotations

import argparse
import os
import shlex
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml


MASTER_SCRIPT = Path("code/99_make_all.py")
MANIFEST = Path("project_manifest.yml")


def _normalize_timeout(raw_timeout: str | int | None) -> int:
    try:
        timeout = int(raw_timeout or 300)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid pipeline timeout: {raw_timeout}") from exc
    if timeout < 0:
        raise ValueError(f"invalid pipeline timeout: {raw_timeout}")
    return timeout


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (AttributeError, ProcessLookupError, PermissionError):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (AttributeError, ProcessLookupError, PermissionError):
            proc.kill()
        proc.wait()


def _command_list(raw_command: object) -> list[str]:
    if isinstance(raw_command, list):
        return [str(part) for part in raw_command if str(part)]
    if isinstance(raw_command, str) and raw_command.strip():
        return shlex.split(raw_command)
    return []


def _load_pipeline() -> dict:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    pipeline = ((manifest or {}).get("automation", {}) or {}).get("pipeline", {}) or {}
    return pipeline if isinstance(pipeline, dict) else {}


def _pipeline_python(pipeline: dict) -> str:
    runtime = pipeline.get("runtime") or {}
    if not isinstance(runtime, dict):
        runtime = {}
    return (
        os.getenv("AEROS_PIPELINE_PYTHON", "").strip()
        or str(runtime.get("python") or "").strip()
        or str(pipeline.get("python") or "").strip()
    )


def _resolve_pipeline_command(pipeline: dict) -> list[str]:
    cmd = _command_list(pipeline.get("command", []))
    runtime_python = _pipeline_python(pipeline)
    if runtime_python and cmd:
        first = Path(cmd[0]).name
        if first in {"python", "python3"}:
            cmd[0] = runtime_python
    return cmd


def _display_command(cmd: list[str]) -> str:
    return shlex.join(cmd)


def _run_streaming(cmd: list[str], timeout_seconds: int, cwd: Path | None = None) -> int:
    started = time.monotonic()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        cwd=str(cwd) if cwd else None,
        start_new_session=True,
        # Unattended: a pipeline script that reads stdin must not block the check.
        stdin=subprocess.DEVNULL,
    )

    assert proc.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    try:
        while True:
            if timeout_seconds > 0 and time.monotonic() - started > timeout_seconds:
                _terminate_process(proc)
                elapsed = time.monotonic() - started
                print(
                    f"TIMEOUT: pipeline exceeded {timeout_seconds}s "
                    f"(elapsed {elapsed:.1f}s)",
                    flush=True,
                )
                return 124

            events = selector.select(timeout=0.1)
            if events:
                line = proc.stdout.readline()
                if line:
                    print(line.rstrip("\n"), flush=True)
                    continue

            if proc.poll() is not None:
                break
    finally:
        selector.unregister(proc.stdout)

    return proc.wait()


def _smoke_check() -> int:
    if not MASTER_SCRIPT.exists():
        print(f"FAIL: missing master script {MASTER_SCRIPT}")
        return 1
    try:
        compile(MASTER_SCRIPT.read_text(encoding="utf-8"), str(MASTER_SCRIPT), "exec")
    except SyntaxError as exc:
        print(f"{exc.filename}:{exc.lineno}: {exc.msg}")
        print("FAIL: pipeline master script failed syntax check (1)")
        return 1

    pipeline = _load_pipeline()
    command = _resolve_pipeline_command(pipeline)
    cwd = pipeline.get("cwd", ".")
    runtime_python = _pipeline_python(pipeline)
    print("SMOKE: pipeline master script exists and compiles")
    if command:
        print(f"SMOKE: configured pipeline cwd={cwd} command={_display_command(command)}")
        if runtime_python:
            print(f"SMOKE: configured pipeline python={runtime_python}")
    else:
        print("SMOKE: no delegated pipeline command configured")
    print("PASS: pipeline smoke check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the project master pipeline.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help=(
            "pipeline timeout in seconds; 0 disables timeout "
            "(default: AEROS_PIPELINE_TIMEOUT or 300)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["smoke", "run"],
        default=os.getenv("AEROS_PIPELINE_CHECK_MODE", "smoke"),
        help="smoke validates the entry point; run executes the delegated pipeline",
    )
    args = parser.parse_args()
    timeout_seconds = _normalize_timeout(
        args.timeout if args.timeout is not None else os.getenv("AEROS_PIPELINE_TIMEOUT", "300")
    )

    if args.mode == "smoke":
        return _smoke_check()

    pipeline = _load_pipeline()
    delegated = _resolve_pipeline_command(pipeline)
    cwd = Path(str(pipeline.get("cwd") or "."))
    if delegated:
        if not cwd.exists() or not cwd.is_dir():
            print(f"FAIL: configured pipeline cwd does not exist: {cwd}")
            return 1
        timeout_label = "off" if timeout_seconds == 0 else f"{timeout_seconds}s"
        print(
            f"Running delegated pipeline: cwd={cwd} command={_display_command(delegated)} "
            f"(timeout: {timeout_label})",
            flush=True,
        )
        returncode = _run_streaming(delegated, timeout_seconds, cwd=cwd)
        if returncode != 0:
            print(f"FAIL: delegated pipeline returned exit code {returncode}", flush=True)
            return returncode
        print("PASS: delegated pipeline ran successfully", flush=True)
        return 0

    if not MASTER_SCRIPT.exists():
        print(f"FAIL: missing master script {MASTER_SCRIPT}")
        return 1
    timeout_label = "off" if timeout_seconds == 0 else f"{timeout_seconds}s"
    print(f"Running pipeline: {MASTER_SCRIPT} (timeout: {timeout_label})", flush=True)
    returncode = _run_streaming([sys.executable, "-u", str(MASTER_SCRIPT)], timeout_seconds)
    if returncode != 0:
        print(f"FAIL: pipeline returned exit code {returncode}", flush=True)
        return returncode

    print("PASS: pipeline master script ran successfully", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
