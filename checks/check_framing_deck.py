#!/usr/bin/env python3
"""Validate the literature framing deck.

The framing deck is the REASONING artifact produced before paper search: given
the research idea, the agent proposes candidate literature frameworks organized
by function bucket, each with a rationale and named seminal anchors. This check
enforces that:
  - the deck is structurally valid;
  - it proposes frameworks for the function buckets that keyword search cannot
    reach on its own (method-identification, theory-mechanism) plus the gap
    bucket -- the three that a topic-only search leaves empty;
  - every named anchor carries a verifiable locator (doi or openalex_id), so
    the reasoning step cannot fabricate citations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

DECK = Path("discovery/literature/framing_deck.yml")
CHECK_NAME = "check_framing_deck"

FUNCTIONS = {
    "idea-inspiring", "gap-verification", "method-identification",
    "data-measurement", "background-institutional", "theory-mechanism",
}
# Buckets a topic-keyword search cannot fill on its own -> the deck MUST cover them.
REQUIRED_BUCKETS = {"gap-verification", "method-identification", "theory-mechanism"}
# How a framework is USED in the design, not just that it is "related".
ROLES = {
    "motivation", "mechanism-tested", "identification-threat",
    "measurement-strategy", "robustness-comparison",
}
# A gap anchor must be empirical (a closest rival), not a review/perspective/theory.
NON_EMPIRICAL_KINDS = {"review", "perspective", "survey", "theory", "editorial", "commentary"}
GAP_MIN_EMPIRICAL_ANCHORS = 2
PLACEHOLDERS = {"", "tbd", "todo", "to be determined", "n/a", "na", "none"}

REMEDIATION_HINT = (
    "Fix framing_deck.yml: each card needs function (one of the 6), a non-empty "
    "framework, rationale, role (motivation|mechanism-tested|identification-threat|"
    "measurement-strategy|robustness-comparison), and caveat; plus >=1 anchor with "
    "a real doi or openalex_id (verify via OpenAlex; do not fabricate). The deck "
    "must cover gap-verification, method-identification, and theory-mechanism. "
    "gap-verification must name >=2 EMPIRICAL closest rivals (anchor kind=empirical, "
    "not review/perspective/theory)."
)


def _placeholder(v: object) -> bool:
    return str(v or "").strip().lower() in PLACEHOLDERS


def _emit(as_json: bool, status: str, failures: list[str], cards: int) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "cards_checked": cards, "failures": failures,
                          "hint": REMEDIATION_HINT if status == "fail" else ""},
                         ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: framing deck is valid ({cards} card(s) checked)")
    else:
        print("FAIL: framing deck problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the literature framing deck.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not DECK.exists():
        return _emit(as_json, "fail", [f"missing {DECK} (run the framing task first)"], 0)

    try:
        data = yaml.safe_load(DECK.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return _emit(as_json, "fail", [f"deck is not valid YAML: {exc}"], 0)

    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        return _emit(as_json, "fail", ["deck has no 'cards' list"], 0)

    failures: list[str] = []
    seen_ids: set[str] = set()
    covered: set[str] = set()
    gap_empirical_anchors = 0  # across non-dropped gap-verification cards

    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            failures.append(f"card #{i+1}: not a mapping")
            continue
        cid = str(card.get("id", "")).strip() or f"#{i+1}"
        if cid in seen_ids:
            failures.append(f"{cid}: duplicate card id")
        seen_ids.add(cid)

        fn = str(card.get("function", "")).strip()
        if fn not in FUNCTIONS:
            failures.append(f"{cid}: invalid function {fn!r}")
        if _placeholder(card.get("framework")):
            failures.append(f"{cid}: empty framework")
        if _placeholder(card.get("rationale")):
            failures.append(f"{cid}: empty rationale")

        role = str(card.get("role", "")).strip().lower()
        if role not in ROLES:
            failures.append(f"{cid}: role must be one of {sorted(ROLES)}, got {role!r}")
        if _placeholder(card.get("caveat")):
            failures.append(f"{cid}: empty caveat (state the threat/limit this framework raises)")

        decision = str(card.get("decision", "proposed")).strip().lower()
        if decision not in {"proposed", "keep", "drop"}:
            failures.append(f"{cid}: invalid decision {decision!r}")

        is_gap = fn == "gap-verification" and decision != "drop"
        anchors = card.get("anchors")
        if not isinstance(anchors, list) or not anchors:
            failures.append(f"{cid}: needs >=1 anchor")
        else:
            for j, a in enumerate(anchors):
                if not isinstance(a, dict):
                    failures.append(f"{cid} anchor#{j+1}: not a mapping")
                    continue
                if _placeholder(a.get("title")):
                    failures.append(f"{cid} anchor#{j+1}: empty title")
                if _placeholder(a.get("doi")) and _placeholder(a.get("openalex_id")):
                    failures.append(
                        f"{cid} anchor#{j+1}: needs a real doi or openalex_id (verify, do not fabricate)")
                if is_gap:
                    kind = str(a.get("kind", "")).strip().lower()
                    if kind in NON_EMPIRICAL_KINDS:
                        failures.append(
                            f"{cid} anchor#{j+1}: gap-verification anchors must be empirical "
                            f"closest rivals, not {kind!r}")
                    elif kind == "empirical":
                        gap_empirical_anchors += 1
                    else:
                        failures.append(
                            f"{cid} anchor#{j+1}: gap anchor must declare kind=empirical "
                            f"(got {kind or 'none'})")

        if fn in FUNCTIONS and decision != "drop":
            covered.add(fn)

    missing = REQUIRED_BUCKETS - covered
    if missing:
        failures.append(
            f"deck must propose at least one non-dropped card for each of: "
            f"{', '.join(sorted(missing))}")
    if "gap-verification" in covered and gap_empirical_anchors < GAP_MIN_EMPIRICAL_ANCHORS:
        failures.append(
            f"gap-verification must name >={GAP_MIN_EMPIRICAL_ANCHORS} empirical closest "
            f"rivals (found {gap_empirical_anchors}); a review/perspective is not a closest rival")

    status = "fail" if failures else "pass"
    return _emit(as_json, status, failures, len(cards))


if __name__ == "__main__":
    sys.exit(main())
