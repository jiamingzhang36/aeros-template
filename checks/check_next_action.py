#!/usr/bin/env python3
"""Validate the deterministic next-action layer.

The check verifies structure and honesty boundaries. It does not certify that
the recommendation is the best scientific choice.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.kernel import find_project_root  # noqa: E402
from aeros.runtime.controller_loop import ControllerLoopArgs, _command_args, run_until  # noqa: E402
from aeros.runtime.next_action import VALID_LABELS, compute_next_action  # noqa: E402


REQUIRED_FIELDS = [
    "recommended_next_action:",
    "why_this_next:",
    "lane:",
    "status_label:",
    "command:",
    "stop_condition:",
]


def _validate_next_action_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    failures = [f"{path}: missing field {field}" for field in REQUIRED_FIELDS if field not in text]
    label = ""
    for line in text.splitlines():
        if line.startswith("status_label:"):
            label = line.split(":", 1)[1].strip()
            break
    if label and "|" not in label and label not in VALID_LABELS:
        failures.append(f"{path}: invalid status_label {label!r}")
    if "SUBSTANTIVE_DONE" in text and "--dry-run" in text:
        failures.append(f"{path}: SUBSTANTIVE_DONE recommendation must not be paired with a dry-run command")
    return failures


def main() -> int:
    root = find_project_root(Path.cwd())
    failures: list[str] = []

    template = root / "templates" / "NEXT_ACTION.md"
    if not template.exists():
        failures.append("missing templates/NEXT_ACTION.md")
    else:
        failures.extend(_validate_next_action_file(template))

    action = compute_next_action(root)
    data = action.to_dict()
    for key in [
        "recommended_next_action",
        "why_this_next",
        "lane",
        "status_label",
        "command",
        "stop_condition",
    ]:
        if not str(data.get(key, "")).strip():
            failures.append(f"computed next action missing {key}")
    if data.get("status_label") not in VALID_LABELS:
        failures.append(f"computed next action has invalid status_label {data.get('status_label')!r}")
    if data.get("status_label") == "SUBSTANTIVE_DONE" and "--dry-run" in str(data.get("command", "")):
        failures.append("computed next action claims SUBSTANTIVE_DONE candidate while using --dry-run")

    rc, records = run_until(root, ControllerLoopArgs(until="no-progress", dry_run=True, max_steps=2))
    if rc != 0 or not records:
        failures.append("controller run-until dry-run did not produce a safe record")
    unsafe_args, unsafe_reason = _command_args(
        type("Action", (), {"command": "python3 -m aeros.cli iterate --stage discovery", "status_label": "ROUTE_READY"})(),
        ControllerLoopArgs(until="human-gate"),
    )
    if unsafe_args or "allow-task-runs" not in unsafe_reason:
        failures.append("controller must reject real iterate commands without --allow-task-runs")

    for lane in ["data", "literature", "method", "analysis", "claim", "writing", "compliance"]:
        lane_action = compute_next_action(root, lane=lane).to_dict()
        if lane_action.get("lane") not in {lane, "discovery", "project", "harness", "human_gate"}:
            failures.append(f"lane {lane}: recommendation drifted to {lane_action.get('lane')!r}")
        if lane_action.get("status_label") not in VALID_LABELS:
            failures.append(f"lane {lane}: invalid status_label {lane_action.get('status_label')!r}")
        if lane_action.get("status_label") == "SUBSTANTIVE_DONE" and "--dry-run" in str(lane_action.get("command", "")):
            failures.append(f"lane {lane}: SUBSTANTIVE_DONE recommendation must not be dry-run")

    failures.extend(_validate_next_action_file(root / "NEXT_ACTION.md"))

    current_state = root / "CURRENT_STATE.md"
    if current_state.exists():
        text = current_state.read_text(encoding="utf-8")
        next_command_lines = [line for line in text.splitlines() if line.startswith("next_command:")]
        if next_command_lines and not next_command_lines[0].split(":", 1)[1].strip():
            failures.append("CURRENT_STATE.md next_command is empty")

    if failures:
        print("FAIL: next action problems detected:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"PASS: next action is valid ({data.get('status_label')} / {data.get('lane')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
