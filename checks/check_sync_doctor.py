#!/usr/bin/env python3
"""Validate sync doctor capability drift detection."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.sync_doctor import diagnose_project, sync_doctor


def main() -> int:
    failures: list[str] = []
    report = sync_doctor(ROOT, projects=[])
    if report.get("status") not in {"PASS", "ATTENTION"}:
        failures.append("template sync doctor returned invalid status")
    with tempfile.TemporaryDirectory(prefix="aeros_sync_doctor_") as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        (project / "project_manifest.yml").write_text("project:\n  name: fixture\n", encoding="utf-8")
        diag = diagnose_project(ROOT, project)
        if diag.get("status") != "ATTENTION":
            failures.append("fixture: missing framework files did not produce ATTENTION")
        missing = set(diag.get("missing_capabilities") or [])
        if not {"improve", "mode", "route_gate", "workflow_presets", "output_intent", "task_preflight"} & missing:
            failures.append("fixture: expected missing capabilities were not reported")
    if "--json" in sys.argv:
        print(json.dumps({"status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: sync doctor problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: sync doctor is valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
