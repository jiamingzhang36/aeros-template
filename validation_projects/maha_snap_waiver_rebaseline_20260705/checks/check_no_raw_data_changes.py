#!/usr/bin/env python3
"""Fail only if raw data is tracked/staged in git (raw data must never enter git).

Untracked raw data present locally is the correct state and is not a failure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = TEMPLATE_ROOT / "data" / "raw"
ALLOWED = {".gitkeep"}


def _is_standalone_repo() -> bool:
    """Return True only when the current template is its own git root."""
    try:
        result = subprocess.run(
            ["git", "-C", str(TEMPLATE_ROOT), "rev-parse", "--show-toplevel"],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        print("SKIP: git unavailable in environment; skipping raw-data guardrail.")
        return False

    if result.returncode != 0:
        print(result.stderr.strip())
        print(
            "SKIP: no git repository at template root "
            f"({TEMPLATE_ROOT}). Initialize one locally with `git init` first."
        )
        return False

    top_level = Path(result.stdout.strip()).resolve()
    return top_level == TEMPLATE_ROOT.resolve()


def main() -> int:
    if not _is_standalone_repo():
        print(
            "SKIP: raw-data check is disabled until the template root is a standalone git repo."
        )
        return 0

    if not RAW_DIR.exists():
        print(f"FAIL: missing {RAW_DIR}")
        return 1

    result = subprocess.run(
        ["git", "-C", str(TEMPLATE_ROOT), "status", "--porcelain", "--", str(RAW_DIR)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip())
        return result.returncode

    # The violation is raw data ENTERING git (tracked/staged), not raw data merely
    # existing locally. Untracked ('??') raw data is the correct state — it is not
    # in git — so it is not a failure; it only warrants a gitignore reminder.
    tracked: list[str] = []
    untracked: list[str] = []
    for line in result.stdout.splitlines():
        xy = line[:2]
        path = Path(line[3:].strip())
        relative_path = Path(*path.parts[2:]).as_posix() if path.parts[:2] == ("data", "raw") else path.as_posix()
        if relative_path in ALLOWED:
            continue
        (untracked if xy == "??" else tracked).append(line)

    if tracked:
        print("FAIL: raw data is tracked/staged in git (raw data must never enter git):")
        print("\n".join(tracked))
        return 1

    if untracked:
        print("PASS: raw data present but untracked (correctly not in git). "
              "Add data/raw/ to .gitignore to silence this note.")
        return 0

    print("PASS: no raw data changes detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
