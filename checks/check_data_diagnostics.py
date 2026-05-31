#!/usr/bin/env python3
"""Check that data_diagnostics.yml is measured (not stub) and has required metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

DIAG = Path("discovery/data_diagnostics.yml")
REQUIRED_METRICS = [
    "n_ban_states_with_firm_presence",
    "bill_text_extractable_states",
    "n_states_with_ban_dates",
    "donor_pool_size",
]
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
        return _emit(as_json, "fail", [f"missing {DIAG} — run D005 probe first"])

    d = yaml.safe_load(DIAG.read_text(encoding="utf-8")) or {}
    failures: list[str] = []

    if str(d.get("status", "")).strip().lower() != "measured":
        failures.append(
            f"status is {d.get('status')!r} — must be 'measured'; "
            "run python3 code/01_ingest/probe_data_diagnostics.py")

    diags = d.get("diagnostics", {}) or {}
    for m in REQUIRED_METRICS:
        if m not in diags:
            failures.append(f"missing diagnostic: {m}")
        elif not isinstance(diags[m], (int, float)):
            failures.append(f"{m} must be numeric, got {type(diags[m]).__name__}")

    return _emit(as_json, "fail" if failures else "pass", failures)


if __name__ == "__main__":
    sys.exit(main())
