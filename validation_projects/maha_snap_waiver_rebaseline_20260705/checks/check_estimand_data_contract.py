#!/usr/bin/env python3
"""Validate the EstimandDataContract scaffold.

The root template may keep values empty/draft. Once a project sets status to
active/locked, required fields must be non-empty.
"""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


PATH = Path("docs/data_contract.yml")
REQUIRED_SECTIONS = [
    "research_question",
    "unit_of_observation",
    "population",
    "treatment_or_exposure",
    "outcome",
    "comparison",
    "time_window",
    "required_variation",
    "required_variables",
    "join_keys",
    "minimum_coverage",
    "maximum_missingness",
    "quality_thresholds",
    "probe_sampling_strategy",
    "probe_success_condition",
    "probe_stop_condition",
    "source_access_class",
    "license_class",
    "credential_requirement",
    "estimated_cost",
    "fallback_source",
]


def _empty(value: object) -> bool:
    return value in (None, "", [], {})


def main() -> int:
    if not PATH.exists():
        print(f"FAIL: missing {PATH}")
        return 1
    data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
    contract = data.get("estimand_data_contract") or {}
    failures: list[str] = []
    if not isinstance(contract, dict):
        failures.append("estimand_data_contract must be a mapping")
        contract = {}
    for key in REQUIRED_SECTIONS:
        if key not in contract:
            failures.append(f"estimand_data_contract missing {key}")
    status = str(contract.get("status") or data.get("data_contract", {}).get("status") or "draft")
    if status in {"active", "locked"}:
        for key in REQUIRED_SECTIONS:
            if _empty(contract.get(key)):
                failures.append(f"active/locked estimand_data_contract has empty {key}")
    if failures:
        print("FAIL: EstimandDataContract problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    if status == "draft":
        print("PASS: scaffold_only EstimandDataContract scaffold is valid (draft, not evidence-bound)")
    else:
        print("PASS: EstimandDataContract is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
