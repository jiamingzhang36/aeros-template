#!/usr/bin/env python3
"""Validate improvement harvest report generation."""

from __future__ import annotations

import json
import os
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
        project = root / "project"
        project.mkdir()
        (project / "project_manifest.yml").write_text("project:\n  name: lagging\n", encoding="utf-8")
        template = root / "template"
        (template / "tools").mkdir(parents=True)
        (template / "tools" / "sync_aeros_latest.zsh").write_text("# fixture template\n", encoding="utf-8")
        completion_dir = root / "agent_runs" / "completion_receipts"
        completion_dir.mkdir(parents=True)
        (completion_dir / "T002.yml").write_text(
            """task_id: T002
progress_class: substantive
progress_label: SUBSTANTIVE_PRODUCED
staging_artifact_paths: [work/source.html]
substantive_evidence_paths: []
""",
            encoding="utf-8",
        )
        old_template_root = os.environ.get("AEROS_TEMPLATE_ROOT")
        os.environ["AEROS_TEMPLATE_ROOT"] = template.as_posix()
        try:
            harvested = harvest_improvements(root, project_roots=[project.as_posix()])
        finally:
            if old_template_root is None:
                os.environ.pop("AEROS_TEMPLATE_ROOT", None)
            else:
                os.environ["AEROS_TEMPLATE_ROOT"] = old_template_root
        if not any(item.get("kind") == "skill_waiver_pattern" for item in harvested.get("backlog_candidates", [])):
            failures.append("fixture: skill waiver pattern was not harvested")
        if not any(item.get("kind") == "project_version_lag" for item in harvested.get("backlog_candidates", [])):
            failures.append("fixture: project version lag was not harvested")
        if not any(item.get("kind") == "staging_as_substantive_risk" for item in harvested.get("backlog_candidates", [])):
            failures.append("fixture: staging-as-substantive risk was not harvested")
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
