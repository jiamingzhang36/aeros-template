#!/usr/bin/env python3
"""Validate the AEROS control-tax dashboard."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.control_tax import build_control_tax, format_control_tax_dashboard  # noqa: E402


def main() -> int:
    failures: list[str] = []
    try:
        report = build_control_tax(ROOT)
        rendered = format_control_tax_dashboard(report)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: control-tax dashboard generation failed: {exc}")
        return 1
    summary = report.get("summary") or {}
    for key in ["control_actions", "substantive_actions", "route_actions", "human_decisions", "accepted_artifacts"]:
        if key not in summary:
            failures.append(f"missing summary key {key}")
        elif not isinstance(summary.get(key), int):
            failures.append(f"summary key {key} must be an integer")
    for key in ["control_action_share", "substantive_action_share"]:
        value = report.get(key)
        if not isinstance(value, (int, float)) or value < 0 or value > 1:
            failures.append(f"{key} must be a share in [0, 1]")
    for marker in ["AEROS Control Tax Dashboard", "control_actions", "substantive_actions", "Does Not Prove"]:
        if marker not in rendered:
            failures.append(f"rendered dashboard missing marker {marker!r}")
    if "claim support" not in (report.get("does_not_prove") or []):
        failures.append("does_not_prove missing claim-support boundary")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: control-tax dashboard is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
