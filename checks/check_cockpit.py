#!/usr/bin/env python3
"""Validate the AEROS cockpit view."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aeros.runtime.cockpit import build_cockpit, format_cockpit  # noqa: E402


def main() -> int:
    failures: list[str] = []
    try:
        cockpit = build_cockpit(ROOT, lane="project", check_profile="smoke")
        rendered = format_cockpit(cockpit)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"cockpit generation failed: {exc}")
        cockpit = {}
        rendered = ""
    if cockpit:
        for key in ["context", "next_action", "fast_check_command", "context_graph_summary"]:
            if key not in cockpit:
                failures.append(f"cockpit missing {key}")
        if "--profile smoke" not in str(cockpit.get("fast_check_command", "")):
            failures.append("cockpit fast check does not use smoke profile")
        label = (cockpit.get("next_action") or {}).get("status_label")
        if label not in {"CHECK_PASS", "ROUTE_READY", "SUBSTANTIVE_DONE"}:
            failures.append(f"cockpit next_action has invalid status label {label!r}")
    for marker in ["AEROS COCKPIT", "Recommended Next", "Does Not Prove", "navigation view"]:
        if marker not in rendered:
            failures.append(f"rendered cockpit missing marker {marker!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: cockpit view is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
