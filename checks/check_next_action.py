#!/usr/bin/env python3
"""Validate the deterministic next-action layer.

The check verifies structure and honesty boundaries. It does not certify that
the recommendation is the best scientific choice.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import csv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.kernel import find_project_root  # noqa: E402
from aeros.runtime.action_spec import validate_action_spec  # noqa: E402
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

ACTION_SPEC_FIELDS = [
    "action_spec_id:",
    "action_spec_kind:",
    "action_spec_effect_class:",
    "action_spec_requires_decision:",
    "action_spec_producer_mode:",
]


def _validate_next_action_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    failures = [f"{path}: missing field {field}" for field in REQUIRED_FIELDS if field not in text]
    failures.extend(f"{path}: missing ActionSpec field {field}" for field in ACTION_SPEC_FIELDS if field not in text)
    label = ""
    for line in text.splitlines():
        if line.startswith("status_label:"):
            label = line.split(":", 1)[1].strip()
            break
    if label and "|" not in label and label not in VALID_LABELS:
        failures.append(f"{path}: invalid status_label {label!r}")
    if ("SUBSTANTIVE_PRODUCED" in text or "SUBSTANTIVE_DONE" in text) and "--dry-run" in text:
        failures.append(f"{path}: substantive-produced recommendation must not be paired with a dry-run command")
    return failures


def _blocked_fulltext_ids(root: Path) -> list[str]:
    path = root / "discovery/literature/search_log.csv"
    if not path.exists():
        return []
    ids: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("follow_up", "")).strip() != "blocked_fulltext":
                continue
            text = " ".join(str(value) for value in row.values())
            cleaned = "".join(ch if ch.isalnum() else " " for ch in text)
            for token in cleaned.split():
                if len(token) == 4 and token.startswith("P") and token[1:].isdigit() and token not in ids:
                    ids.append(token)
    return sorted(ids)


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
    spec = data.get("action_spec") or {}
    failures.extend(f"computed next action {failure}" for failure in validate_action_spec(spec))
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
    if data.get("status_label") in {"SUBSTANTIVE_PRODUCED", "SUBSTANTIVE_DONE"} and "--dry-run" in str(data.get("command", "")):
        failures.append("computed next action claims substantive-produced candidate while using --dry-run")
    if not isinstance(spec, dict) or not spec:
        failures.append("computed next action missing action_spec")
    else:
        if spec.get("command") != data.get("command"):
            failures.append("computed next action ActionSpec command differs from rendered command")
        if spec.get("lane") != data.get("lane"):
            failures.append("computed next action ActionSpec lane differs from rendered lane")
        if spec.get("producer_mode") != "declared":
            failures.append(f"computed next action ActionSpec producer_mode is not declared: {spec.get('producer_mode')!r}")

    next_json = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "next", "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if next_json.returncode != 0:
        failures.append(f"aeros next --json failed with exit {next_json.returncode}: {next_json.stderr.strip()}")
    else:
        try:
            next_json_data = json.loads(next_json.stdout)
        except json.JSONDecodeError as exc:
            failures.append(f"aeros next --json did not emit JSON: {exc}")
            next_json_data = {}
        next_json_spec = next_json_data.get("action_spec") if isinstance(next_json_data, dict) else None
        if not isinstance(next_json_spec, dict) or not next_json_spec:
            failures.append("aeros next --json missing action_spec")
        else:
            failures.extend(f"aeros next --json {failure}" for failure in validate_action_spec(next_json_spec))
            if next_json_spec.get("producer_mode") != "declared":
                failures.append(
                    f"aeros next --json ActionSpec producer_mode is not declared: {next_json_spec.get('producer_mode')!r}"
                )
            if next_json_spec.get("command") != next_json_data.get("command"):
                failures.append("aeros next --json ActionSpec command differs from rendered command")
            if next_json_spec.get("lane") != next_json_data.get("lane"):
                failures.append("aeros next --json ActionSpec lane differs from rendered lane")

    rc, records = run_until(root, ControllerLoopArgs(until="no-progress", dry_run=True, max_steps=2))
    if rc != 0 or not records:
        failures.append("controller run-until dry-run did not produce a safe record")
    elif not records[0].get("action_spec"):
        failures.append("controller run-until dry-run did not include an ActionSpec record")
    else:
        if (records[0].get("action_spec") or {}).get("producer_mode") != "declared":
            failures.append("controller run-until dry-run ActionSpec producer_mode is not declared")
        for key in ("primary_stop_reason", "semantic_progress", "frontier_hash", "action_signature"):
            if key not in records[0]:
                failures.append(f"controller run-until dry-run missing {key}")
    rc, max_records = run_until(root, ControllerLoopArgs(until="max-steps", dry_run=True, max_steps=2))
    if rc != 0 or not max_records:
        failures.append("controller run-until max-steps dry-run did not produce a safe record")
    elif not max_records[0].get("action_spec"):
        failures.append("controller run-until max-steps dry-run did not include an ActionSpec record")
    else:
        if (max_records[0].get("action_spec") or {}).get("producer_mode") != "declared":
            failures.append("controller run-until max-steps ActionSpec producer_mode is not declared")
        for key in ("primary_stop_reason", "semantic_progress", "frontier_hash", "action_signature"):
            if key not in max_records[0]:
                failures.append(f"controller run-until max-steps dry-run missing {key}")
    unsafe_args, unsafe_reason = _command_args(
        type("Action", (), {"command": "python3 -m aeros.cli iterate --stage discovery", "status_label": "ROUTE_READY"})(),
        ControllerLoopArgs(until="human-gate"),
    )
    if unsafe_args or "allow-task-runs" not in unsafe_reason:
        failures.append("controller must reject real iterate commands without --allow-task-runs")

    for lane in ["data", "literature", "method", "analysis", "claim", "writing", "compliance"]:
        lane_action = compute_next_action(root, lane=lane).to_dict()
        lane_spec = lane_action.get("action_spec") or {}
        failures.extend(f"lane {lane}: {failure}" for failure in validate_action_spec(lane_spec))
        if lane_action.get("lane") not in {lane, "discovery", "project", "harness", "human_gate"}:
            failures.append(f"lane {lane}: recommendation drifted to {lane_action.get('lane')!r}")
        if lane_action.get("status_label") not in VALID_LABELS:
            failures.append(f"lane {lane}: invalid status_label {lane_action.get('status_label')!r}")
        if lane_action.get("status_label") in {"SUBSTANTIVE_PRODUCED", "SUBSTANTIVE_DONE"} and "--dry-run" in str(lane_action.get("command", "")):
            failures.append(f"lane {lane}: substantive-produced recommendation must not be dry-run")
        if isinstance(lane_spec, dict) and lane_spec.get("command") != lane_action.get("command"):
            failures.append(f"lane {lane}: ActionSpec command differs from rendered command")
        if isinstance(lane_spec, dict) and lane_spec.get("producer_mode") != "declared":
            failures.append(f"lane {lane}: ActionSpec producer_mode is not declared: {lane_spec.get('producer_mode')!r}")

    blocked_fulltext_ids = _blocked_fulltext_ids(root)
    if blocked_fulltext_ids:
        literature_action = compute_next_action(root, lane="literature").to_dict()
        text = " ".join(str(value) for value in literature_action.values())
        if not literature_action.get("blocked"):
            failures.append("lane literature: blocked_fulltext records must produce a blocked next-action")
        missing = [paper_id for paper_id in blocked_fulltext_ids if paper_id not in text]
        if missing:
            failures.append(f"lane literature: blocked full-text ids missing from recommendation: {', '.join(missing)}")

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
