#!/usr/bin/env python3
"""Validate the post-pipeline reconcile control path.

This check only verifies wiring and safety boundaries. It does not run a real
pipeline, validate scientific results, approve gates, or certify claims.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.reconcile import build_reconcile_plan  # noqa: E402


def main() -> int:
    root = Path.cwd()
    plan = build_reconcile_plan(root)
    names = {step.name for step in plan}
    required = {"provenance", "research_graph", "global_state"}
    failures: list[str] = []
    missing = required - names
    if missing:
        failures.append(f"reconcile plan missing core step(s): {', '.join(sorted(missing))}")
    proc = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "reconcile", "--dry-run"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        failures.append(f"`aeros reconcile --dry-run` returned {proc.returncode}")
    for expected in ["dry_run: true", "provenance", "research_graph", "global_state", "does_not_prove"]:
        if expected not in output:
            failures.append(f"`aeros reconcile --dry-run` output missing {expected!r}")
    if failures:
        print("FAIL: reconcile check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: reconcile command is wired and boundary-labeled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
