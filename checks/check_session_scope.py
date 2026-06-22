#!/usr/bin/env python3
"""Validate session scope guard policy and active-session drift if present."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.session_guard import LANES, audit_session, load_policy, start_session  # noqa: E402


def main() -> int:
    root = Path.cwd()
    policy = load_policy(root)
    failures: list[str] = []
    lanes = policy.get("lanes") or {}
    for lane in LANES:
        lane_policy = lanes.get(lane) or {}
        if not lane_policy.get("allowed_prefixes"):
            failures.append(f"lane {lane} has no allowed_prefixes")
        if "forbidden_prefixes" not in lane_policy:
            failures.append(f"lane {lane} missing forbidden_prefixes")
    common = policy.get("common_allowed_prefixes") or []
    for required in ["SESSION_CONTRACT.yml", "agent_runs/", "outputs/logs/", "decisions/revision_log.md"]:
        if required not in common:
            failures.append(f"common_allowed_prefixes missing {required}")
    try:
        _, payload = start_session(root, lane="data", objective="dry-run schema check", dry_run=True)
    except Exception as exc:
        failures.append(f"session start dry-run failed: {exc}")
        payload = {}
    if payload and payload.get("active_lane") != "data":
        failures.append("session start dry-run did not preserve lane")
    audit = audit_session(root)
    if audit.active and audit.off_scope_files:
        failures.append("active session has off-scope changes: " + ", ".join(audit.off_scope_files))
    if failures:
        print("FAIL: session scope guard problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: session scope guard is configured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
