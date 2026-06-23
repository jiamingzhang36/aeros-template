#!/usr/bin/env python3
"""Validate EvidenceUnit and ResultAdmission records.

EvidenceUnit records are machine facts: extracted, located, hash-bound units of
evidence. ResultAdmission records are human/governance judgments about whether
machine facts may be admitted for a result or claim context. Keeping them
separate prevents parser/OCR success from laundering itself into claim support.
"""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


PROJECT_EVIDENCE_ROOT = Path("evidence/evidence_units")
PROJECT_ADMISSION_ROOT = Path("evidence/result_admissions")
FIXTURE_ROOT = Path("tests/evidence_units")
POLICY = Path("harness/evidence_unit_policy.yml")
ALLOWED_FUNCTIONS = {
    "gap_verification",
    "method_identification",
    "mechanism",
    "data_measurement",
    "institutional_background",
    "idea_inspiring",
}
ALLOWED_UNIT_TYPES = {"literature_extract", "result_artifact", "data_snapshot", "code_output", "manual_note"}
ALLOWED_MACHINE_STATUS = {"parsed", "hash_verified", "locator_verified", "failed", "unverified"}
ALLOWED_ADMISSION_STATUS = {"not_admitted", "needs_review", "human_admitted", "rejected"}
REQUIRED_EVIDENCE_UNIT = [
    "evidence_unit_id",
    "unit_type",
    "source_artifact_sha256",
    "locator",
    "evidence_function",
    "extracted_assertion",
    "limits",
    "machine_status",
    "admission_status",
]
REQUIRED_RESULT_ADMISSION = [
    "result_admission_id",
    "result_id",
    "admitted_evidence_units",
    "admission_status",
    "authority",
    "claim_effect",
    "limitations",
    "does_not_prove",
]


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _validate_policy() -> list[str]:
    if not POLICY.exists():
        return [f"missing {POLICY}"]
    data = _load_yaml(POLICY)
    failures: list[str] = []
    for phrase in ["machine facts", "human admission", "no automatic claim upgrade"]:
        if phrase not in POLICY.read_text(encoding="utf-8"):
            failures.append(f"{POLICY}: missing boundary phrase {phrase!r}")
    if set(data.get("progression") or []) != {"evidence_unit", "result_admission", "claim_registry_update"}:
        failures.append(f"{POLICY}: progression must separate evidence_unit/result_admission/claim_registry_update")
    return failures


def _validate_evidence_unit(path: Path, data: dict) -> list[str]:
    failures: list[str] = []
    for key in REQUIRED_EVIDENCE_UNIT:
        if key not in data:
            failures.append(f"{path}: missing {key}")
    locator = data.get("locator") or {}
    if not isinstance(locator, dict) or not any(locator.get(k) for k in ["page", "section", "span", "row", "cell"]):
        failures.append(f"{path}: locator must include page, section, span, row, or cell")
    if data.get("unit_type") not in ALLOWED_UNIT_TYPES:
        failures.append(f"{path}: invalid unit_type {data.get('unit_type')!r}")
    if data.get("evidence_function") not in ALLOWED_FUNCTIONS:
        failures.append(f"{path}: invalid evidence_function {data.get('evidence_function')!r}")
    if data.get("machine_status") not in ALLOWED_MACHINE_STATUS:
        failures.append(f"{path}: invalid machine_status {data.get('machine_status')!r}")
    if data.get("admission_status") not in {"not_admitted", "needs_review"}:
        failures.append(f"{path}: EvidenceUnit cannot self-admit evidence; use ResultAdmission")
    if "supported" in str(data.get("claim_effect", "")).lower():
        failures.append(f"{path}: EvidenceUnit cannot declare supported claim effect")
    if data.get("human_approved") is True:
        failures.append(f"{path}: EvidenceUnit cannot carry human_approved=true; use ResultAdmission")
    return failures


def _validate_result_admission(path: Path, data: dict, known_units: set[str]) -> list[str]:
    failures: list[str] = []
    for key in REQUIRED_RESULT_ADMISSION:
        if key not in data:
            failures.append(f"{path}: missing {key}")
    status = data.get("admission_status")
    if status not in ALLOWED_ADMISSION_STATUS:
        failures.append(f"{path}: invalid admission_status {status!r}")
    units = data.get("admitted_evidence_units") or []
    if not isinstance(units, list) or not units:
        failures.append(f"{path}: admitted_evidence_units must be a non-empty list")
    for unit_id in units if isinstance(units, list) else []:
        if str(unit_id) not in known_units:
            failures.append(f"{path}: unknown EvidenceUnit {unit_id!r}")
    if status == "human_admitted":
        for key in ["approved_by", "approved_at", "decision_ref"]:
            if not str(data.get(key, "")).strip():
                failures.append(f"{path}: human_admitted admission missing {key}")
    if status != "human_admitted" and any(str(data.get(k, "")).strip() for k in ["approved_by", "approved_at", "decision_ref"]):
        failures.append(f"{path}: non-admitted ResultAdmission must not carry approval metadata")
    claim_effect = str(data.get("claim_effect", "")).strip()
    if claim_effect not in {"none", "candidate_support", "contradicts", "context_only"}:
        failures.append(f"{path}: claim_effect must be none/candidate_support/contradicts/context_only")
    if "scientific truth" not in " ".join(str(x) for x in data.get("does_not_prove") or []):
        failures.append(f"{path}: does_not_prove must include scientific truth")
    return failures


def _records(root: Path, record_type: str) -> list[tuple[Path, dict]]:
    if not root.exists():
        return []
    records: list[tuple[Path, dict]] = []
    for path in sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml")):
        data = _load_yaml(path)
        if data:
            data.setdefault("record_type", record_type)
        records.append((path, data))
    return records


def main() -> int:
    failures: list[str] = []
    failures.extend(_validate_policy())
    evidence_records = _records(FIXTURE_ROOT / "evidence_units", "evidence_unit")
    admission_records = _records(FIXTURE_ROOT / "result_admissions", "result_admission")
    evidence_records.extend(_records(PROJECT_EVIDENCE_ROOT, "evidence_unit"))
    admission_records.extend(_records(PROJECT_ADMISSION_ROOT, "result_admission"))
    if not evidence_records:
        failures.append("missing EvidenceUnit fixture records")
    if not admission_records:
        failures.append("missing ResultAdmission fixture records")
    known_units: set[str] = set()
    for path, data in evidence_records:
        if not isinstance(data, dict):
            failures.append(f"{path}: must be a mapping")
            continue
        unit_id = str(data.get("evidence_unit_id", "")).strip()
        if unit_id:
            known_units.add(unit_id)
        failures.extend(_validate_evidence_unit(path, data))
    for path, data in admission_records:
        if not isinstance(data, dict):
            failures.append(f"{path}: must be a mapping")
            continue
        failures.extend(_validate_result_admission(path, data, known_units))
    if failures:
        print("FAIL: EvidenceUnit problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "PASS: EvidenceUnit/ResultAdmission records are valid "
        f"({len(evidence_records)} evidence unit(s), {len(admission_records)} admission record(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
