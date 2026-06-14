#!/usr/bin/env python3
"""Validate AEROS improvement backlog entries."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

BACKLOG = Path("harness/improvement_backlog.yml")
CHECK_NAME = "check_improvement_backlog"
REQUIRED = (
    "id",
    "created_at",
    "updated_at",
    "status",
    "priority",
    "area",
    "source",
    "issue",
    "proposed_fix",
    "owner",
)
STATUSES = {"open", "in_progress", "blocked", "resolved", "wont_do"}
PRIORITIES = {"low", "medium", "high", "critical"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _emit(as_json: bool, status: str, failures: list[str], n: int) -> int:
    if as_json:
        print(json.dumps({
            "check": CHECK_NAME,
            "status": status,
            "entries": n,
            "failures": failures,
        }, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: improvement backlog is well-formed ({n} entry/entries)")
    else:
        print("FAIL: improvement backlog problems detected:")
        print("\n".join(failures))
    return 0 if status == "pass" else 1


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate harness/improvement_backlog.yml.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not BACKLOG.exists():
        return _emit(args.json, "fail", [f"missing {BACKLOG}"], 0)
    try:
        data = yaml.safe_load(BACKLOG.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return _emit(args.json, "fail", [f"backlog is not valid YAML: {exc}"], 0)

    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return _emit(args.json, "fail", ["'entries' must be a list"], 0)

    failures: list[str] = []
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append(f"entry #{i + 1}: not a mapping")
            continue
        item_id = str(entry.get("id", "")).strip() or f"#{i + 1}"
        if item_id in seen:
            failures.append(f"{item_id}: duplicate id")
        seen.add(item_id)

        for field in REQUIRED:
            if _blank(entry.get(field)):
                failures.append(f"{item_id}: missing/empty {field}")

        status = str(entry.get("status", "")).strip()
        priority = str(entry.get("priority", "")).strip()
        if status not in STATUSES:
            failures.append(f"{item_id}: status must be one of {sorted(STATUSES)}")
        if priority not in PRIORITIES:
            failures.append(f"{item_id}: priority must be one of {sorted(PRIORITIES)}")
        for field in ("created_at", "updated_at", "resolved_at"):
            value = str(entry.get(field, "") or "").strip()
            if value and not DATE_RE.match(value):
                failures.append(f"{item_id}: {field} must be YYYY-MM-DD")
        if status == "resolved":
            if _blank(entry.get("resolved_at")):
                failures.append(f"{item_id}: resolved entries must set resolved_at")
            if _blank(entry.get("resolution_commit")):
                failures.append(f"{item_id}: resolved entries must set resolution_commit")

    return _emit(args.json, "fail" if failures else "pass", failures, len(entries))


if __name__ == "__main__":
    sys.exit(main())
