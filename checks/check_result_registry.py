#!/usr/bin/env python3
"""Validate Phase 0 result registry records.

This check is intentionally mechanical. It verifies that registered result
numbers have estimation-call provenance and extracted spec fields. It does not
decide whether the estimate is correct or whether a claim is valid.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.paper_ci.result_registry import (  # noqa: E402
    REGISTRY_FIELDS,
    RESULT_REGISTRY,
    record_from_row,
    read_registry,
)


def main() -> int:
    root = Path.cwd()
    path = root / RESULT_REGISTRY
    if not path.exists():
        print("PASS: result registry inactive (no evidence/result_registry.csv yet)")
        return 0

    rows = read_registry(root)
    failures: list[str] = []
    seen: set[str] = set()

    if rows:
        missing_header = sorted(set(REGISTRY_FIELDS) - set(rows[0].keys()))
        if missing_header:
            failures.append(f"result_registry.csv missing column(s): {missing_header}")

    for row in rows:
        result_id = row.get("result_id", "").strip()
        if not result_id:
            failures.append("row missing result_id")
            continue
        if result_id in seen:
            failures.append(f"{result_id}: duplicate result_id")
        seen.add(result_id)

        for json_field in [
            "values_json",
            "fixed_effects_json",
            "cluster_json",
            "sample_filters_json",
            "code_ref_json",
        ]:
            try:
                json.loads(row.get(json_field) or "{}")
            except json.JSONDecodeError as exc:
                failures.append(f"{result_id}: invalid {json_field}: {exc}")

        try:
            record = record_from_row(row)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            failures.append(f"{result_id}: cannot parse registry row: {exc}")
            continue
        failures.extend(record.validate(root))

    if failures:
        print("FAIL: result registry problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"PASS: result registry valid ({len(rows)} result(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
