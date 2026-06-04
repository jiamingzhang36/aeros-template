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
import re
import sys
from pathlib import Path

import yaml

ANCHOR = Path("discovery/anchor.yml")
CLAIMS = Path("evidence/claim_registry.md")
CHECK_NAME = "check_anchor"

REQUIRED = ["topic", "claim_type", "identification", "data"]

# The one robust distinction (not a 7-level ladder, which mis-ranks different
# KINDS of claims as if they were strengths): does the claim assert more than an
# association? "Beyond-association" claims (causal and everything that presupposes
# causality) are drift when the anchor is only descriptive/associational.
ASSOCIATION_OR_BELOW = {"descriptive", "associational", "correlational"}
BEYOND_ASSOCIATION = {"causal", "mechanism", "external_validity",
                      "policy_translation", "forecast"}
KNOWN_TYPES = ASSOCIATION_OR_BELOW | BEYOND_ASSOCIATION


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


def _claim_types() -> tuple[list[tuple[str, str]], bool]:
    """Return (rows of (claim_id, type), looks_populated).

    looks_populated is True when the registry clearly contains claim content but
    we parsed zero rows -- a format mismatch we must surface loudly instead of
    silently passing (#2: a check that silently lies is worse than no check)."""
    if not CLAIMS.exists():
        return [], False
    text = CLAIMS.read_text(encoding="utf-8")
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("| C") or line.startswith("| Claim ID"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0]:
            rows.append((cells[0], cells[2]))
    # Fail-loud signal: real claim-id tokens (C001-style) are present but NONE
    # parsed into the expected table shape. Requires actual claim ids, so an
    # empty-template registry (header + legend only) does NOT trip this.
    has_claim_ids = bool(
        re.search(r"(?m)^\|\s*C\d", text)          # malformed table row
        or re.search(r"(?m)^\s*[-*]?\s*C\d{3}\b", text)  # list/alt format claim id
    )
    looks_populated = (not rows) and has_claim_ids
    return rows, looks_populated


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

    anchor_type = _norm(anchor.get("claim_type", ""))
    if anchor_type and anchor_type not in KNOWN_TYPES:
        failures.append(f"anchor.claim_type {anchor.get('claim_type')!r} is not a known claim type "
                        f"({', '.join(sorted(KNOWN_TYPES))})")

    rows, looks_populated = _claim_types()
    if looks_populated:
        failures.append(f"{CLAIMS} appears to contain claims but none could be parsed "
                        "(format mismatch?) — refusing to pass silently")

    # The one robust drift rule: if the anchor only commits to association or
    # below, no claim may assert beyond association (causal and what presupposes it).
    if anchor_type in ASSOCIATION_OR_BELOW:
        for claim_id, claim_type in rows:
            if _norm(claim_type) in BEYOND_ASSOCIATION:
                failures.append(
                    f"DRIFT: {claim_id} is '{claim_type}' but the anchor commits only to "
                    f"'{anchor.get('claim_type')}' — a claim may not go beyond association "
                    "without re-anchoring at intake"
                )

    if failures:
        return _emit(as_json, "fail", failures)
    return _emit(as_json, "pass", [],
                 note=f"anchor locked; 4 components set; no claim drifts beyond anchor "
                      f"'{anchor.get('claim_type')}' ({len(rows)} claim(s) checked)")


if __name__ == "__main__":
    sys.exit(main())
