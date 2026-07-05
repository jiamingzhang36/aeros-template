#!/usr/bin/env python3
"""Validate AEA-style replication package alignment metadata."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("FAIL: PyYAML is required for check_aea_replication_alignment.py") from exc


ROOT = Path.cwd()
POLICY = ROOT / "harness/aea_replication_policy.yml"
TEMPLATE = ROOT / "templates/aea_data_package_manifest.yml"
ACTIVE_MANIFEST = ROOT / "replication/aea_data_package_manifest.yml"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def _validate_manifest(path: Path, data: dict[str, Any], required_fields: list[str], statuses: set[str]) -> list[str]:
    failures: list[str] = []
    for field in required_fields:
        if field not in data:
            failures.append(f"{path}: missing field {field}")
    status = str(data.get("status", "")).strip()
    if status and status not in statuses:
        failures.append(f"{path}: invalid status {status!r}")
    return failures


def main() -> int:
    failures: list[str] = []
    try:
        policy = _load(POLICY)
        template = _load(TEMPLATE)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1

    required_fields = [str(item) for item in (policy.get("required_manifest_fields") or [])]
    statuses = {str(item) for item in (policy.get("allowed_statuses") or [])}
    if not required_fields:
        failures.append(f"{POLICY}: missing required_manifest_fields")
    if not statuses:
        failures.append(f"{POLICY}: missing allowed_statuses")
    for key in (
        "external_standard",
        "policy_version",
        "source_urls",
        "principle",
        "required_package_artifacts",
        "required_alignment_items",
        "recommended_check_profile",
        "profile_command",
        "profile_checks",
        "p_and_p_2026_guidance",
        "non_goals",
    ):
        if not policy.get(key):
            failures.append(f"{POLICY}: missing {key}")
    if policy.get("recommended_check_profile") != "aea":
        failures.append(f"{POLICY}: recommended_check_profile must be aea")
    profile_checks = [str(item) for item in (policy.get("profile_checks") or [])]
    check_profiles_path = ROOT / "harness/check_profiles.yml"
    profiles = yaml.safe_load(check_profiles_path.read_text(encoding="utf-8")) or {}
    aea_profile = ((profiles.get("profiles") or {}).get("aea") or {}).get("checks") or []
    for check in profile_checks:
        if check not in aea_profile:
            failures.append(f"{POLICY}: profile_checks item {check} missing from harness/check_profiles.yml aea profile")
    if str(policy.get("policy_version")) != "February 2026":
        failures.append(f"{POLICY}: policy_version must be February 2026")
    source_urls = [str(item) for item in (policy.get("source_urls") or [])]
    for url in [
        "https://www.aeaweb.org/journals/data/data-code-policy",
        "https://aeadataeditor.github.io/posts/2026-01-19-preparing-pandp-replication-packages",
    ]:
        if url not in source_urls:
            failures.append(f"{POLICY}: missing source URL {url}")
    required_items = {str(item) for item in (policy.get("required_alignment_items") or [])}
    for item in [
        "data_availability_statement",
        "raw_data_or_exception",
        "analysis_data_or_reproducible_build",
        "transformation_and_cleaning_code",
        "analysis_code_for_computational_results",
        "top_level_readme",
        "program_to_output_map",
        "licenses_and_redistribution_rights",
        "trusted_repository_plan",
        "non_public_data_constraints",
    ]:
        if item not in required_items:
            failures.append(f"{POLICY}: required_alignment_items missing {item}")
    p_and_p = policy.get("p_and_p_2026_guidance") or {}
    if "fully compliant" not in str(p_and_p.get("requirement", "")).lower():
        failures.append(f"{POLICY}: P&P guidance must preserve full-compliance requirement")
    if "github alone" not in str(p_and_p.get("repository_note", "")).lower():
        failures.append(f"{POLICY}: P&P guidance must flag GitHub-alone repository risk")

    failures.extend(_validate_manifest(TEMPLATE, template, required_fields, statuses))
    alignment = template.get("aea_2026_alignment")
    if not isinstance(alignment, dict):
        failures.append(f"{TEMPLATE}: missing aea_2026_alignment")
    else:
        missing_items = required_items - set(alignment)
        if missing_items:
            failures.append(
                f"{TEMPLATE}: aea_2026_alignment missing {', '.join(sorted(missing_items))}"
            )
    standard_alignment = template.get("standard_alignment") or {}
    if standard_alignment.get("policy_version") != "February 2026":
        failures.append(f"{TEMPLATE}: standard_alignment.policy_version must be February 2026")

    if ACTIVE_MANIFEST.exists():
        try:
            active = _load(ACTIVE_MANIFEST)
        except ValueError as exc:
            failures.append(str(exc))
        else:
            failures.extend(_validate_manifest(ACTIVE_MANIFEST, active, required_fields, statuses))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    scope = "template + active manifest" if ACTIVE_MANIFEST.exists() else "template only"
    print(f"PASS: AEA replication alignment metadata valid ({scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
