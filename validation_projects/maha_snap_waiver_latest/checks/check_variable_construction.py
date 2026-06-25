#!/usr/bin/env python3
"""Validate G2 variable construction against the data inventory.

This check is intentionally strict enough to prevent a vacuous G2 pass:
`discovery/variable_construction.md` must exist, declare filled front matter,
define treatment and outcome variables, map every variable to a real data_id in
`discovery/data_inventory.csv`, and avoid marking every variable constructible.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml


CHECK_NAME = "check_variable_construction"
VARIABLES = Path("discovery/variable_construction.md")
INVENTORY = Path("discovery/data_inventory.csv")
ROLES = {"treatment", "outcome", "control", "instrument", "moderator", "unit-key", "running-variable"}
CONSTRUCTIBLE = {"yes", "no", "uncertain"}
PLACEHOLDERS = {"", "tbd", "todo", "to be determined", "n/a", "na", "none"}

REMEDIATION_HINT = (
    "Create discovery/variable_construction.md with YAML front matter status: filled "
    "and variables[]. Each variable needs name, role, definition, source_data_id, "
    "construction, validity_concern, and constructible yes/no/uncertain. Include at "
    "least one treatment and one outcome, and map source_data_id to data_inventory.csv."
)


def _front_matter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return {}, text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    return (data if isinstance(data, dict) else {}), text[match.end():]


def _inventory_ids() -> set[str]:
    if not INVENTORY.exists():
        return set()
    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        return {
            (row.get("data_id") or "").strip()
            for row in csv.DictReader(handle)
            if (row.get("data_id") or "").strip()
        }


def _is_placeholder(value: object) -> bool:
    return str(value or "").strip().lower() in PLACEHOLDERS


def _emit(as_json: bool, status: str, failures: list[str], n: int) -> int:
    if as_json:
        print(json.dumps({
            "check": CHECK_NAME,
            "status": status,
            "variables_checked": n,
            "failures": failures,
            "hint": REMEDIATION_HINT if status == "fail" else "",
        }, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: variable construction is valid ({n} variable(s) checked)")
    else:
        print("FAIL: variable construction problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    if not VARIABLES.exists():
        return _emit(as_json, "fail", [f"missing {VARIABLES}"], 0)
    if not INVENTORY.exists():
        return _emit(as_json, "fail", [f"missing {INVENTORY}"], 0)

    fm, body = _front_matter(VARIABLES.read_text(encoding="utf-8"))
    failures: list[str] = []
    if str(fm.get("status", "")).strip().lower() != "filled":
        failures.append("front matter status must be 'filled'")

    variables = fm.get("variables")
    if not isinstance(variables, list) or not variables:
        return _emit(as_json, "fail", failures + ["front matter variables must be a non-empty list"], 0)

    data_ids = _inventory_ids()
    roles_seen: set[str] = set()
    constructible_values: list[str] = []
    names_seen: set[str] = set()

    for idx, var in enumerate(variables, start=1):
        if not isinstance(var, dict):
            failures.append(f"variable #{idx}: must be a mapping")
            continue
        name = str(var.get("name", "")).strip()
        label = name or f"variable #{idx}"
        if _is_placeholder(name):
            failures.append(f"{label}: missing name")
        elif name in names_seen:
            failures.append(f"{label}: duplicate variable name")
        names_seen.add(name)

        role = str(var.get("role", "")).strip()
        roles_seen.add(role)
        if role not in ROLES:
            failures.append(f"{label}: invalid role {role!r}")

        for field in ("definition", "construction", "validity_concern"):
            if _is_placeholder(var.get(field)):
                failures.append(f"{label}: missing {field}")

        source_id = str(var.get("source_data_id", "")).strip()
        if source_id not in data_ids:
            failures.append(f"{label}: source_data_id {source_id!r} is not in {INVENTORY}")

        constructible = str(var.get("constructible", "")).strip().lower()
        constructible_values.append(constructible)
        if constructible not in CONSTRUCTIBLE:
            failures.append(f"{label}: constructible must be yes/no/uncertain, got {constructible!r}")

        if name and f"## {name}" not in body:
            failures.append(f"{label}: missing body section '## {name}'")

    if "treatment" not in roles_seen:
        failures.append("must define at least one treatment variable")
    if "outcome" not in roles_seen:
        failures.append("must define at least one outcome variable")
    if constructible_values and all(value == "yes" for value in constructible_values):
        failures.append("do not mark every variable constructible=yes; use uncertain/no where evidence is incomplete")

    return _emit(as_json, "fail" if failures else "pass", failures, len(variables))


if __name__ == "__main__":
    sys.exit(main())
