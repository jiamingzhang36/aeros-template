#!/usr/bin/env python3
"""Check that the data contract contains the minimum harness sections."""

from __future__ import annotations

import sys
from pathlib import Path


DATA_CONTRACT = Path("docs/data_contract.yml")
REQUIRED_TOKENS = [
    "data_contract:",
    "raw_data:",
    "derived_data:",
    "units:",
    "required_variables:",
    "provenance:",
    "privacy:",
    "directory: \"data/raw\"",
    "intermediate_directory: \"data/intermediate\"",
    "clean_directory: \"data/clean\"",
]


def main() -> int:
    if not DATA_CONTRACT.exists():
        print(f"FAIL: missing {DATA_CONTRACT}")
        return 1

    text = DATA_CONTRACT.read_text(encoding="utf-8")
    missing = [token for token in REQUIRED_TOKENS if token not in text]
    if missing:
        print("FAIL: data contract is missing required entries:")
        print("\n".join(missing))
        return 1

    print("PASS: data contract contains required harness sections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
