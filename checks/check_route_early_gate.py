#!/usr/bin/env python3
"""Validate route decision early-gate behavior."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.route_gate import validate_route_early_gate


def main() -> int:
    failures: list[str] = []
    template_report = validate_route_early_gate(ROOT, intent="quick smoke")
    if template_report["status"] != "PASS":
        failures.extend(template_report["failures"])

    with tempfile.TemporaryDirectory(prefix="aeros_route_gate_") as tmp:
        root = Path(tmp)
        (root / "discovery").mkdir()
        (root / "discovery" / "route_decision.yml").write_text(
            """version: '0.1'
decision_status: pending
selected_route: pending
allowed_routes: [negative_seed_first, base_universe_first]
current_decision: {route: pending, decision_ref: ''}
""",
            encoding="utf-8",
        )
        bad = validate_route_early_gate(root, intent="source_capture denominator")
        if bad["status"] != "FAIL":
            failures.append("fixture: pending route did not block route-sensitive source work")
        (root / "discovery" / "route_decision.yml").write_text(
            """version: '0.1'
decision_status: proposed
selected_route: negative_seed_first
allowed_routes: [negative_seed_first, base_universe_first]
current_decision: {route: negative_seed_first, decision_ref: route-packet}
""",
            encoding="utf-8",
        )
        good = validate_route_early_gate(root, intent="source_capture denominator")
        if good["status"] != "PASS":
            failures.append("fixture: proposed selected route did not satisfy early gate")
    if "--json" in sys.argv:
        print(json.dumps({"status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: route early-gate problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: route early gate is valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
