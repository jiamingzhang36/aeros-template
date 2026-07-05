#!/usr/bin/env python3
"""Validate lightweight operating dashboard files.

This check keeps daily project state tracking small and explicit:
CURRENT_STATE.md, three outcome labels, a human-gate queue, and the rollout
playbook. It does not certify research quality or gate approval.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


CURRENT_STATE = Path("CURRENT_STATE.md")
STATUS_POLICY = Path("harness/status_label_policy.yml")
HUMAN_GATE_QUEUE = Path("decisions/human_gate_queue.yml")
ROLLOUT_PLAYBOOK = Path("harness/rollout_playbook.md")

CURRENT_STATE_FIELDS = [
    "current_goal:",
    "latest_substantive_artifact:",
    "current_blocker:",
    "next_command:",
    "does_not_prove:",
    "last_validation:",
]

STATUS_LABELS = {"CHECK_PASS", "CAPTURE_LOGGED", "ROUTE_READY", "SUBSTANTIVE_PRODUCED"}
STATUS_LABEL_ALIASES = {"SUBSTANTIVE_DONE"}
QUEUE_REQUIRED_FIELDS = {
    "project",
    "request",
    "why_human_needed",
    "after_approval_codex_can",
    "risk_boundary",
    "status",
}


def main() -> int:
    failures: list[str] = []

    if not CURRENT_STATE.exists():
        failures.append("missing CURRENT_STATE.md")
    else:
        text = CURRENT_STATE.read_text(encoding="utf-8")
        for field in CURRENT_STATE_FIELDS:
            if field not in text:
                failures.append(f"CURRENT_STATE.md missing field {field}")

    if yaml is None:
        failures.append("PyYAML is required to validate operating dashboard policy files")
    else:
        if not STATUS_POLICY.exists():
            failures.append("missing harness/status_label_policy.yml")
        else:
            data = yaml.safe_load(STATUS_POLICY.read_text(encoding="utf-8")) or {}
            labels = set((data.get("labels") or {}).keys())
            missing = sorted(STATUS_LABELS - labels)
            if missing:
                failures.append(f"harness/status_label_policy.yml missing label(s): {missing}")
            final_rule = data.get("final_response_rule") or {}
            if final_rule.get("required") is not True:
                failures.append("harness/status_label_policy.yml must require final response labels")

        if not HUMAN_GATE_QUEUE.exists():
            failures.append("missing decisions/human_gate_queue.yml")
        else:
            data = yaml.safe_load(HUMAN_GATE_QUEUE.read_text(encoding="utf-8")) or {}
            items = data.get("items")
            if not isinstance(items, list):
                failures.append("decisions/human_gate_queue.yml items must be a list")
            else:
                allowed = set(((data.get("schema") or {}).get("allowed_statuses") or []))
                for idx, item in enumerate(items, start=1):
                    if not isinstance(item, dict):
                        failures.append(f"human gate queue item {idx} must be a mapping")
                        continue
                    missing = sorted(QUEUE_REQUIRED_FIELDS - set(item.keys()))
                    if missing:
                        failures.append(f"human gate queue item {idx} missing field(s): {missing}")
                    status = str(item.get("status", "")).strip()
                    if allowed and status not in allowed:
                        failures.append(f"human gate queue item {idx} has invalid status {status!r}")

    if not ROLLOUT_PLAYBOOK.exists():
        failures.append("missing harness/rollout_playbook.md")
    else:
        text = ROLLOUT_PLAYBOOK.read_text(encoding="utf-8")
        for phrase in [
            "tools/sync_aeros_latest.zsh <project_path>",
            "check_work_lanes.py",
            "run_harness_checks.py --timeout 30",
            "CURRENT_STATE.md",
            "CHECK_PASS",
            "ROUTE_READY",
            "SUBSTANTIVE_PRODUCED",
        ]:
            if phrase not in text:
                failures.append(f"harness/rollout_playbook.md missing {phrase!r}")

    if failures:
        print("FAIL: operating dashboard problems detected:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("PASS: operating dashboard files are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
