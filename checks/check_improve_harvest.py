#!/usr/bin/env python3
"""Validate improvement harvest report generation."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.improve_harvest import harvest_improvements


def main() -> int:
    failures: list[str] = []
    report = harvest_improvements(ROOT)
    if report.get("status") != "ADVISORY" or not report.get("backlog_candidates"):
        failures.append("template harvest did not produce advisory candidates")
    with tempfile.TemporaryDirectory(prefix="aeros_improve_harvest_") as tmp:
        root = Path(tmp)
        receipt_dir = root / "agent_runs" / "skill_invocations"
        receipt_dir.mkdir(parents=True)
        (receipt_dir / "T001_skill_invocations.yml").write_text(
            """task_id: T001
skill_obligations: [data_source]
skills_used: []
skill_waivers:
  - skill_class: data_source
    reason: blocked
""",
            encoding="utf-8",
        )
        harvested = harvest_improvements(root)
        if not any(item.get("kind") == "skill_waiver_pattern" for item in harvested.get("backlog_candidates", [])):
            failures.append("fixture: skill waiver pattern was not harvested")
    if "--json" in sys.argv:
        print(json.dumps({"status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: improve harvest problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: improvement harvest is valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
