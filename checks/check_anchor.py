#!/usr/bin/env python3
"""Anchor check: the 4-component research anchor, set once and frozen (anti-drift).

Team Paper Lite's "下锚": four components -- topic, claim_type, identification,
data -- are fixed once at intake and never re-anchored. The anchor is the single
upstream contract everything downstream must respect. This is the structural
defense against the most common failure in AI-assisted empirical work: a project
that starts descriptive and silently drifts into causal language.

Behavior:
- Missing or status: draft  -> PASS (nothing locked yet; safe on a fresh template).
- status: locked            -> ENFORCE: all four components filled, claim_type is a
  known type, and NO registered claim exceeds the anchor's claim_type ceiling.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ANCHOR = Path("discovery/anchor.yml")
CLAIMS = Path("evidence/claim_registry.md")
CHECK_NAME = "check_anchor"

REQUIRED = ["topic", "claim_type", "identification", "data"]

# Claim-strength ladder (consistent with AGENTS.md claim taxonomy). A claim whose
# type ranks above the anchor's claim_type is drift and must be blocked.
RANK = {
    "descriptive": 1,
    "associational": 2,
    "correlational": 2,
    "causal": 3,
    "mechanism": 4,
    "external_validity": 5,
    "policy_translation": 6,
    "forecast": 7,
}


def _norm(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif status == "pass":
        print(f"PASS: {note or 'anchor consistent'}")
    else:
        print("FAIL: anchor problems detected:")
        for f in failures:
            print(f"  - {f}")
    return 0 if status == "pass" else 1


def _claim_types() -> list[tuple[str, str]]:
    """Return (claim_id, type) from the claim registry markdown table."""
    if not CLAIMS.exists():
        return []
    rows: list[tuple[str, str]] = []
    for line in CLAIMS.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| C") or line.startswith("| Claim ID"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0]:
            rows.append((cells[0], cells[2]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not ANCHOR.exists():
        return _emit(as_json, "pass", [], note=f"{ANCHOR} not present yet (anchor not locked)")

    data = yaml.safe_load(ANCHOR.read_text(encoding="utf-8")) or {}
    anchor = data.get("anchor", data) if isinstance(data, dict) else {}
    status = _norm(anchor.get("status", "draft"))

    if status != "locked":
        return _emit(as_json, "pass", [], note=f"anchor status is {status!r} (not locked; not yet enforced)")

    failures: list[str] = []
    for field in REQUIRED:
        if not str(anchor.get(field, "")).strip():
            failures.append(f"locked anchor is missing component: {field}")

    ceiling_type = _norm(anchor.get("claim_type", ""))
    ceiling = RANK.get(ceiling_type)
    if ceiling_type and ceiling is None:
        failures.append(f"anchor.claim_type {anchor.get('claim_type')!r} is not a known claim type "
                        f"({', '.join(sorted(set(RANK)))})")

    if ceiling is not None:
        for claim_id, claim_type in _claim_types():
            ctype = _norm(claim_type)
            crank = RANK.get(ctype)
            if crank is None:
                continue  # unknown/blank claim type handled by other checks
            if crank > ceiling:
                failures.append(
                    f"DRIFT: {claim_id} is '{claim_type}' but the anchor ceiling is "
                    f"'{anchor.get('claim_type')}' — claims may not exceed the anchor set at intake"
                )

    if failures:
        return _emit(as_json, "fail", failures)
    return _emit(as_json, "pass", [],
                 note=f"anchor locked; 4 components set; no claim exceeds ceiling '{anchor.get('claim_type')}'")


if __name__ == "__main__":
    sys.exit(main())
