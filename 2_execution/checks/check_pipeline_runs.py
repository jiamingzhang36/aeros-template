#!/usr/bin/env python3
"""Run the project master script placeholder or project-specific pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MASTER_SCRIPT = Path("2_execution/code/run_all.py")


def main() -> int:
    if not MASTER_SCRIPT.exists():
        print(f"FAIL: missing master script {MASTER_SCRIPT}")
        return 1

    result = subprocess.run(
        [sys.executable, str(MASTER_SCRIPT)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        print(f"FAIL: pipeline returned exit code {result.returncode}")
        return result.returncode

    print("PASS: pipeline master script ran successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
