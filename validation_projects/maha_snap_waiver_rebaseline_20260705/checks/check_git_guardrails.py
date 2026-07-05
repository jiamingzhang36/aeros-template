#!/usr/bin/env python3
"""Run git/data guardrail checks as a single entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


GUARDRAIL_CHECKS = [
    "check_no_raw_data_changes.py",
    "check_no_placeholders.py",
    "check_no_large_files.py",
]


def _run(check: str) -> int:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / check)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip("\n"))
    if result.stderr:
        print(result.stderr.rstrip("\n"))
    return result.returncode


def main() -> int:
    failures = 0
    for check in GUARDRAIL_CHECKS:
        if _run(check):
            failures += 1

    if failures:
        print(f"FAIL: {failures} git/data guardrail check(s) failed")
        return 1

    print("PASS: git/data guardrail checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
