"""Harness-observed receipts.

These receipts are written by the harness runner from observed subprocess
results and local file hashes. They are deliberately narrower than task
completion receipts: they prove only that a particular check command observed
particular exit codes and source hashes at a point in time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import tempfile
import re


DEFAULT_SUBJECTS = (
    "project_manifest.yml",
    "harness/check_profiles.yml",
    "decisions/update_ledger.md",
    "AGENTS.md",
)

DOES_NOT_PROVE = (
    "scientific validity",
    "data truth",
    "literature full-text sufficiency",
    "claim support",
    "gate approval",
    "paper readiness",
    "absence of malicious code outside the observed checks",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def subject_hashes(root: Path, rel_paths: list[str] | tuple[str, ...] = DEFAULT_SUBJECTS) -> list[dict]:
    subjects: list[dict] = []
    for rel in rel_paths:
        path = root / rel
        item = {"path": rel, "exists": path.exists()}
        if path.is_file():
            item["sha256"] = sha256_file(path)
            item["size_bytes"] = path.stat().st_size
        subjects.append(item)
    return subjects


def _safe_receipt_id(profile: str, when: datetime) -> str:
    safe_profile = re.sub(r"[^A-Za-z0-9_.-]+", "-", profile or "full").strip("-") or "full"
    stamp = when.strftime("%Y%m%dT%H%M%SZ")
    return f"HARNESS-{safe_profile}-{stamp}"


def write_observed_harness_receipt(
    root: Path,
    summary: dict,
    command: list[str],
    *,
    subjects: list[str] | tuple[str, ...] = DEFAULT_SUBJECTS,
    output_dir: str = "outputs/harness_receipts",
) -> tuple[Path, dict]:
    """Write an observed harness receipt and return ``(path, payload)``."""

    root = root.resolve()
    when = datetime.now(timezone.utc)
    profile = str(summary.get("profile") or "full")
    receipt_id = _safe_receipt_id(profile, when)
    payload = {
        "version": 1,
        "receipt_type": "harness_observed_check_run",
        "receipt_id": receipt_id,
        "generated_by": "checks/run_harness_checks.py",
        "generated_at": when.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "command": list(command),
        "profile": profile,
        "status": summary.get("status"),
        "failures": int(summary.get("failures") or 0),
        "checks": list(summary.get("checks") or []),
        "subjects": subject_hashes(root, subjects),
        "verification_strength": "harness_observed_exit_codes_and_file_hashes",
        "does_not_prove": list(DOES_NOT_PROVE),
    }
    payload["storage"] = "project_outputs"
    out_dir = root / output_dir
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        safe_root = re.sub(r"[^A-Za-z0-9_.-]+", "-", root.name or "aeros").strip("-") or "aeros"
        out_dir = Path(tempfile.gettempdir()) / "aeros_harness_receipts" / safe_root
        out_dir.mkdir(parents=True, exist_ok=True)
        payload["storage"] = "fallback_tempdir"
        payload["storage_fallback_reason"] = f"{type(exc).__name__}: {exc}"
    path = out_dir / f"{receipt_id}.json"
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        if payload.get("storage") == "fallback_tempdir":
            raise
        safe_root = re.sub(r"[^A-Za-z0-9_.-]+", "-", root.name or "aeros").strip("-") or "aeros"
        out_dir = Path(tempfile.gettempdir()) / "aeros_harness_receipts" / safe_root
        out_dir.mkdir(parents=True, exist_ok=True)
        payload["storage"] = "fallback_tempdir"
        payload["storage_fallback_reason"] = f"{type(exc).__name__}: {exc}"
        path = out_dir / f"{receipt_id}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path, payload
