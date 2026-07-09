#!/usr/bin/env python3
"""Validate that current-work context biases next/drive routing without authority."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.current_work import load_current_work_context
from aeros.runtime.drive import build_drive_report
from aeros.runtime.next_action import compute_next_action


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_current_work_") as tmp:
        root = Path(tmp)
        (root / "project_manifest.yml").write_text(
            """project:
  name: fixture
research:
  topic: Fixture manuscript project
  one_sentence_question: Does the fixture route writing work before data fallback?
""",
            encoding="utf-8",
        )
        (root / "CURRENT_WORK.yml").write_text(
            """active_goal: finalize poster/manuscript packet
active_deliverable: poster and manuscript citation audit
active_lane: writing
priority_order:
  - manuscript citation truth
  - poster wording consistency
explicitly_deprioritized:
  - broad capture unless requested
""",
            encoding="utf-8",
        )
        context = load_current_work_context(root)
        if context.get("status") != "active" or context.get("active_lane") != "writing":
            failures.append("current work context did not load active writing lane")
        action = compute_next_action(root)
        if action.lane == "data" or "data scan" in action.command:
            failures.append("next action ignored active writing context and fell back to data-first")
        report = build_drive_report(root)
        objective = report.get("chosen_objective") or {}
        if objective.get("lane") == "data" or objective.get("objective_id") == "broad_capture":
            failures.append("drive ignored active writing context and chose broad_capture/data")
        if objective.get("objective_id") != "current_work_priority":
            failures.append("drive did not compile active priority_order[0] into a current-work objective")
        if objective.get("objective") != "manuscript citation truth":
            failures.append("drive did not select the first operator-declared current-work priority")
        if "task preflight" not in str(objective.get("command") or ""):
            failures.append("current-work objective must remain a preflight-only recommendation")
        if objective.get("source") != "CURRENT_WORK.yml#priority_order[0]":
            failures.append("current-work objective must expose its deterministic source")
        signals = report.get("project_signals") or {}
        if not isinstance(signals.get("current_work"), dict):
            failures.append("drive report does not surface current_work signal")
    if failures:
        print("FAIL: current work context problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: current work context biases next/drive safely")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
