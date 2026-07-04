#!/usr/bin/env python3
"""Validate output intent declarations."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.contract import load_contract
from aeros.runtime.output_intent import VALID_OUTPUT_INTENTS, validate_all_output_intents

POLICY = Path("harness/output_intent_policy.yml")


def _discover_contracts(root: Path) -> dict:
    contracts = {}
    for path in sorted((root / "tasks").rglob("*.yml")):
        try:
            contract = load_contract(path)
        except Exception:
            continue
        contracts[contract.task_id] = (contract, path)
    return contracts


def main() -> int:
    failures: list[str] = []
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    declared = set((policy or {}).get("valid_output_intents") or [])
    if declared != VALID_OUTPUT_INTENTS:
        failures.append("output intent policy does not match runtime valid intent set")
    failures.extend(validate_all_output_intents(ROOT, _discover_contracts(ROOT)))

    with tempfile.TemporaryDirectory(prefix="aeros_output_intent_") as tmp:
        root = Path(tmp)
        task_dir = root / "tasks" / "discovery"
        task_dir.mkdir(parents=True)
        (task_dir / "BAD.yml").write_text(
            """task_id: BAD
stage: discovery
allowed_outputs: [work/source.html]
checks: []
output_intents:
  work/source.html: final_truth
""",
            encoding="utf-8",
        )
        bad = validate_all_output_intents(root, _discover_contracts(root))
        if not bad:
            failures.append("fixture: invalid output intent did not fail")
    if "--json" in sys.argv:
        print(json.dumps({"status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: output intent problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: output intents are valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
