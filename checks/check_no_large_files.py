#!/usr/bin/env python3
"""Fail if any git-tracked file is too large to push to GitHub.

GitHub hard-rejects files larger than 100 MiB. A single oversized file (often a
backup tarball or data snapshot an autonomous run committed) blocks the whole
push. This check flags such files early, in the harness, instead of at push time.

Default limit is the GitHub hard limit (100 MiB) so it only ever fires on files
that are genuinely unpushable — no false positives on legitimately-tracked data.
Lower LIMIT_MB if a project wants a stricter hygiene threshold (GitHub itself
warns above 50 MiB).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CHECK_NAME = "check_no_large_files"
LIMIT_MB = 100
LIMIT_BYTES = LIMIT_MB * 1024 * 1024
HINT = "Move the file out of git (gitignore it and keep it locally) or use Git LFS."


def tracked_files(root: Path) -> list[str] | None:
    """Return git-tracked paths, or None if this is not a usable git repo."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"], cwd=str(root), text=True, capture_output=True
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return [f for f in proc.stdout.split("\0") if f]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path.cwd()

    files = tracked_files(root)
    if files is None:
        msg = "not a git repository; nothing to size-check"
        if args.json:
            print(json.dumps({"check": CHECK_NAME, "status": "pass", "failures": [], "hint": msg}))
        else:
            print(f"PASS: {msg}")
        return 0

    failures: list[str] = []
    for rel in files:
        path = root / rel
        try:
            size = path.stat().st_size
        except OSError:
            continue  # deleted/unreadable; not our concern
        if size > LIMIT_BYTES:
            failures.append(f"{rel} is {size / 1048576:.1f} MB (> {LIMIT_MB} MB; GitHub rejects >100 MiB)")

    if args.json:
        print(json.dumps({
            "check": CHECK_NAME,
            "status": "fail" if failures else "pass",
            "failures": failures,
            "hint": HINT if failures else "",
        }))
    elif failures:
        print("FAIL: git-tracked file(s) exceed the GitHub size limit:")
        for item in failures:
            print(f"  - {item}")
        print(f"Hint: {HINT}")
    else:
        print(f"PASS: no git-tracked file exceeds {LIMIT_MB} MB ({len(files)} file(s) checked)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
