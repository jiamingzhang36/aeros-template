#!/usr/bin/env python3
"""Validate the correction ledger (the harness's evolving-constraint memory)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

LEDGER = Path("harness/correction_ledger.yml")
CHECK_NAME = "check_correction_ledger"
REQUIRED = ("id", "date", "type", "scope", "symptom", "root_cause", "lesson", "enforced_by")
TYPES = {"agent-lesson", "runtime-fix"}


def _emit(as_json: bool, status: str, failures: list[str], n: int) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "entries": n,
                          "failures": failures}, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: correction ledger is well-formed ({n} entry/entries)")
    else:
        print("FAIL: correction ledger problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the correction ledger.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not LEDGER.exists():
        return _emit(as_json, "pass", [], 0)  # optional artifact
    try:
        data = yaml.safe_load(LEDGER.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return _emit(as_json, "fail", [f"ledger is not valid YAML: {exc}"], 0)

    entries = data.get("corrections", [])
    if not isinstance(entries, list):
        return _emit(as_json, "fail", ["'corrections' must be a list"], 0)

    failures: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            failures.append(f"entry #{i+1}: not a mapping")
            continue
        cid = str(e.get("id", "")).strip() or f"#{i+1}"
        if cid in seen:
            failures.append(f"{cid}: duplicate id")
        seen.add(cid)
        for f in REQUIRED:
            v = e.get(f)
            if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v):
                failures.append(f"{cid}: missing/empty {f}")
        if str(e.get("type", "")).strip() not in TYPES:
            failures.append(f"{cid}: type must be one of {sorted(TYPES)}")

    return _emit(as_json, "fail" if failures else "pass", failures, len(entries))


if __name__ == "__main__":
    sys.exit(main())
