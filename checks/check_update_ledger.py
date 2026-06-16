#!/usr/bin/env python3
"""Ensure meaningful template updates are tracked in decisions/update_ledger.md."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LEDGER = Path("decisions/update_ledger.md")
REQUIRED_PHRASES = [
    "North star:",
    "Alignment",
    "Non-goal",
    "Drift risk",
    "Next check",
]


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()


def _commit_touches_ledger(commit: str) -> bool:
    try:
        names = _git(["show", "--name-only", "--format=", commit]).splitlines()
    except Exception:
        return False
    return any(name.strip() == str(LEDGER) for name in names)


def main() -> int:
    if not LEDGER.exists():
        print("FAIL: missing decisions/update_ledger.md")
        return 1
    text = LEDGER.read_text(encoding="utf-8")
    failures: list[str] = []
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"update ledger missing required phrase: {phrase}")

    try:
        commits = _git(["log", "--format=%h", "-5"]).splitlines()
    except Exception:
        commits = []
    for commit in commits:
        if commit in text:
            continue
        if _commit_touches_ledger(commit):
            continue
        failures.append(f"recent commit {commit} is not referenced in decisions/update_ledger.md")

    if failures:
        print("FAIL: update ledger problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: update ledger tracks recent updates ({len(commits)} commit(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
