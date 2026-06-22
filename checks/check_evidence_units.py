#!/usr/bin/env python3
"""Validate EvidenceUnit records if present."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


ROOT = Path("evidence/evidence_units")
ALLOWED_FUNCTIONS = {
    "gap_verification",
    "method_identification",
    "mechanism",
    "data_measurement",
    "institutional_background",
    "idea_inspiring",
}
REQUIRED = [
    "evidence_unit_id",
    "paper_id",
    "source_artifact_sha256",
    "locator",
    "literature_function",
    "extracted_proposition",
    "limitation",
    "verifier_status",
]


def main() -> int:
    if not ROOT.exists():
        print("PASS: evidence units inactive (no evidence/evidence_units directory)")
        return 0
    failures: list[str] = []
    files = sorted(ROOT.glob("*.yml")) + sorted(ROOT.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            failures.append(f"{path}: must be a mapping")
            continue
        for key in REQUIRED:
            if key not in data:
                failures.append(f"{path}: missing {key}")
        locator = data.get("locator") or {}
        if not isinstance(locator, dict) or not any(locator.get(k) for k in ["page", "section", "span"]):
            failures.append(f"{path}: locator must include page, section, or span")
        if data.get("literature_function") not in ALLOWED_FUNCTIONS:
            failures.append(f"{path}: invalid literature_function {data.get('literature_function')!r}")
        if data.get("verifier_status") not in {"unverified", "sampled", "verified"}:
            failures.append(f"{path}: verifier_status must be unverified/sampled/verified")
    if failures:
        print("FAIL: EvidenceUnit problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: evidence units valid ({len(files)} record(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
