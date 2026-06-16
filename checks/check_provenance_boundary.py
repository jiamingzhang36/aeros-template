#!/usr/bin/env python3
"""Validate provenance boundary rules that separate feasibility from claim support."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

BOUNDARY = Path("harness/provenance_boundary.yml")
REQUIRED_RULES = {
    "probe_cannot_support_claim",
    "validated_result_can_support_claim",
    "human_receipt_cannot_create_data_fact",
    "action_receipt_is_progress_metadata",
}


def main() -> int:
    if not BOUNDARY.exists():
        print(f"FAIL: missing {BOUNDARY}")
        return 1
    data = yaml.safe_load(BOUNDARY.read_text(encoding="utf-8")) or {}
    rules = data.get("rules", []) if isinstance(data, dict) else []
    seen = {str(rule.get("id", "")) for rule in rules if isinstance(rule, dict)}
    failures = []
    for rule_id in sorted(REQUIRED_RULES - seen):
        failures.append(f"missing provenance boundary rule: {rule_id}")
    for rule in rules if isinstance(rules, list) else []:
        if not isinstance(rule, dict):
            failures.append("boundary rule must be a mapping")
            continue
        if not str(rule.get("id", "")).strip():
            failures.append("boundary rule missing id")
        if "may_directly_support_claim" not in rule:
            failures.append(f"{rule.get('id', '(missing)')}: missing may_directly_support_claim")
    if failures:
        print("FAIL: provenance boundary problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: provenance boundary rules valid ({len(rules)} rule(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
