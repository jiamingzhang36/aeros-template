#!/usr/bin/env python3
"""Validate AEROS skill routing declarations and invocation receipts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.contract import load_contract  # noqa: E402
from aeros.runtime.skill_receipt import validate_skill_invocations  # noqa: E402

CHECK_NAME = "check_skill_invocations"


def _discover_contracts(root: Path) -> dict:
    contracts = {}
    for path in sorted((root / "tasks").rglob("*.yml")):
        try:
            contract = load_contract(path)
        except Exception:
            continue
        contracts[contract.task_id] = (contract, path)
    return contracts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path.cwd()
    failures = validate_skill_invocations(root, _discover_contracts(root))
    if args.json:
        print(json.dumps({"check": CHECK_NAME, "status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: skill invocation receipt problems detected:")
        for failure in failures:
            print(f"  - {failure}")
    else:
        print("PASS: skill invocation receipts are valid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
