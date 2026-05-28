#!/usr/bin/env python3
"""Fail if tracked or untracked raw data files changed."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


RAW_DIR = Path("data/raw")
ALLOWED = {str(RAW_DIR / ".gitkeep")}


def main() -> int:
    if not RAW_DIR.exists():
        print(f"FAIL: missing {RAW_DIR}")
        return 1

    result = subprocess.run(
        ["git", "status", "--porcelain", "--", str(RAW_DIR)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip())
        return result.returncode

    changed = []
    for line in result.stdout.splitlines():
        path = line[3:].strip()
        if path not in ALLOWED:
            changed.append(line)

    if changed:
        print("FAIL: raw data changes detected:")
        print("\n".join(changed))
        return 1

    print("PASS: no raw data changes detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
