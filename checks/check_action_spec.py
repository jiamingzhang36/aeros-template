#!/usr/bin/env python3
"""Validate typed ActionSpec invariants directly.

This check is intentionally narrow. It does not certify that a recommended
action is scientifically optimal; it only ensures the typed control object is
not a decorative wrapper around an unsafe command string.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.action_spec import ActionSpec, action_spec_from_next, declared_action_spec, validate_action_spec  # noqa: E402


def _fake_action(command: str, *, lane: str = "project", blocked: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        recommended_next_action="test action",
        why_this_next="test rationale",
        lane=lane,
        status_label="ROUTE_READY",
        command=command,
        stop_condition="stop after test",
        source="check_action_spec",
        blocked=blocked,
    )


def main() -> int:
    failures: list[str] = []

    cases = [
        (
            "adopt placeholder",
            _fake_action('python3 -m aeros.cli adopt --idea "<your research idea>" --dry-run', lane="discovery"),
            "adopt_idea",
            "local_write_preview",
            True,
        ),
        (
            "literature status",
            _fake_action("python3 -m aeros.cli literature status", lane="literature"),
            "literature_status",
            "read_only",
            False,
        ),
        (
            "iterate preview",
            _fake_action("python3 -m aeros.cli iterate --stage discovery --dry-run", lane="data"),
            "iterate_preview",
            "local_write_preview",
            False,
        ),
        (
            "real task iteration",
            _fake_action("python3 -m aeros.cli iterate --stage discovery", lane="data"),
            "task_iteration",
            "task_run",
            True,
        ),
        (
            "blocked status",
            _fake_action("python3 -m aeros.cli literature status", lane="literature", blocked=True),
            "literature_status",
            "blocked",
            True,
        ),
    ]

    for name, action, expected_kind, expected_effect, expected_decision in cases:
        spec = action_spec_from_next(action)
        errors = validate_action_spec(spec)
        if errors:
            failures.append(f"{name}: valid derived ActionSpec rejected: {'; '.join(errors)}")
        if spec.kind != expected_kind:
            failures.append(f"{name}: kind {spec.kind!r} != {expected_kind!r}")
        if spec.effect_class != expected_effect:
            failures.append(f"{name}: effect_class {spec.effect_class!r} != {expected_effect!r}")
        if spec.requires_decision is not expected_decision:
            failures.append(f"{name}: requires_decision {spec.requires_decision!r} != {expected_decision!r}")
        if spec.producer_mode != "inferred_compat":
            failures.append(f"{name}: compatibility inference producer_mode should be inferred_compat")

    declared = declared_action_spec(
        kind="literature_status",
        effect_class="read_only",
        lane="literature",
        command="python3 -m aeros.cli literature status",
        stop_condition="stop after status",
    )
    if declared.producer_mode != "declared":
        failures.append("declared ActionSpec producer_mode is not declared")
    if validate_action_spec(declared):
        failures.append("declared ActionSpec should validate cleanly")

    invalid_read_only = ActionSpec(
        id="AS-invalid-read-only",
        kind="bad",
        lane="harness",
        effect_class="read_only",
        capabilities=("read_project_state",),
        expected_outputs=("paper/draft.md",),
        command="python3 -m aeros.cli status",
        stop_condition="stop",
    )
    if not any("read_only" in item for item in validate_action_spec(invalid_read_only)):
        failures.append("invalid read_only ActionSpec with expected_outputs was not rejected")

    invalid_task_run = ActionSpec(
        id="AS-invalid-task-run",
        kind="task_iteration",
        lane="data",
        effect_class="task_run",
        capabilities=("read_project_state", "run_task"),
        requires_decision=False,
        command="python3 -m aeros.cli iterate --stage discovery",
        stop_condition="stop",
    )
    if not any("require a decision" in item for item in validate_action_spec(invalid_task_run)):
        failures.append("invalid task_run ActionSpec without requires_decision was not rejected")

    if failures:
        print("FAIL: ActionSpec problems detected:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("PASS: ActionSpec invariants are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
