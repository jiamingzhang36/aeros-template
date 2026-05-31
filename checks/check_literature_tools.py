#!/usr/bin/env python3
"""Run the literature-related harness checks as a single entry point."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


CHECK_DIR = Path(__file__).resolve().parent
LITERATURE_CHECKS = [
    "check_literature_registry.py",
    "check_literature_functions.py",
    "check_extraction_cards.py",
    "check_synthesis_grounding.py",
    "check_citation_audit.py",
    "check_gap_grounding.py",
]


def _run(check: str, extra_args: list[str]) -> int:
    cmd = [sys.executable, str(CHECK_DIR / check), *extra_args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip("\n"))
    if result.stderr:
        print(result.stderr.rstrip("\n"))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all literature checks.")
    parser.add_argument(
        "--require-complete-matrix",
        action="store_true",
        help="Require complete matrix checks in literature functions.",
    )
    args, _ = parser.parse_known_args()

    failures = 0
    literature_args = ["--require-complete-matrix"] if args.require_complete_matrix else []

    for check in LITERATURE_CHECKS:
        extra = literature_args if check == "check_literature_functions.py" else []
        status = _run(check, extra)
        if status:
            failures += 1

    if failures:
        print(f"FAIL: {failures} literature check(s) failed")
        return 1

    print("PASS: literature checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
