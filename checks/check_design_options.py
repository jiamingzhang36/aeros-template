#!/usr/bin/env python3
"""Validate the design-options deck: ranked candidate designs with data gates.

Empirical design is data-contingent: you do not commit to one design upfront,
you hold ranked candidates each guarded by a DATA-VIABILITY condition, and the
choice is deferred until the data is in hand. This check enforces that the deck
is a real such mechanism:
  - >= 2 candidate designs, each with a checkable viability_condition, a unique
    priority, and a claim_boundary;
  - at least one fallback-floor design (always viable) so the project never has
    zero feasible designs;
  - every causal/mechanism candidate addresses all framing identification-threat
    cards (whichever causal design is selected must handle them);
  - a Selection Rule section describing the data-triggered choice.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

OPTIONS = Path("discovery/design_options.md")
DECK = Path("discovery/literature/framing_deck.yml")
CHECK_NAME = "check_design_options"

PROJECT_TYPES = {"causal", "descriptive", "measurement", "prediction",
                 "policy-translation", "mechanism", "replication"}
CAUSAL_TYPES = {"causal", "mechanism"}
PLACEHOLDERS = {"", "tbd", "todo", "to be determined", "n/a", "na", "none"}

REMEDIATION_HINT = (
    "Fill design_options.md: front matter needs status: filled and an 'options' "
    "list of >=2 candidate designs, each with id, name, project_type, "
    "identification, viability_condition (a checkable data diagnostic), unique "
    "integer priority, claim_boundary, and is_fallback_floor. >=1 option must be "
    "is_fallback_floor: true. Every causal/mechanism option's threats_addressed "
    "must cover all framing identification-threat cards. Add a '## Selection Rule' "
    "section describing the data-triggered choice."
)


def _ph(v: object) -> bool:
    return str(v or "").strip().lower() in PLACEHOLDERS


def _front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return (fm if isinstance(fm, dict) else {}), text[m.end():]


def _emit(as_json: bool, status: str, failures: list[str], n: int) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "options_checked": n,
                          "failures": failures, "hint": REMEDIATION_HINT if status == "fail" else ""},
                         ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: design options deck is valid ({n} option(s) checked)")
    else:
        print("FAIL: design options problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the design-options deck.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not OPTIONS.exists():
        return _emit(as_json, "fail", [f"missing {OPTIONS}"], 0)
    fm, body = _front_matter(OPTIONS.read_text(encoding="utf-8"))
    if str(fm.get("status", "")).strip().lower() != "filled":
        return _emit(as_json, "fail", ["design_options.md is not status: filled (not produced yet)"], 0)

    opts = fm.get("options")
    if not isinstance(opts, list) or len(opts) < 2:
        return _emit(as_json, "fail", ["need an 'options' list of >=2 candidate designs"], 0)

    # framing identification-threat cards that causal options must address
    threat_cards: set[str] = set()
    if DECK.exists():
        deck = yaml.safe_load(DECK.read_text(encoding="utf-8")) or {}
        for c in deck.get("cards", []) or []:
            if isinstance(c, dict) and str(c.get("role", "")).strip().lower() == "identification-threat" \
                    and str(c.get("decision", "proposed")).strip().lower() != "drop":
                threat_cards.add(str(c.get("id", "")).strip())

    failures: list[str] = []
    seen_ids: set[str] = set()
    priorities: list[int] = []
    floors = 0

    for i, o in enumerate(opts):
        if not isinstance(o, dict):
            failures.append(f"option #{i+1}: not a mapping")
            continue
        oid = str(o.get("id", "")).strip() or f"#{i+1}"
        if oid in seen_ids:
            failures.append(f"{oid}: duplicate option id")
        seen_ids.add(oid)

        for field in ("name", "identification", "viability_condition", "claim_boundary"):
            if _ph(o.get(field)):
                failures.append(f"{oid}: empty {field}")

        pt = str(o.get("project_type", "")).strip().lower()
        if pt not in PROJECT_TYPES:
            failures.append(f"{oid}: invalid project_type {pt!r}")

        pr = o.get("priority")
        if not isinstance(pr, int) or pr < 1:
            failures.append(f"{oid}: priority must be a positive integer, got {pr!r}")
        else:
            priorities.append(pr)

        is_floor = bool(o.get("is_fallback_floor", False))
        if is_floor:
            floors += 1

        if not is_floor and pt in CAUSAL_TYPES and threat_cards:
            addressed = {str(x).strip() for x in (o.get("threats_addressed", []) or [])}
            missing = threat_cards - addressed
            if missing:
                failures.append(
                    f"{oid}: causal/mechanism design must address framing threat cards; "
                    f"missing: {', '.join(sorted(missing))}")

        if f"## Option {oid}" not in body and f"## {oid}" not in body:
            failures.append(f"{oid}: no '## Option {oid}' section in the body")

    if floors < 1:
        failures.append("need at least one is_fallback_floor: true option (an always-viable design)")
    if len(set(priorities)) != len(priorities):
        failures.append("option priorities must be unique")
    if "## Selection Rule" not in body:
        failures.append("missing '## Selection Rule' section (the data-triggered choice)")

    return _emit(as_json, "fail" if failures else "pass", failures, len(opts))


if __name__ == "__main__":
    sys.exit(main())
