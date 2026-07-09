#!/usr/bin/env python3
"""Validate sync doctor capability drift detection."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("FAIL: PyYAML is required for check_sync_doctor.py") from exc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.sync_doctor import CAPABILITIES, CAPABILITY_EXEMPT_CHECKS, diagnose_project, sync_doctor


def _profile_checks() -> set[str]:
    data = yaml.safe_load((ROOT / "harness/check_profiles.yml").read_text(encoding="utf-8")) or {}
    checks: set[str] = set()
    for profile in (data.get("profiles") or {}).values():
        values = (profile or {}).get("checks")
        if isinstance(values, list):
            checks.update(str(item) for item in values)
    return checks


def _capability_checks() -> set[str]:
    checks: set[str] = set()
    for rels in CAPABILITIES.values():
        for rel in rels:
            if rel.startswith("checks/"):
                checks.add(Path(rel).name)
    return checks


def main() -> int:
    failures: list[str] = []
    profile_checks = _profile_checks()
    covered = _capability_checks()
    missing_meta = sorted(profile_checks - covered - set(CAPABILITY_EXEMPT_CHECKS))
    if missing_meta:
        failures.append(
            "profile check(s) missing from sync doctor CAPABILITIES or explicit exemption list: "
            + ", ".join(missing_meta)
        )
    stale_exemptions = sorted(set(CAPABILITY_EXEMPT_CHECKS) - profile_checks)
    if stale_exemptions:
        failures.append(
            "sync doctor exemption(s) no longer appear in check_profiles.yml: "
            + ", ".join(stale_exemptions)
        )
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
        expected_missing = {
            "improve",
            "mode",
            "broad_capture",
            "route_gate",
            "workflow_presets",
            "output_intent",
            "task_preflight",
            "harness_observed_receipts",
            "update_ledger_hash_chain",
            "protected_path_hook",
            "evidence_sufficiency_audit",
            "submission_research_driver",
            "skill_use_attestation",
            "current_work_context",
        }
        if not expected_missing <= missing:
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
