#!/usr/bin/env python3
"""Exercise the AEROS drive usefulness entrypoint."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    proc = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "drive", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        failures.append("aeros drive --json exited nonzero: " + (proc.stderr or proc.stdout)[-1000:])
    else:
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            failures.append(f"aeros drive --json emitted invalid JSON: {exc}")
            report = {}
        objective = report.get("chosen_objective") or {}
        for key in ["objective_id", "objective", "lane", "why", "command", "stop_condition", "status_label"]:
            if not objective.get(key):
                failures.append(f"drive objective missing {key}")
        if report.get("model") != "AEROS-USEFUL-001-drive-mvp":
            failures.append("drive report does not declare AEROS-USEFUL-001 model")
        if "project_signals" not in report or "broad_capture" not in (report.get("project_signals") or {}):
            failures.append("drive report must include broad_capture project signal")
        if "data/processed/" not in (report.get("what_this_does_not_touch") or []):
            failures.append("drive report must state protected data/processed boundary")
        if not report.get("does_not_prove"):
            failures.append("drive report must include does_not_prove boundaries")
        preflight = ((report.get("project_signals") or {}).get("preflight") or {})
        if objective.get("objective_id") == "broad_capture" and preflight.get("task_mode") != "broad_capture":
            failures.append("drive broad_capture objective must use broad_capture preflight")

    proc2 = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "drive", "--goal", "citation-risk", "--execute", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc2.returncode != 0:
        failures.append("aeros drive citation-risk --execute failed: " + (proc2.stderr or proc2.stdout)[-1000:])
    else:
        payload = json.loads(proc2.stdout)
        execution = payload.get("execution") or {}
        if execution.get("attempted") is not True:
            failures.append("drive citation-risk --execute should run the read-only citation check")
        if execution.get("status") != "pass":
            failures.append("drive citation-risk execution should pass in template mode")

    if failures:
        print("FAIL: drive entrypoint problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: drive entrypoint is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
