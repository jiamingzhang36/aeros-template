#!/usr/bin/env python3
"""Bind gate approval to integrity.

Gate approval is recorded by a human committing ``decisions/approvals/G{N}.md``.
AEROS cannot block that git commit -- but it CAN make the harness fail when an
approval is not backed by passing integrity checks. This turns a diffuse set of
failures (no-op completions, missing receipts, an incomplete data contract) into
one pointed, blocking signal:

    "Gate G{N} is approved but is not integrity-backed -- fix the work or
     withdraw the approval."

Surfaced by the 2026-06-25 MAHA validation: a G10 approval was committed while the
project failed 7 integrity checks, because the approval gate was not bound to them.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Failure of any of these means "work claimed complete is not substantively sound."
# An approved gate must not coexist with any of them failing.
INTEGRITY_CRITICAL = [
    "check_noop_runs.py",
    "check_completion_receipts.py",
    "check_skill_invocations.py",
    "check_estimand_data_contract.py",
]


def _approved_gates(root: Path) -> list[str]:
    approvals = root / "decisions/approvals"
    if not approvals.exists():
        return []
    return sorted(
        p.stem for p in approvals.glob("G*.md")
        if len(p.stem) > 1 and p.stem[1:].isdigit()
    )


def evaluate(root: Path) -> tuple[int, str]:
    approved = _approved_gates(root)
    if not approved:
        return 0, "PASS: approval integrity inactive (no gate approvals on file)"
    failing: list[str] = []
    for name in INTEGRITY_CRITICAL:
        check = root / "checks" / name
        if not check.exists():
            continue
        proc = subprocess.run(
            [sys.executable, str(check)], cwd=root,
            capture_output=True, text=True, timeout=300, check=False,
        )
        if proc.returncode != 0:
            failing.append(name)
    if failing:
        lines = [
            "FAIL: gate approval is not integrity-backed.",
            f"  approved gate(s): {', '.join(approved)}",
            f"  failing integrity check(s): {', '.join(failing)}",
            "  An approved gate must not stand on red integrity checks.",
            "  Resolve: complete/repair the flagged work, or withdraw the approval",
            "  (remove or supersede the decisions/approvals/G*.md file).",
        ]
        return 1, "\n".join(lines)
    return 0, (
        f"PASS: approved gate(s) {', '.join(approved)} are integrity-backed "
        f"({len(INTEGRITY_CRITICAL)} integrity check(s) green)"
    )


def main() -> int:
    rc, message = evaluate(ROOT)
    print(message)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
