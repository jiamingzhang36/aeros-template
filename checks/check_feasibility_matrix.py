#!/usr/bin/env python3
"""Check that the feasibility matrix includes required dimensions and decision labels."""

from __future__ import annotations

import re
import sys
from pathlib import Path


MATRIX = Path("discovery/feasibility_matrix.md")
REQUIRED_DIMENSIONS = [
    "Importance",
    "Literature gap",
    "Data availability",
    "Measurement quality",
    "Identification",
    "Execution cost",
]
ALLOWED_DECISIONS = {"pursue", "revise", "pause", "drop", "TBD"}


def main() -> int:
    if not MATRIX.exists():
        print(f"FAIL: missing {MATRIX}")
        return 1

    text = MATRIX.read_text(encoding="utf-8")
    failures: list[str] = []

    for dimension in REQUIRED_DIMENSIONS:
        if dimension not in text:
            failures.append(f"missing dimension: {dimension}")

    match = re.search(r"Decision:\s*([A-Za-z_ -]+)", text)
    if not match:
        failures.append("missing Decision line")
    else:
        decision = match.group(1).strip()
        if decision not in ALLOWED_DECISIONS:
            failures.append(f"decision must be one of {sorted(ALLOWED_DECISIONS)}, got {decision!r}")

    if failures:
        print("FAIL: feasibility matrix problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: feasibility matrix contains required dimensions and decision label")
    return 0


if __name__ == "__main__":
    sys.exit(main())
