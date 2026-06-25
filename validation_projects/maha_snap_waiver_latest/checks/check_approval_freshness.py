#!/usr/bin/env python3
"""Validate artifact-bound human approvals remain fresh.

This opt-in check looks for decisions/approvals/*.artifact.yml records. These
records bind a human approval to a specific artifact hash. If the artifact later
changes, the approval cannot be silently reused.

No approval records means the check passes quietly. This check does not decide
whether the human judgment was correct; it only prevents stale authority reuse.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import yaml


APPROVAL_DIR = Path("decisions/approvals")
REQUIRED = ["artifact_path", "artifact_sha256", "approved_by", "approved_at", "decision_ref"]


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _approval_records() -> list[Path]:
    if not APPROVAL_DIR.exists():
        return []
    return sorted(APPROVAL_DIR.glob("*.artifact.yml")) + sorted(APPROVAL_DIR.glob("*.artifact.yaml"))


def main() -> int:
    failures: list[str] = []
    records = _approval_records()
    for path in records:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            failures.append(f"{path}: invalid YAML: {exc}")
            continue
        if not isinstance(payload, dict):
            failures.append(f"{path}: approval record must be a mapping")
            continue
        for key in REQUIRED:
            if not str(payload.get(key, "")).strip():
                failures.append(f"{path}: missing {key}")
        artifact = Path(str(payload.get("artifact_path", "")).strip())
        if not str(artifact):
            continue
        if artifact.is_absolute():
            failures.append(f"{path}: artifact_path must be project-relative, not absolute")
            continue
        if not artifact.exists():
            failures.append(f"{path}: artifact_path does not exist: {artifact}")
            continue
        expected = str(payload.get("artifact_sha256", "")).strip().lower()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            failures.append(f"{path}: malformed artifact_sha256")
            continue
        actual = _sha256(artifact)
        if actual != expected:
            failures.append(
                f"{path}: artifact hash changed for {artifact}; approval is stale and must be renewed"
            )

    if failures:
        print("FAIL: artifact-bound approval freshness problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    if records:
        print(f"PASS: artifact-bound approvals are fresh ({len(records)} record(s))")
    else:
        print("PASS: no artifact-bound approval records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
