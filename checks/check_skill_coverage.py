#!/usr/bin/env python3
"""Validate task-level skill obligation coverage."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.contract import load_contract
from aeros.runtime.skill_obligation import validate_skill_coverage
from aeros.runtime.skill_receipt import write_skill_invocation_receipt

CHECK_NAME = "check_skill_coverage"


def _discover_contracts(root: Path) -> dict:
    contracts = {}
    for path in sorted((root / "tasks").rglob("*.yml")):
        try:
            contract = load_contract(path)
        except Exception:
            continue
        contracts[contract.task_id] = (contract, path)
    return contracts


def _write_fixture(root: Path, *, with_waiver: bool, required: bool = False) -> None:
    task_dir = root / "tasks" / "discovery"
    task_dir.mkdir(parents=True)
    waiver = ""
    if with_waiver:
        waiver = """
skill_waivers:
  - skill_class: data_source
    reason: no source sample exists yet
    scope: blocked_source_probe
    progress_label: ROUTE_READY
"""
    (task_dir / "D999_probe.yml").write_text(
        f"""task_id: D999_probe
stage: discovery
gate: G1
work_lane: data
goal: Probe whether a source exists.
allowed_outputs: [discovery/data_inventory.csv]
checks: [check_data_inventory.py]
allowed_skills: []
recommended_skills: []
required_skill_classes: {["data_source"] if required else []}
{waiver}
""",
        encoding="utf-8",
    )


def main() -> int:
    failures = validate_skill_coverage(ROOT, _discover_contracts(ROOT))

    with tempfile.TemporaryDirectory(prefix="aeros_skill_coverage_") as tmp:
        root = Path(tmp)
        (root / "harness").mkdir()
        (root / "harness" / "skill_map_core.yml").write_text(
            """version: '0.1'
skills:
  data_inventory:
    name: data-inventory
  data_quality_checker:
    name: data-quality-checker
  data_merge_audit:
    name: data-merge-audit
""",
            encoding="utf-8",
        )
        _write_fixture(root, with_waiver=False)
        fixture_failures = validate_skill_coverage(root, _discover_contracts(root))
        if fixture_failures:
            failures.append("fixture: ordinary task incorrectly required skill/waiver: " + "; ".join(fixture_failures))

    with tempfile.TemporaryDirectory(prefix="aeros_skill_coverage_") as tmp:
        root = Path(tmp)
        (root / "harness").mkdir()
        (root / "harness" / "skill_map_core.yml").write_text(
            """version: '0.1'
skills:
  data_inventory:
    name: data-inventory
  data_quality_checker:
    name: data-quality-checker
  data_merge_audit:
    name: data-merge-audit
""",
            encoding="utf-8",
        )
        _write_fixture(root, with_waiver=False, required=True)
        fixture_failures = validate_skill_coverage(root, _discover_contracts(root))
        if fixture_failures:
            failures.append("fixture: required class declaration should defer use-or-waive to completion: " + "; ".join(fixture_failures))

    with tempfile.TemporaryDirectory(prefix="aeros_skill_coverage_") as tmp:
        root = Path(tmp)
        (root / "harness").mkdir()
        (root / "harness" / "skill_map_core.yml").write_text(
            """version: '0.1'
skills:
  data_inventory:
    name: data-inventory
  data_quality_checker:
    name: data-quality-checker
  data_merge_audit:
    name: data-merge-audit
""",
            encoding="utf-8",
        )
        _write_fixture(root, with_waiver=True, required=True)
        fixture_failures = validate_skill_coverage(root, _discover_contracts(root))
        if fixture_failures:
            failures.append("fixture: explicit waiver did not satisfy obligation: " + "; ".join(fixture_failures))

    with tempfile.TemporaryDirectory(prefix="aeros_skill_receipt_") as tmp:
        root = Path(tmp)
        (root / "harness").mkdir()
        (root / "harness" / "skill_map_core.yml").write_text(
            """version: '0.1'
skills:
  data_inventory:
    name: data-inventory
""",
            encoding="utf-8",
        )
        _write_fixture(root, with_waiver=False)
        contract = load_contract(root / "tasks" / "discovery" / "D999_probe.yml")
        receipt = write_skill_invocation_receipt(root, contract, skills_used=[], run_report_path=None)
        text = receipt.read_text(encoding="utf-8")
        if "missing_skill_decision: false" not in text or "verdict: pass" not in text:
            failures.append("fixture: ordinary task incorrectly failed skill receipt")

    if "--json" in sys.argv:
        print(json.dumps({"check": CHECK_NAME, "status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: skill coverage problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: skill coverage obligations are valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
