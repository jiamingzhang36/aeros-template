#!/usr/bin/env python3
"""Validate claim-upgrade automation remains recommendation-only."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
POLICY = Path("harness/claim_upgrade_policy.yml")
CLAIM_REGISTRY = Path("evidence/claim_registry.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main() -> int:
    failures: list[str] = []
    if not POLICY.exists():
        failures.append(f"missing {POLICY}")
    policy_text = _read(POLICY)
    for phrase in ["recommendation_only", "must not mutate claim_registry", "human gate"]:
        if phrase not in policy_text:
            failures.append(f"{POLICY}: missing boundary phrase {phrase!r}")
    before = _read(CLAIM_REGISTRY)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "aeros.cli",
            "claim-upgrade",
            "review",
            "--claim-id",
            "C_TEST",
            "--evidence-status",
            "admitted_support",
            "--identification-level",
            "associational",
            "--result-admission-status",
            "human_admitted",
            "--validation-status",
            "validated",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        failures.append(f"claim-upgrade review failed: {proc.stderr or proc.stdout}")
    else:
        payload = json.loads(proc.stdout)
        if payload.get("authority_status") != "recommendation_only":
            failures.append("claim-upgrade review is not recommendation_only")
        if payload.get("required_human_gate") is not True:
            failures.append("claim-upgrade review does not require human gate")
        if payload.get("recommendation") != "eligible_for_human_upgrade_review":
            failures.append(f"unexpected recommendation: {payload.get('recommendation')}")
    after = _read(CLAIM_REGISTRY)
    if before != after:
        failures.append("claim-upgrade review modified claim_registry.md")

    if failures:
        print("FAIL: claim-upgrade recommendation problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: claim-upgrade recommendation is human-gated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
