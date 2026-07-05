#!/usr/bin/env python3
"""Data-completeness gate: required data must be acquired + validated + ratified.

The integrity layers above this (numbers trace to result cells; claims trace to
results) ALL assume the underlying data is complete and correct. Nothing verified
that. This check closes the ungated foundation: before the pipeline may advance
past data readiness, every variable the data_contract declares REQUIRED must be
collected + validated (not merely "located"), and a human must ratify that data
acquisition is complete.

Reads docs/data_contract.yml:
- no contract, or no required_variables  -> PASS (nothing to enforce yet; safe on
  a fresh template before a contract exists).
- otherwise: every required_variables entry needs status in {collected, validated,
  complete}; "located"/"pending"/"missing"/blank is NOT enough. AND a top-level
  human sign-off (data_ratified_by) must be set. Anything missing -> FAIL.

This deliberately mirrors the claim gate: a check confirms structure, a human
ratifies substance. "Located" is the data analog of a draft claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

CONTRACT = Path("docs/data_contract.yml")
CHECK_NAME = "check_data_complete"
OK_STATUS = {"collected", "validated", "complete"}
PLACEHOLDER = {"", "tbd", "todo", "n/a", "na", "none", "pending", "draft"}
REMEDIATION = (
    "In docs/data_contract.yml: give every required_variables entry a "
    "status: collected|validated (not 'located'), and set a top-level "
    "data_ratified_by: <name> once acquisition is genuinely complete."
)


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures,
                          "hint": REMEDIATION if status == "fail" else ""}))
    elif status == "pass":
        print(f"PASS: {note or 'data acquisition complete and ratified'}")
    else:
        print("FAIL: data acquisition not complete/ratified:")
        for f in failures:
            print(f"  - {f}")
        print(f"  HINT: {REMEDIATION}")
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not CONTRACT.exists():
        return _emit(as_json, "pass", [], note=f"{CONTRACT} not present (no data contract yet)")
    try:
        data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return _emit(as_json, "fail", [f"{CONTRACT} is not valid YAML: {exc}"])

    required = data.get("required_variables") or []
    if not isinstance(required, list) or not required:
        return _emit(as_json, "pass", [], note="no required_variables declared yet")

    failures: list[str] = []
    for entry in required:
        if not isinstance(entry, dict):
            failures.append(f"required_variables entry is not a mapping: {entry!r}")
            continue
        name = str(entry.get("name", "?"))
        status = str(entry.get("status", "")).strip().lower()
        if status not in OK_STATUS:
            shown = entry.get("status", "(no status field)")
            failures.append(
                f"required variable '{name}': status {shown!r} is not collected/validated "
                f"(located-only or unset does not satisfy data completeness)"
            )

    # Human ratification of data completeness (the substance check a file cannot do).
    ratified = str(data.get("data_ratified_by", "")).strip().lower()
    if ratified in PLACEHOLDER:
        failures.append("data acquisition is not human-ratified: set top-level "
                        "data_ratified_by: <name> in data_contract.yml")

    if failures:
        return _emit(as_json, "fail", failures)
    return _emit(as_json, "pass", [],
                 note=f"{len(required)} required variable(s) collected/validated; "
                      f"acquisition ratified by {data.get('data_ratified_by')}")


if __name__ == "__main__":
    sys.exit(main())
