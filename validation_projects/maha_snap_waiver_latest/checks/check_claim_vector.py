#!/usr/bin/env python3
"""Validate ClaimVector advisory compiler boundaries."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.claim_vector import compile_claim_vector  # noqa: E402


POLICY = Path("harness/claim_vector_policy.yml")
TEMPLATE = Path("templates/claim_vector.yml")
CLAIM_REGISTRY = Path("evidence/claim_registry.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main() -> int:
    failures: list[str] = []
    for path in [POLICY, TEMPLATE]:
        if not path.exists():
            failures.append(f"missing {path}")
    policy_text = _read(POLICY)
    for phrase in ["advisory_only", "no automatic claim upgrade", "human gate"]:
        if phrase not in policy_text:
            failures.append(f"{POLICY}: missing boundary phrase {phrase!r}")

    candidate = compile_claim_vector(
        claim_id="C_TEST",
        evidence_status="candidate_support",
        identification_level="associational",
        result_admission_status="needs_review",
        validation_status="validated",
    )
    if candidate.claim_ceiling != "candidate_only":
        failures.append(f"unadmitted evidence should compile to candidate_only, got {candidate.claim_ceiling}")
    if "causes" not in candidate.forbidden_language:
        failures.append("candidate vector must forbid causal language")
    if candidate.authority_status != "advisory_only" or not candidate.required_human_gate:
        failures.append("ClaimVector must remain advisory and human-gated")

    admitted = compile_claim_vector(
        claim_id="C_TEST",
        evidence_status="admitted_support",
        identification_level="associational",
        result_admission_status="human_admitted",
        validation_status="validated",
    )
    if admitted.claim_ceiling != "associational":
        failures.append(f"associational admitted evidence compiled to {admitted.claim_ceiling}")
    if not any("associated" in item for item in admitted.allowed_language):
        failures.append("associational vector missing associated-with allowed language")
    if "causes" not in admitted.forbidden_language:
        failures.append("associational vector must forbid causes")

    before = _read(CLAIM_REGISTRY)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "aeros.cli",
            "claim-vector",
            "compile",
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
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        failures.append(f"claim-vector CLI failed: {proc.stderr or proc.stdout}")
    else:
        payload = json.loads(proc.stdout)
        if payload.get("authority_status") != "advisory_only":
            failures.append("claim-vector CLI did not emit advisory_only")
        if payload.get("claim_ceiling") != "associational":
            failures.append(f"claim-vector CLI emitted wrong ceiling: {payload.get('claim_ceiling')}")
    after = _read(CLAIM_REGISTRY)
    if before != after:
        failures.append("claim-vector CLI modified claim_registry.md")

    if failures:
        print("FAIL: ClaimVector problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: ClaimVector advisory compiler is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
