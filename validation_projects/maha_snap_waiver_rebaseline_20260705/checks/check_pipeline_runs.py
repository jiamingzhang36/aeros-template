#!/usr/bin/env python3
"""Run the project master script placeholder or project-specific pipeline."""

from __future__ import annotations

import argparse
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.execution_profile import display_command, resolve_execution_profile, resolved_command  # noqa: E402
from aeros.runtime.reconcile import run_reconcile  # noqa: E402


MASTER_SCRIPT = Path("code/99_make_all.py")


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

    profile = resolve_execution_profile(Path.cwd())
    command = resolved_command(profile)
    cwd = profile.cwd
    print("SMOKE: pipeline master script exists and compiles")
    if command:
        print(f"SMOKE: execution_profile={profile.name} cwd={cwd} command={display_command(command)}")
        print(f"SMOKE: configured pipeline python={profile.python}")
        if profile.post_run_hooks:
            print(f"SMOKE: post_run_hooks={','.join(profile.post_run_hooks)}")
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

    profile = resolve_execution_profile(Path.cwd())
    delegated = resolved_command(profile)
    cwd = Path(str(profile.cwd or "."))
    if delegated:
        if not cwd.exists() or not cwd.is_dir():
            print(f"FAIL: configured pipeline cwd does not exist: {cwd}")
            return 1
        timeout_label = "off" if timeout_seconds == 0 else f"{timeout_seconds}s"
        print(
            f"Running delegated pipeline: profile={profile.name} cwd={cwd} command={display_command(delegated)} "
            f"(timeout: {timeout_label})",
            flush=True,
        )
        returncode = _run_streaming(delegated, timeout_seconds, cwd=cwd)
        if returncode != 0:
            print(f"FAIL: delegated pipeline returned exit code {returncode}", flush=True)
            return returncode
        if "reconcile" in profile.post_run_hooks:
            report = run_reconcile(Path.cwd(), timeout_seconds=max(timeout_seconds, 1))
            if not report.ok:
                print("FAIL: post-run reconcile hook failed", flush=True)
                return 1
            print("POST-RUN: reconcile hook passed", flush=True)
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
