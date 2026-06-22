#!/usr/bin/env python3
"""Validate adversarial benchmark scaffold."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


PATH = Path("harness/adversarial_benchmark.yml")
REQUIRED = {
    "false_fulltext",
    "exit_zero_no_output",
    "stale_registry",
    "claim_ceiling_escape",
    "stale_human_approval",
    "session_scope_drift",
    "wrong_python_runtime",
    "undeclared_credential",
}


def main() -> int:
    if not PATH.exists():
        print(f"FAIL: missing {PATH}")
        return 1
    data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
    scenarios = {
        str(item.get("id"))
        for item in data.get("scenarios", [])
        if isinstance(item, dict) and item.get("id")
    }
    missing = REQUIRED - scenarios
    if missing:
        print("FAIL: adversarial benchmark missing scenarios:")
        for item in sorted(missing):
            print(f"- {item}")
        return 1
    print("PASS: adversarial benchmark scaffold is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
