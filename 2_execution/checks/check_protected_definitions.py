#!/usr/bin/env python3
"""Fail if protected definition files have uncommitted changes."""

from __future__ import annotations

import subprocess
import sys


PROTECTED_PATHS = [
    "1_design/protected_definitions.yml",
    "1_design/data_contract.yml",
    "3_evidence/claim_registry.md",
]


def main() -> int:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *PROTECTED_PATHS],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip())
        return result.returncode

    changes = result.stdout.strip()
    if changes:
        print("FAIL: protected files have uncommitted changes:")
        print(changes)
        print("Human approval is required before changing protected definitions.")
        return 1

    print("PASS: protected definition files are unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
