#!/usr/bin/env python3
"""Check expanded-result registration and claim-boundary discipline."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


RESULT_INDEX = Path("evidence/result_index.csv")
CLAIMS = Path("evidence/claim_registry.md")
REPORT = Path("audits/expanded_result_validation_report.md")
REQUIRED_RESULT_IDS = {"R004", "R005"}


def main() -> int:
    if not REPORT.exists():
        print("SKIP: expanded result validation report not present yet")
        return 0

    failures: list[str] = []
    result_ids: set[str] = set()
    if not RESULT_INDEX.exists():
        failures.append(f"missing {RESULT_INDEX}")
    else:
        with RESULT_INDEX.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                result_id = row.get("result_id", "").strip()
                if result_id:
                    result_ids.add(result_id)
                    path_value = row.get("path", "").strip()
                    source = row.get("script_or_source", "").strip()
                    if result_id in REQUIRED_RESULT_IDS:
                        if not path_value or not Path(path_value).exists():
                            failures.append(f"{result_id}: registered output path missing or absent")
                        if not source:
                            failures.append(f"{result_id}: script_or_source is empty")

    missing_results = REQUIRED_RESULT_IDS - result_ids
    if missing_results:
        failures.append(f"missing expanded result IDs: {', '.join(sorted(missing_results))}")

    claims = CLAIMS.read_text(encoding="utf-8") if CLAIMS.exists() else ""
    if "C002" not in claims:
        failures.append(f"{CLAIMS}: C002 not found")
    if "supported" in claims.lower() and "R004" in claims:
        failures.append(
            f"{CLAIMS}: do not mark expanded collection claims supported without explicit human approval"
        )

    report = REPORT.read_text(encoding="utf-8")
    if "claim ceiling" not in report.lower() or "human approval" not in report.lower():
        failures.append(f"{REPORT}: must state claim ceiling and human approval requirement")

    if failures:
        print("FAIL: expanded result validation problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: expanded results are registered with bounded claim discipline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
