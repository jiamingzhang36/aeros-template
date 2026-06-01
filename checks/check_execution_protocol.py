#!/usr/bin/env python3
"""Validate that the main execution protocol is filled before G4 execution."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

CHECK_NAME = "check_execution_protocol"
PROTOCOL = Path("execution/protocol/main_execution_protocol.md")
REQUIRED_SECTIONS = [
    "Observation Unit",
    "Collection or Construction Grid",
    "Inputs",
    "Outputs to Register",
    "Exclusion Rules",
    "Provenance Requirements",
    "Claim Boundary",
    "Human Approval Status",
]
PLACEHOLDERS = {"", "tbd", "todo", "unknown", "n/a", "na", "none"}


def _front_matter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return {}, text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    return data if isinstance(data, dict) else {}, text[match.end():]


def _section_text(body: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, body, flags=re.S | re.M)
    return match.group("body").strip() if match else ""


def _placeholder(text: str) -> bool:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", text or "").strip().lower()
    return cleaned in PLACEHOLDERS


def _emit(as_json: bool, status: str, failures: list[str]) -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif status == "pass":
        print("PASS: execution protocol is filled")
    else:
        print("FAIL: execution protocol problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not PROTOCOL.exists():
        return _emit(as_json, "fail", [f"missing {PROTOCOL}"])
    fm, body = _front_matter(PROTOCOL.read_text(encoding="utf-8"))
    failures: list[str] = []
    if str(fm.get("status", "")).strip().lower() != "filled":
        failures.append("front matter status must be filled")
    if _placeholder(str(fm.get("claim_ceiling", ""))):
        failures.append("front matter claim_ceiling must be non-placeholder")
    result_ids = fm.get("result_ids")
    if not isinstance(result_ids, list) or not result_ids:
        failures.append("front matter result_ids must be a non-empty list")

    for section in REQUIRED_SECTIONS:
        text = _section_text(body, section)
        if not text:
            failures.append(f"missing section ## {section}")
        elif _placeholder(text):
            failures.append(f"section ## {section} is placeholder-like")

    return _emit(as_json, "fail" if failures else "pass", failures)


if __name__ == "__main__":
    sys.exit(main())
