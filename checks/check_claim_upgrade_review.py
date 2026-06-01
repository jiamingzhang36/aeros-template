#!/usr/bin/env python3
"""Check that a claim-upgrade review is present and does not self-approve."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPORT = Path("audits/claim_upgrade_review_report.md")
CLAIMS = Path("evidence/claim_registry.md")
RESULT_INDEX = Path("evidence/result_index.csv")


def main() -> int:
    if not REPORT.exists():
        print("SKIP: claim upgrade review report not present yet")
        return 0

    failures: list[str] = []
    report = REPORT.read_text(encoding="utf-8")
    claims = CLAIMS.read_text(encoding="utf-8") if CLAIMS.exists() else ""
    result_index = RESULT_INDEX.read_text(encoding="utf-8") if RESULT_INDEX.exists() else ""

    for required in ["C002", "R004", "R005", "human approval", "claim ceiling"]:
        if required.lower() not in report.lower():
            failures.append(f"{REPORT}: missing required review term {required!r}")

    if not re.search(r"\brecommendation\b|\brecommended action\b|\bdecision option\b", report, re.I):
        failures.append(f"{REPORT}: must include a recommendation or decision option")

    if "supported" in claims.lower() and "C002" in claims:
        c002_lines = [line for line in claims.splitlines() if line.strip().startswith("| C002 ")]
        if c002_lines and "| supported |" in c002_lines[0].lower():
            failures.append(f"{CLAIMS}: C002 must not be marked supported before human approval")

    if "R004" not in result_index or "R005" not in result_index:
        failures.append(f"{RESULT_INDEX}: R004/R005 must be registered before claim upgrade review")

    forbidden = [
        "upgrade approved",
        "claim is approved",
        "final conclusion",
        "ready for submission",
    ]
    for phrase in forbidden:
        if phrase in report.lower():
            failures.append(f"{REPORT}: forbidden self-approval phrase {phrase!r}")

    if failures:
        print("FAIL: claim upgrade review problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: claim upgrade review is present and requires human approval")
    return 0


if __name__ == "__main__":
    sys.exit(main())
