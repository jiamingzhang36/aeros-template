#!/usr/bin/env python3
"""Check that data_diagnostics.yml records measured project diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

DIAG = Path("discovery/data_diagnostics.yml")
CHECK_NAME = "check_data_diagnostics"


def _emit(as_json: bool, status: str, failures: list[str]) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif status == "pass":
        print("PASS: data diagnostics are measured and complete")
    else:
        print("FAIL: data diagnostics problems:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not DIAG.exists():
        return _emit(as_json, "fail", [f"missing {DIAG} - run the project data probe first"])

    d = yaml.safe_load(DIAG.read_text(encoding="utf-8")) or {}
    failures: list[str] = []

    if str(d.get("status", "")).strip().lower() != "measured":
        failures.append(
            f"status is {d.get('status')!r} - must be 'measured' after project-specific data probing"
        )

    diags = d.get("diagnostics", {}) or {}
    if not isinstance(diags, dict) or not diags:
        failures.append("diagnostics must contain at least one measured numeric metric")
    else:
        numeric_count = 0
        for key, value in diags.items():
            if isinstance(value, (int, float)):
                numeric_count += 1
            elif isinstance(value, (dict, list)):
                # Allow auxiliary structured diagnostics (e.g. per-term counts).
                # Machine-adjudicable viability tests should reference numeric
                # top-level metrics.
                continue
            else:
                failures.append(f"{key} must be numeric, got {type(value).__name__}")
        if numeric_count == 0:
            failures.append("diagnostics must contain at least one measured numeric metric")

    return _emit(as_json, "fail" if failures else "pass", failures)


if __name__ == "__main__":
    sys.exit(main())
