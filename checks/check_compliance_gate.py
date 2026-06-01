#!/usr/bin/env python3
"""Check that compliance/release review artifacts exist and require human approval."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_FILES = [
    Path("compliance/provider_terms_review.md"),
    Path("compliance/data_license_review.md"),
    Path("compliance/irb_ethics_review.md"),
    Path("compliance/public_release_decision.md"),
    Path("audits/compliance_gate_report.md"),
]

ALLOWED_RELEASE_STATUS = {"blocked", "internal-only", "approved-for-release"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _extract_release_status(text: str) -> str:
    match = re.search(r"^release_status:\s*([A-Za-z0-9_-]+)\s*$", text, flags=re.I | re.M)
    return match.group(1).strip().lower() if match else ""


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing {path}")
            continue
        text = _read(path)
        if _nonempty_lines(text) < 8:
            failures.append(f"{path}: too short for compliance review")

    provider = _read(Path("compliance/provider_terms_review.md")).lower()
    data = _read(Path("compliance/data_license_review.md")).lower()
    ethics = _read(Path("compliance/irb_ethics_review.md")).lower()
    release = _read(Path("compliance/public_release_decision.md"))
    report = _read(Path("audits/compliance_gate_report.md")).lower()

    if provider and not all(term in provider for term in ["provider", "terms", "output"]):
        failures.append("provider_terms_review.md must discuss provider terms and output-use risk")
    if data and not all(term in data for term in ["data", "license", "source"]):
        failures.append("data_license_review.md must discuss data sources and license/access status")
    if ethics and not any(term in ethics for term in ["human subjects", "irb", "personal data"]):
        failures.append("irb_ethics_review.md must discuss human-subjects/IRB/personal-data status")

    status = _extract_release_status(release)
    if not status:
        failures.append("public_release_decision.md must declare release_status: blocked|internal-only|approved-for-release")
    elif status not in ALLOWED_RELEASE_STATUS:
        failures.append(f"public_release_decision.md invalid release_status: {status}")

    if status == "approved-for-release":
        if "human approval" not in release.lower() or "approver" not in release.lower():
            failures.append("approved-for-release requires explicit human approval and approver")

    if report and "human approval" not in report:
        failures.append("compliance_gate_report.md must state human approval requirement")
    if report and "automatic approval" in report:
        failures.append("compliance_gate_report.md must not imply automatic approval")

    if failures:
        print("FAIL: compliance gate problems detected:")
        print("\n".join(failures))
        return 1

    print(f"PASS: compliance gate artifacts present (release_status: {status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
