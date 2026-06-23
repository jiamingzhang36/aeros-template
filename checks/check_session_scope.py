#!/usr/bin/env python3
"""Validate session scope guard policy and active-session drift if present."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.session_guard import LANES, audit_session, load_policy, start_session  # noqa: E402


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=20, check=False)


def _init_git_fixture(root: Path) -> list[str]:
    failures: list[str] = []
    for argv in [
        ["git", "init"],
        ["git", "config", "user.email", "aeros-fixture@example.invalid"],
        ["git", "config", "user.name", "AEROS Fixture"],
    ]:
        proc = _run(argv, root)
        if proc.returncode != 0:
            failures.append(f"{' '.join(argv)} failed: {(proc.stderr or proc.stdout).strip()}")
    _write_text(root / "README.md", "fixture\n")
    for argv in [["git", "add", "README.md"], ["git", "commit", "-m", "fixture root"]]:
        proc = _run(argv, root)
        if proc.returncode != 0:
            failures.append(f"{' '.join(argv)} failed: {(proc.stderr or proc.stdout).strip()}")
    return failures


def _semantic_scope_fixture(rel_path: str, expected_verdict: str, expected_class: str) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_session_scope_") as tmp_name:
        tmp = Path(tmp_name)
        failures.extend(_init_git_fixture(tmp))
        if failures:
            return failures
        start_session(tmp, lane="data", objective=f"semantic fixture {expected_verdict}", dry_run=False)
        _write_text(tmp / rel_path, "off-scope semantic fixture\n")
        audit = audit_session(tmp)
        if audit.verdict != expected_verdict:
            failures.append(f"{rel_path}: expected {expected_verdict}, got {audit.verdict}")
        matching = [item for item in audit.changed_artifacts if item.get("path") == rel_path]
        if not matching:
            failures.append(f"{rel_path}: audit missing changed_artifacts entry")
        elif matching[0].get("semantic_class") != expected_class:
            failures.append(
                f"{rel_path}: expected semantic_class {expected_class}, got {matching[0].get('semantic_class')}"
            )
        if audit.ok:
            failures.append(f"{rel_path}: semantic drift fixture should not be ok")
    return failures


def main() -> int:
    root = Path.cwd()
    policy = load_policy(root)
    failures: list[str] = []
    lanes = policy.get("lanes") or {}
    for lane in LANES:
        lane_policy = lanes.get(lane) or {}
        if not lane_policy.get("allowed_prefixes"):
            failures.append(f"lane {lane} has no allowed_prefixes")
        if "forbidden_prefixes" not in lane_policy:
            failures.append(f"lane {lane} missing forbidden_prefixes")
    common = policy.get("common_allowed_prefixes") or []
    for required in ["SESSION_CONTRACT.yml", "agent_runs/", "outputs/logs/", "decisions/revision_log.md"]:
        if required not in common:
            failures.append(f"common_allowed_prefixes missing {required}")
    try:
        _, payload = start_session(root, lane="data", objective="dry-run schema check", dry_run=True)
    except Exception as exc:
        failures.append(f"session start dry-run failed: {exc}")
        payload = {}
    if payload and payload.get("active_lane") != "data":
        failures.append("session start dry-run did not preserve lane")
    audit = audit_session(root)
    if audit.active and audit.off_scope_files:
        failures.append("active session has off-scope changes: " + ", ".join(audit.off_scope_files))
    if audit.active and not isinstance(audit.changed_artifacts, list):
        failures.append("active session audit did not emit changed_artifacts")
    if audit.active and audit.verdict not in {
        "no_changes",
        "bookkeeping_only",
        "expected_lane_change",
        "supporting_cross_lane_change",
        "SCOPE_DRIFT",
        "CLAIM_SCOPE_DRIFT",
        "AUTHORITY_DRIFT",
        "inspection_failed",
    }:
        failures.append(f"active session audit has invalid verdict {audit.verdict!r}")
    failures.extend(_semantic_scope_fixture("paper/draft.md", "CLAIM_SCOPE_DRIFT", "claim_scope_drift"))
    failures.extend(_semantic_scope_fixture("evidence/claim_registry.md", "AUTHORITY_DRIFT", "authority_drift"))
    if failures:
        print("FAIL: session scope guard problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: session scope guard is configured; semantic drift fixtures detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
