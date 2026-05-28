#!/usr/bin/env python3
"""Check that literature functions are valid and function matrix is consistent."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
FUNCTION_MATRIX = Path("discovery/literature/synthesis/function_matrix.csv")
ALLOWED_FUNCTIONS = {
    "idea-inspiring",
    "gap-verification",
    "method-identification",
    "data-measurement",
    "background-institutional",
    "theory-mechanism",
}
YES_NO = {"yes", "no"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    failures: list[str] = []
    if not REGISTRY.exists():
        print(f"FAIL: missing {REGISTRY}")
        return 1
    if not FUNCTION_MATRIX.exists():
        print(f"FAIL: missing {FUNCTION_MATRIX}")
        return 1

    registry = {row["paper_id"].strip(): row for row in read_csv(REGISTRY) if row.get("paper_id", "").strip()}
    matrix = {row["paper_id"].strip(): row for row in read_csv(FUNCTION_MATRIX) if row.get("paper_id", "").strip()}

    for paper_id, row in registry.items():
        primary = row.get("primary_function", "").strip()
        if primary not in ALLOWED_FUNCTIONS:
            failures.append(f"{paper_id}: invalid registry primary_function {primary!r}")
        if paper_id not in matrix:
            failures.append(f"{paper_id}: missing from function_matrix.csv")

    for paper_id, row in matrix.items():
        if paper_id not in registry:
            failures.append(f"{paper_id}: function matrix references unknown paper")
            continue
        primary = row.get("primary_function", "").strip()
        if primary != registry[paper_id].get("primary_function", "").strip():
            failures.append(f"{paper_id}: primary function mismatch between registry and function matrix")
        for column in ["extraction_card", "can_support_gap_claim", "can_support_method_claim", "can_support_data_claim"]:
            value = row.get(column, "").strip()
            if value and value not in YES_NO:
                failures.append(f"{paper_id}: {column} must be yes/no, got {value!r}")
        if row.get("can_support_gap_claim", "").strip() == "yes":
            if primary != "gap-verification":
                failures.append(f"{paper_id}: only gap-verification papers can support gap claims")
            if row.get("extraction_card", "").strip() != "yes":
                failures.append(f"{paper_id}: gap-supporting papers require extraction_card=yes")

    if failures:
        print("FAIL: literature function problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: literature function classifications are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
