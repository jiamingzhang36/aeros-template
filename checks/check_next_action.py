#!/usr/bin/env python3
"""Validate the deterministic next-action layer.

The check verifies structure and honesty boundaries. It does not certify that
the recommendation is the best scientific choice.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import csv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.kernel import find_project_root  # noqa: E402
from aeros.runtime.action_spec import validate_action_spec  # noqa: E402
from aeros.runtime.controller_loop import ControllerLoopArgs, _command_args, run_until  # noqa: E402
from aeros.runtime.episode_watchdog import (  # noqa: E402
    EpisodeStep,
    WatchdogPolicy,
    assess_after,
    assess_before,
    artifact_hashes,
    load_episode_steps,
    record_episode_step,
    semantic_state_fingerprint,
)
from aeros.runtime.next_action import VALID_LABELS, compute_next_action  # noqa: E402
from aeros.runtime.context_budget import pointer_first_result, prepare_context_packet  # noqa: E402


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


def _watchdog_step(**overrides) -> EpisodeStep:
    values = {
        "episode_id": "EP-FIX",
        "objective_id": "OBJ-FIX",
        "frontier_id": "FRONTIER-FIX",
        "step": 1,
        "action_signature": "ACTION-FIX",
        "input_fingerprint": "INPUT-FIX",
        "state_fingerprint_before": "STATE-A",
        "state_fingerprint_after": "STATE-B",
        "expected_artifacts": (),
        "accepted_artifacts": (),
        "accepted_artifact_hashes": {},
        "research_value_events": (),
        "blockers_before": (),
        "blockers_after": (),
        "tool_result_hash": "RESULT-FIX",
        "error_code": "",
        "tokens_input": 0,
        "tokens_output": 0,
        "cost": 0.0,
        "wall_time": 0.1,
        "assistant_text": "",
    }
    values.update(overrides)
    return EpisodeStep(**values)


def _watchdog_fixtures() -> list[str]:
    failures: list[str] = []
    policy = WatchdogPolicy(max_tokens_without_value=100)
    with tempfile.TemporaryDirectory(prefix="aeros_watchdog_") as name:
        root = Path(name)
        (root / "outputs").mkdir()
        artifact = root / "outputs/result.json"
        artifact.write_text('{"ok": true}\n', encoding="utf-8")
        hashes = artifact_hashes(root, ("outputs/result.json",))
        prior = _watchdog_step(
            accepted_artifacts=("outputs/result.json",),
            accepted_artifact_hashes=hashes,
        )
        cache = assess_before(root, [prior], _watchdog_step())
        if cache.reason != "CACHE_HIT" or not cache.stop:
            failures.append("watchdog did not prevent a duplicate accepted action via cache hit")

        repeats = [_watchdog_step(step=1), _watchdog_step(step=2)]
        repeated = assess_before(root, repeats, _watchdog_step(step=3))
        if repeated.reason != "STOP_REPEATED_ACTION":
            failures.append("watchdog did not stop a third unchanged repeated action")

        stalled = _watchdog_step(state_fingerprint_after="STATE-A")
        first_stall = assess_after([], stalled, policy)
        second_stall = assess_after([stalled], _watchdog_step(step=2, state_fingerprint_after="STATE-A"), policy)
        if first_stall.reason != "REPLAN_REQUIRED" or second_stall.reason != "STOP_NO_STATE_CHANGE":
            failures.append("watchdog no-state-change escalation is invalid")

        errored = _watchdog_step(error_code="EXIT_7")
        same_error = assess_after([errored], _watchdog_step(step=2, error_code="EXIT_7"), policy)
        if same_error.reason != "STOP_SAME_ERROR":
            failures.append("watchdog allowed the same action/input/error twice")

        loop_text = "The same sources were checked and the next step is to check the same sources again."
        text_history = [
            _watchdog_step(step=1, state_fingerprint_after="STATE-B", assistant_text=loop_text),
            _watchdog_step(step=2, state_fingerprint_before="STATE-B", state_fingerprint_after="STATE-C", assistant_text=loop_text),
        ]
        text_loop = assess_after(
            text_history,
            _watchdog_step(step=3, state_fingerprint_before="STATE-C", state_fingerprint_after="STATE-D", assistant_text=loop_text),
            policy,
        )
        if text_loop.reason != "STOP_TEXT_LOOP":
            failures.append("watchdog did not detect a three-output text loop")

        compact = assess_after([], _watchdog_step(tokens_input=60, tokens_output=50), policy)
        token_stop = assess_after(
            [_watchdog_step(tokens_input=60, tokens_output=50)],
            _watchdog_step(step=2, tokens_input=60, tokens_output=50),
            policy,
        )
        if compact.reason != "REPLAN_WITH_COMPACT_CONTEXT" or token_stop.reason != "STOP_TOKEN_WASTE":
            failures.append("watchdog token-waste escalation is invalid")

        decision = assess_after([], prior, policy)
        record_episode_step(root, prior, decision)
        loaded = load_episode_steps(root)
        if len(loaded) != 1 or loaded[0].accepted_artifacts != ("outputs/result.json",):
            failures.append("watchdog did not persist/reload its episode observation through the event log")

        before = semantic_state_fingerprint(root)
        (root / "agent_runs").mkdir()
        (root / "agent_runs/noise.log").write_text("timestamp-only noise\n", encoding="utf-8")
        after = semantic_state_fingerprint(root)
        if before != after:
            failures.append("runtime log noise incorrectly changed the semantic state fingerprint")

        # Per-save volatile metadata (state.py stamps updated_at=_now()) must not
        # move the semantic fingerprint, or the no_state_change stop is defeated;
        # a substantive change must still move it.
        (root / "aeros_state.yml").write_text(
            "current_gate: G0\ncurrent_stage: discovery\ntasks: {}\nupdated_at: 2026-07-11T10:00:00Z\n",
            encoding="utf-8")
        stamp_a = semantic_state_fingerprint(root)
        (root / "aeros_state.yml").write_text(
            "current_gate: G0\ncurrent_stage: discovery\ntasks: {}\nupdated_at: 2026-07-11T10:00:09Z\n",
            encoding="utf-8")
        stamp_b = semantic_state_fingerprint(root)
        if stamp_a != stamp_b:
            failures.append("re-stamped updated_at wrongly changed the semantic state fingerprint")
        (root / "aeros_state.yml").write_text(
            "current_gate: G3\ncurrent_stage: execution\ntasks: {}\nupdated_at: 2026-07-11T10:00:09Z\n",
            encoding="utf-8")
        if semantic_state_fingerprint(root) == stamp_b:
            failures.append("a substantive gate/stage change did not move the semantic state fingerprint")
    return failures


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


def _is_template_project(root: Path) -> bool:
    if root.name == "aeros-template":
        return True
    manifest = root / "project_manifest.yml"
    if not manifest.exists():
        return False
    text = manifest.read_text(encoding="utf-8", errors="ignore")
    return "project_mode: template" in text


def main() -> int:
    root = find_project_root(Path.cwd())
    failures: list[str] = []
    failures.extend(_watchdog_fixtures())

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

    if _is_template_project(root):
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

    lane_matrix = ["data", "literature", "method", "analysis", "claim", "writing", "compliance"] if _is_template_project(root) else []
    for lane in lane_matrix:
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

    with tempfile.TemporaryDirectory(prefix="aeros_context_budget_") as context_name:
        context_root = Path(context_name)
        (context_root / "events").mkdir(parents=True)
        (context_root / "CURRENT_STATE.md").write_text("goal: test\n" + ("high-signal state\n" * 400), encoding="utf-8")
        event_lines = []
        for index in range(8):
            event_lines.append(json.dumps({
                "event_type": "episode_step",
                "payload": {"step": index, "action_signature": f"A-{index}", "state_changed": index == 7},
            }))
        (context_root / "events/event_log.jsonl").write_text("\n".join(event_lines) + "\n", encoding="utf-8")
        packet = prepare_context_packet(context_root, max_input_tokens=600, compact_ratio=0.68)
        if len(packet.recent_events) > 5 or packet.omitted_event_count < 3:
            failures.append("Context Budget did not retain only the latest five episode events")
        if packet.estimated_tokens > int(packet.max_input_tokens * 0.68) or not packet.compacted:
            failures.append("Context Budget did not compact before its configured threshold")
        pointer = pointer_first_result(
            artifact_path="outputs/example.json",
            summary="bounded result",
            key_facts=("one", "two"),
            changed_state="none",
            next_question="review",
        )
        if pointer.get("raw_output_in_context") is not False or pointer.get("artifact_path") != "outputs/example.json":
            failures.append("Context Budget result is not pointer-first")

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
