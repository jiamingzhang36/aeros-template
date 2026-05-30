#!/usr/bin/env python3
"""Verify design_selection.md matches a fresh adjudication (no faking/staleness).

The selection record must equal what re-running the deterministic engine on the
current options + diagnostics produces; otherwise the earned claim could be
stale or hand-edited. Passes (skips) when there is no selection yet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

# Make the in-repo aeros package importable without requiring a pip install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.adjudicate import adjudicate  # noqa: E402

SELECTION = Path("discovery/design_selection.md")
CHECK_NAME = "check_design_selection"


def _front_matter(path: Path) -> dict:
    t = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, flags=re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def _emit(as_json: bool, status: str, failures: list[str]) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif status == "pass":
        print("PASS: design selection matches a fresh adjudication")
    else:
        print("FAIL: design selection problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the design selection record.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not SELECTION.exists():
        return _emit(as_json, "pass", [])  # nothing selected yet

    fm = _front_matter(SELECTION)
    fresh = adjudicate(Path("."))
    sel = fresh["selected"]
    expected_sel = sel["id"] if sel else "none"
    expected_claim = fresh["earned_claim"] or "none"

    failures: list[str] = []
    if str(fm.get("selected_design", "")).strip() != str(expected_sel):
        failures.append(
            f"selected_design is {fm.get('selected_design')!r} but fresh adjudication "
            f"selects {expected_sel!r} — selection is stale; re-run `aeros adjudicate`")
    if str(fm.get("earned_claim_ceiling", "")).strip() != str(expected_claim):
        failures.append(
            f"earned_claim_ceiling is {fm.get('earned_claim_ceiling')!r} but fresh "
            f"adjudication earns {expected_claim!r} — re-run `aeros adjudicate`")

    return _emit(as_json, "fail" if failures else "pass", failures)


if __name__ == "__main__":
    sys.exit(main())
