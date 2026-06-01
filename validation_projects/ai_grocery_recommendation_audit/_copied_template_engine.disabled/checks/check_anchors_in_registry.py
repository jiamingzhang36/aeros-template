#!/usr/bin/env python3
"""Recall floor: every non-dropped framing-deck anchor must reach the registry.

This is the check that makes "passing != thorough" bite for the search step.
The framing deck (human-reasoned, human-gated) commits to seminal anchors per
framework; D001b must actually register them. An anchor counts as covered if
its DOI matches a registry row, or its normalized title matches a registry
title. If the deck is absent, there is nothing to enforce (PASS).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

DECK = Path("discovery/literature/framing_deck.yml")
REGISTRY = Path("discovery/literature/paper_registry.csv")
CHECK_NAME = "check_anchors_in_registry"

REMEDIATION_HINT = (
    "Register every non-dropped framing-deck anchor in paper_registry.csv "
    "(carry its DOI and exact title). The deck's seminal anchors are the recall "
    "floor for the framework search; they must appear in the registry."
)


def _norm_title(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())[:50]


def _norm_doi(s: str) -> str:
    return str(s or "").strip().lower().replace("https://doi.org/", "").strip()


def _emit(as_json: bool, status: str, failures: list[str], checked: int) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "anchors_checked": checked, "failures": failures,
                          "hint": REMEDIATION_HINT if status == "fail" else ""},
                         ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: all deck anchors are registered ({checked} anchor(s) checked)")
    else:
        print("FAIL: framing-deck anchors missing from registry:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check deck anchors reach the registry.")
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not DECK.exists():
        return _emit(as_json, "pass", [], 0)  # nothing to enforce yet
    if not REGISTRY.exists():
        return _emit(as_json, "fail", [f"missing {REGISTRY}"], 0)

    deck = yaml.safe_load(DECK.read_text(encoding="utf-8")) or {}
    reg_titles: set[str] = set()
    reg_dois: set[str] = set()
    with REGISTRY.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("title", "").strip():
                reg_titles.add(_norm_title(row["title"]))
            if row.get("doi", "").strip():
                reg_dois.add(_norm_doi(row["doi"]))

    failures: list[str] = []
    checked = 0
    for card in deck.get("cards", []) or []:
        if not isinstance(card, dict):
            continue
        if str(card.get("decision", "proposed")).strip().lower() == "drop":
            continue
        cid = card.get("id", "?")
        for a in card.get("anchors", []) or []:
            if not isinstance(a, dict):
                continue
            checked += 1
            title = _norm_title(a.get("title", ""))
            doi = _norm_doi(a.get("doi", ""))
            covered = (title and title in reg_titles) or (doi and doi in reg_dois)
            if not covered:
                failures.append(
                    f"{cid}: anchor {a.get('author','?')} ({a.get('year','?')}) "
                    f"'{str(a.get('title',''))[:50]}' not in registry")

    status = "fail" if failures else "pass"
    return _emit(as_json, status, failures, checked)


if __name__ == "__main__":
    sys.exit(main())
