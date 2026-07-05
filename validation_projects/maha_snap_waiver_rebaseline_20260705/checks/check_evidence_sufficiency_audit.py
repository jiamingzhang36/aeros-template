#!/usr/bin/env python3
"""Validate evidence/governance sufficiency audit policy and records."""

from __future__ import annotations

from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("FAIL: PyYAML is required for check_evidence_sufficiency_audit.py") from exc


ROOT = Path.cwd()
POLICY = ROOT / "harness/evidence_sufficiency_audit_policy.yml"
TEMPLATE = ROOT / "templates/evidence_sufficiency_audit.yml"
ACTIVE = ROOT / "audits/evidence_sufficiency_audit.yml"
REQUIRED_DIMENSIONS = {
    "actor",
    "authority",
    "action",
    "policy",
    "decision_basis",
    "resource_access",
    "lifecycle",
    "verification_strength",
}


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def validate_record(path: Path, data: dict, allowed_strength: set[str]) -> list[str]:
    failures: list[str] = []
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, dict):
        return [f"{path}: missing dimensions mapping"]
    missing = REQUIRED_DIMENSIONS - set(dimensions)
    if missing:
        failures.append(f"{path}: missing dimension(s): {', '.join(sorted(missing))}")
    for dimension in REQUIRED_DIMENSIONS:
        item = dimensions.get(dimension) or {}
        if not isinstance(item, dict):
            failures.append(f"{path}: dimension {dimension} must be a mapping")
            continue
        if "value" not in item:
            failures.append(f"{path}: dimension {dimension} missing value")
        if "note" not in item:
            failures.append(f"{path}: dimension {dimension} missing note")
    strength = ((dimensions.get("verification_strength") or {}).get("value") or "").strip()
    if strength and strength not in allowed_strength:
        failures.append(f"{path}: invalid verification_strength {strength!r}")
    for key in ["audit_id", "artifact_id", "artifact_path", "artifact_type", "overall_assessment", "does_not_prove"]:
        if key not in data:
            failures.append(f"{path}: missing {key}")
    if "claim support" not in (data.get("does_not_prove") or []):
        failures.append(f"{path}: does_not_prove missing claim-support boundary")
    return failures


def main() -> int:
    failures: list[str] = []
    if not POLICY.exists():
        print("FAIL: missing harness/evidence_sufficiency_audit_policy.yml")
        return 1
    if not TEMPLATE.exists():
        print("FAIL: missing templates/evidence_sufficiency_audit.yml")
        return 1
    try:
        policy = load(POLICY)
        template = load(TEMPLATE)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    dimensions = set(policy.get("required_dimensions") or [])
    if dimensions != REQUIRED_DIMENSIONS:
        failures.append(f"{POLICY}: required_dimensions must equal the 8 governance dimensions")
    allowed_strength = {str(item) for item in (policy.get("allowed_verification_strength") or [])}
    if not allowed_strength:
        failures.append(f"{POLICY}: missing allowed_verification_strength")
    for minimum_key in ["minimum_for_gate_packet", "minimum_for_completion_claim"]:
        values = set(policy.get(minimum_key) or [])
        if not values or not values <= REQUIRED_DIMENSIONS:
            failures.append(f"{POLICY}: invalid {minimum_key}")
    if "scientific validity" not in (policy.get("does_not_prove") or []):
        failures.append(f"{POLICY}: does_not_prove missing scientific-validity boundary")
    failures.extend(validate_record(TEMPLATE, template, allowed_strength))
    if ACTIVE.exists():
        try:
            failures.extend(validate_record(ACTIVE, load(ACTIVE), allowed_strength))
        except ValueError as exc:
            failures.append(str(exc))
    if failures:
        print("FAIL: evidence sufficiency audit check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    scope = "template + active audit" if ACTIVE.exists() else "template only"
    print(f"PASS: evidence sufficiency audit policy is valid ({scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

