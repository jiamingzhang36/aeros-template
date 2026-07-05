#!/usr/bin/env python3
"""Run agent-runs validation checks as one combined entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


AGENT_RUN_TOOLS = [
    "build_agent_runs_index.py",
    "check_agent_runs_index.py",
    "check_agent_run_report.py",
]


def _run(check: str) -> int:
    check_dir = Path(__file__).resolve().parent
    result = subprocess.run(
        [sys.executable, str(check_dir / check)],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout.rstrip("\n"))
    if result.stderr:
        print(result.stderr.rstrip("\n"))
    return result.returncode


def main() -> int:
    failures = 0
    for check in AGENT_RUN_TOOLS:
        if _run(check):
            failures += 1

    if failures:
        print(f"FAIL: {failures} agent-runs tool checks failed")
        return 1

    print("PASS: agent-runs tools checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
