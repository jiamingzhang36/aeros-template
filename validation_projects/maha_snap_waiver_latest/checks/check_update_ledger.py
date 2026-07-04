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



def _worktree_dirty() -> bool:
    try:
        return bool(_git(["status", "--porcelain"]).strip())
    except Exception:
        return False

def _commit_touches_ledger(commit: str) -> bool:
    try:
        names = _git(["show", "--name-only", "--format=", commit]).splitlines()
    except Exception:
        return False
    return any(name.strip() == str(LEDGER) for name in names)


# A commit needs a narrative ledger entry only if it changes the framework itself.
# Bookkeeping, validation-project, doc, and project-artifact commits are exempt --
# requiring a ledger entry for those is what produced recurring false-red harness
# failures (e.g. a validation-project gate approval that touches no framework code).
FRAMEWORK_PREFIXES = ("aeros/", "checks/", "harness/", "templates/", "tools/")


def _commit_touches_framework(commit: str) -> bool:
    try:
        names = _git(["show", "--name-only", "--format=", commit]).splitlines()
    except Exception:
        # If we cannot inspect the commit, be conservative and require an entry.
        return True
    return any(
        name.strip().startswith(FRAMEWORK_PREFIXES)
        for name in names
        if name.strip()
    )


def main() -> int:
    if not LEDGER.exists():
        print("FAIL: missing decisions/update_ledger.md")
        return 1
    text = LEDGER.read_text(encoding="utf-8")
    failures: list[str] = []
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"update ledger missing required phrase: {phrase}")

    pending_count = text.count("**Commit(s)**: `pending`")
    if pending_count and not _worktree_dirty():
        failures.append(
            f"pending commit marker remains in update ledger ({pending_count}); "
            "replace with commit hash before claiming tracking is current"
        )

    try:
        commits = _git(["log", "--format=%h", "-5"]).splitlines()
    except Exception:
        commits = []
    for commit in commits:
        if commit in text:
            continue
        if _commit_touches_ledger(commit):
            continue
        if not _commit_touches_framework(commit):
            # Non-framework commit (bookkeeping / validation project / docs / project
            # artifact): does not require a framework-evolution narrative entry.
            continue
        failures.append(
            f"recent commit {commit} changes framework code but is not referenced "
            "in decisions/update_ledger.md"
        )

    if failures:
        print("FAIL: update ledger problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: update ledger tracks recent updates ({len(commits)} commit(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
