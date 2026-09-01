#!/usr/bin/env python3
"""Validate AEROS context bundle plumbing and honesty boundaries."""

from __future__ import annotations

import sys
import tempfile
import json
from unittest.mock import patch
from pathlib import Path

ROOT = Path.cwd()
REQUIRED_FILES = [
    ROOT / "aeros/runtime/context_bundle.py",
    ROOT / "aeros/runtime/context_episode.py",
    ROOT / "harness/context_budget.yml",
    ROOT / "templates/CONTEXT_BUNDLE.md",
    ROOT / "CONTEXT_BUNDLE.md",
]


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing {path}")
    cli = ROOT / "aeros/cli.py"
    if cli.exists() and "context" not in cli.read_text(encoding="utf-8"):
        failures.append("aeros/cli.py: missing context command wiring")
    if (ROOT / "aeros/runtime/context_bundle.py").exists():
        sys.path.insert(0, str(ROOT))
        try:
            from aeros.runtime.context_bundle import build_context_bundle, format_context_bundle
            from aeros.runtime.context_episode import bind_execution_context, close_context_episode, context_episode_status, ensure_advice_context, open_context_episode, record_task_preflight
            bundle = build_context_bundle(ROOT, lane="project", brief=True)
            rendered = format_context_bundle(bundle, brief=True)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"context bundle generation failed: {exc}")
        else:
            for key in ["current_goal", "next_action", "stop_rule", "does_not_prove", "source_hashes", "context_staleness"]:
                if key not in bundle:
                    failures.append(f"context bundle missing key: {key}")
            next_action = bundle.get("next_action") or {}
            if next_action.get("status_label") in {"SUBSTANTIVE_PRODUCED", "SUBSTANTIVE_DONE"} and not bundle.get("latest_substantive_artifact"):
                failures.append("context bundle cannot imply substantive production without latest_substantive_artifact")
            for marker in ["recommended_next_action", "status_label", "context_stale", "stop_rule", "does_not_prove"]:
                if marker not in rendered:
                    failures.append(f"rendered context missing marker: {marker}")
            with tempfile.TemporaryDirectory(prefix="aeros_context_episode_") as temporary:
                fixture_root = Path(temporary)
                tracked = fixture_root / "artifact.txt"
                tracked.write_text("before\n", encoding="utf-8")
                fixture_bundle = {
                    "lane": "literature",
                    "current_goal": "ground one citation",
                    "current_blocker": "",
                    "latest_substantive_artifact": "",
                    "next_action": {"recommended_next_action": "inspect a passage", "command": "aeros submit", "status_label": "ROUTE_READY"},
                    "source_hashes": {"CURRENT_STATE.md": "fixture"},
                    "does_not_prove": "fixture boundary",
                }
                opened = open_context_episode(
                    fixture_root,
                    lane="literature",
                    goal="ground one citation",
                    entrypoint="fixture",
                    conversation_id="fixture-chat",
                    tracked_artifacts=["artifact.txt"],
                    bundle=fixture_bundle,
                )
                if not (opened.get("context_basis") or {}).get("context_hash"):
                    failures.append("context episode did not record a context hash")
                binding = bind_execution_context(
                    fixture_root,
                    task_id="T_CONTEXT",
                    lane="literature",
                    goal="ground one citation",
                )
                binding_path = fixture_root / str(binding.get("binding_path") or "")
                if not binding.get("episode_id") or not binding_path.is_file():
                    failures.append("execution context did not write a durable task binding")
                activation = record_task_preflight(
                    fixture_root,
                    context_basis=opened.get("context_basis") or {},
                    report={
                        "status": "ADVISORY",
                        "lane": "literature",
                        "intent": "ground one citation",
                        "task_mode": "literature_recovery",
                        "startup_brief": {"recommended_action": "inspect a passage", "highest_research_risk": {"risk_id": "citation_debt"}},
                    },
                )
                if activation.get("status") != "ACTIVE":
                    failures.append("task preflight did not record a durable activation packet")
                tracked.write_text("after\n", encoding="utf-8")
                closed = close_context_episode(
                    fixture_root,
                    conversation_id="fixture-chat",
                    summary="updated the tracked fixture artifact",
                    work_items=["fixture update"],
                    artifact_paths=["artifact.txt"],
                    outcome="fixture_complete",
                )
                artifact_rows = (closed.get("close") or {}).get("observed_artifacts") or []
                if not artifact_rows or artifact_rows[0].get("changed_since_open") is not True:
                    failures.append("context episode did not distinguish an observed artifact change from declared work")
                if (closed.get("effect") or {}).get("status") != "RISK_RAISED":
                    failures.append("closed context episode did not report the recorded risk effect honestly")
                episode_status = context_episode_status(fixture_root, conversation_id="fixture-chat")
                if episode_status.get("status") != "CLOSED" or episode_status.get("activation_status") != "EFFECT_REPORTED":
                    failures.append("context episode did not close cleanly")
                replacement_bundle = dict(fixture_bundle)
                replacement_bundle["current_goal"] = "review a different passage"
                old_directory = fixture_root / "outputs/context/episodes" / str((opened.get("episode") or {}).get("episode_id") or "")
                active_pointer = fixture_root / "outputs/context/episodes/active/fixture-chat.json"
                active_pointer.write_text(
                    json.dumps({"episode_id": (opened.get("episode") or {}).get("episode_id"), "state": "open"}),
                    encoding="utf-8",
                )
                if old_directory.is_dir():
                    old_directory.chmod(0o500)
                try:
                    replacement = open_context_episode(
                        fixture_root,
                        lane="literature",
                        goal="review a different passage",
                        entrypoint="fixture",
                        conversation_id="fixture-chat",
                        bundle=replacement_bundle,
                    )
                finally:
                    if old_directory.is_dir():
                        old_directory.chmod(0o700)
                if replacement.get("status") not in {"OPENED", "REUSED"}:
                    failures.append("a stale read-only episode prevented a fresh context episode")
                with patch("aeros.runtime.context_episode.open_context_episode", side_effect=OSError("read-only fixture")):
                    fallback = ensure_advice_context(fixture_root, lane="literature", entrypoint="fixture")
                if fallback.get("status") != "EPHEMERAL_UNPERSISTED" or not fallback.get("persistence_warning"):
                    failures.append("unwritable episode storage did not yield an explicit ephemeral context basis")
                with patch("aeros.runtime.context_episode.open_context_episode", side_effect=OSError("read-only fixture")):
                    try:
                        bind_execution_context(fixture_root, task_id="T_BLOCK", lane="literature", goal="fixture")
                    except RuntimeError:
                        pass
                    else:
                        failures.append("execution context did not fail closed when persistence was unavailable")
    template = ROOT / "templates/CONTEXT_BUNDLE.md"
    if template.exists():
        text = template.read_text(encoding="utf-8")
        for marker in ["does_not_prove", "stop_rule", "This bundle is context"]:
            if marker not in text:
                failures.append(f"{template}: missing marker {marker!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: context bundle plumbing is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
