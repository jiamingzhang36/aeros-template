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
    for key in ("external_standard", "principle", "required_package_artifacts", "non_goals"):
        if not policy.get(key):
            failures.append(f"{POLICY}: missing {key}")

    failures.extend(_validate_manifest(TEMPLATE, template, required_fields, statuses))

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
