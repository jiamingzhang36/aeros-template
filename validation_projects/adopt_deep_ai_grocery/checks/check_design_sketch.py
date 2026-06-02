#!/usr/bin/env python3
"""Validate the design sketch and its grounding in framing + data.

A design sketch is where framing (frameworks + roles) and data scouting converge
into a concrete candidate design. This check enforces that the design is
GROUNDED, not free-form:
  - required sections are present and non-placeholder;
  - project_type and claim_type are declared from controlled vocabularies;
  - every data source it leans on (grounded_data_ids) actually exists in
    data_inventory.csv;
  - it ADDRESSES every identification-threat the framing deck flagged (a design
    cannot silently ignore a threat the reasoning step already named).

Runs only against a produced sketch (status: filled); otherwise it reports the
sketch is not yet filled.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

SKETCH = Path("discovery/design_sketch.md")
DECK = Path("discovery/literature/framing_deck.yml")
INVENTORY = Path("discovery/data_inventory.csv")
CHECK_NAME = "check_design_sketch"

PROJECT_TYPES = {"causal", "descriptive", "measurement", "prediction",
                 "policy-translation", "mechanism", "replication"}
REQUIRED_SECTIONS = [
    "## Research Question", "## Project Type", "## Unit of Analysis",
    "## Treatment / Exposure", "## Outcome", "## Identification Strategy",
    "## Threats to Validity", "## Candidate Data",
    "## Minimum Viable Version", "## Claim Boundary",
]
PLACEHOLDERS = {"", "tbd", "todo", "to be determined", "n/a", "na", "none"}

REMEDIATION_HINT = (
    "Fill design_sketch.md: front matter needs status: filled, project_type "
    "(causal|descriptive|measurement|prediction|policy-translation|mechanism), "
    "claim_type, grounded_data_ids (each must exist in data_inventory.csv), and "
    "addresses_threats covering every identification-threat card in framing_deck.yml. "
    "All required sections must have real content."
)


def _front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return (fm if isinstance(fm, dict) else {}), text[m.end():]


def _section_meaningful(body: str, heading: str) -> bool:
    lines = body.splitlines()
    try:
        i = next(k for k, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return False
    for ln in lines[i + 1:]:
        if ln.startswith("## "):
            break
        s = ln.strip()
        if s and not s.startswith("#") and s.lower() not in PLACEHOLDERS:
            return True
    return False


def _emit(as_json: bool, status: str, failures: list[str]) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures,
                          "hint": REMEDIATION_HINT if status == "fail" else ""},
                         ensure_ascii=False))
    elif status == "pass":
        print("PASS: design sketch is valid and grounded")
    else:
        print("FAIL: design sketch problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the design sketch.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not SKETCH.exists():
        return _emit(as_json, "fail", [f"missing {SKETCH}"])
    fm, body = _front_matter(SKETCH.read_text(encoding="utf-8"))

    if str(fm.get("status", "")).strip().lower() != "filled":
        return _emit(as_json, "fail", ["design_sketch.md is not status: filled (not produced yet)"])

    failures: list[str] = []

    pt = str(fm.get("project_type", "")).strip().lower()
    if pt not in PROJECT_TYPES:
        failures.append(f"project_type must be one of {sorted(PROJECT_TYPES)}, got {pt!r}")
    if str(fm.get("claim_type", "")).strip().lower() in PLACEHOLDERS:
        failures.append("claim_type is empty")

    # grounded_data_ids must exist in the inventory
    valid_ids: set[str] = set()
    if INVENTORY.exists():
        with INVENTORY.open(newline="", encoding="utf-8") as fh:
            valid_ids = {r["data_id"].strip() for r in csv.DictReader(fh) if r.get("data_id", "").strip()}
    g_ids = fm.get("grounded_data_ids", []) or []
    if not isinstance(g_ids, list) or not g_ids:
        failures.append("grounded_data_ids must be a non-empty list of data_inventory ids")
    else:
        for d in g_ids:
            if str(d).strip() not in valid_ids:
                failures.append(f"grounded_data_id {d!r} is not in data_inventory.csv")

    # must address every identification-threat card from the framing deck
    threat_cards: set[str] = set()
    if DECK.exists():
        deck = yaml.safe_load(DECK.read_text(encoding="utf-8")) or {}
        for c in deck.get("cards", []) or []:
            if isinstance(c, dict) and str(c.get("role", "")).strip().lower() == "identification-threat" \
                    and str(c.get("decision", "proposed")).strip().lower() != "drop":
                threat_cards.add(str(c.get("id", "")).strip())
    addressed = {str(x).strip() for x in (fm.get("addresses_threats", []) or [])}
    missing_threats = threat_cards - addressed
    if missing_threats:
        failures.append(
            f"design must address every framing identification-threat card; "
            f"missing: {', '.join(sorted(missing_threats))}")

    for sec in REQUIRED_SECTIONS:
        if sec not in body:
            failures.append(f"missing section {sec}")
        elif not _section_meaningful(body, sec):
            failures.append(f"section {sec} has no real content")

    return _emit(as_json, "fail" if failures else "pass", failures)


if __name__ == "__main__":
    sys.exit(main())
