#!/usr/bin/env python3
"""Validate receipt-backed exceptions so they cannot become universal bypasses."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

EXCEPTION_DIRS = [Path("decisions/exceptions"), Path("evidence/exceptions"), Path("data/exceptions")]
PROVENANCE_BOUNDARY = Path("harness/provenance_boundary.yml")
ALLOWED_SCOPES = {"one_source_only", "one_run_only", "one_gate_only"}
ALLOWED_EFFECTS = {"allow_backfill_queue_entry", "allow_frozen_evidence_registration", "allow_manual_probe_substitute"}
DISALLOWED_EFFECTS = {"support_empirical_claim", "raise_claim_ceiling", "approve_gate", "skip_provenance", "skip_human_gate"}
REASON_CATEGORIES = {"source_unprobeable_api", "legal_terms_blocker", "credential_required", "frozen_public_snapshot", "manual_archive_only"}


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _validate_exception(path: Path, data: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    label = str(data.get("exception_id") or path)
    scope = str(data.get("scope", "")).strip()
    if scope not in ALLOWED_SCOPES:
        failures.append(f"{label}: invalid or missing scope")
    if not str(data.get("expires_after", "")).strip():
        failures.append(f"{label}: missing expires_after")
    allowed = set(data.get("allowed_effect") or [])
    disallowed = set(data.get("disallowed_effect") or [])
    if not allowed:
        failures.append(f"{label}: missing allowed_effect")
    if not allowed <= ALLOWED_EFFECTS:
        failures.append(f"{label}: unsupported allowed_effect {sorted(allowed - ALLOWED_EFFECTS)}")
    missing_disallowed = DISALLOWED_EFFECTS - disallowed
    if missing_disallowed:
        failures.append(f"{label}: disallowed_effect must include {sorted(missing_disallowed)}")
    if any(effect in DISALLOWED_EFFECTS for effect in allowed):
        failures.append(f"{label}: allowed_effect contains forbidden claim/gate/provenance bypass")
    if data.get("human_review_required") is not True:
        failures.append(f"{label}: human_review_required must be true")
    reason = str(data.get("reason_category", "")).strip()
    if reason not in REASON_CATEGORIES:
        failures.append(f"{label}: invalid or missing reason_category")
    if not str(data.get("decision_ref", "")).strip():
        failures.append(f"{label}: missing decision_ref")
    return failures


def _boundary_has_exception_rule() -> bool:
    if not PROVENANCE_BOUNDARY.exists():
        return False
    data = _load(PROVENANCE_BOUNDARY)
    rules = data.get("rules", []) if isinstance(data, dict) else []
    for rule in rules if isinstance(rules, list) else []:
        if isinstance(rule, dict) and str(rule.get("id", "")) == "receipt_backed_exception_scope_limited":
            return True
    return False


def main() -> int:
    failures: list[str] = []
    if not _boundary_has_exception_rule():
        failures.append("harness/provenance_boundary.yml missing receipt_backed_exception_scope_limited rule")
    paths: list[Path] = []
    for directory in EXCEPTION_DIRS:
        if directory.exists():
            paths.extend(sorted(directory.glob("*.yml")))
    for path in paths:
        try:
            data = _load(path)
        except yaml.YAMLError as exc:
            failures.append(f"{path}: unreadable exception ({exc})")
            continue
        if not isinstance(data, dict):
            failures.append(f"{path}: exception must be a mapping")
            continue
        failures.extend(_validate_exception(path, data))
    if failures:
        print("FAIL: exception scope problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: exception scopes valid ({len(paths)} exception file(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
