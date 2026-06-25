#!/usr/bin/env python3
"""Validate paper-readiness automation remains report-only."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
POLICY = Path("harness/paper_readiness_policy.yml")
PROTECTED = [
    Path("paper/draft.md"),
    Path("evidence/claim_registry.md"),
    Path("decisions/decision_log.csv"),
    Path("aeros_state.yml"),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main() -> int:
    failures: list[str] = []
    if not POLICY.exists():
        failures.append(f"missing {POLICY}")
    policy_text = _read(POLICY)
    for phrase in ["report_only", "paper_ready_verdict: not_asserted", "must not approve paper readiness"]:
        if phrase not in policy_text:
            failures.append(f"{POLICY}: missing boundary phrase {phrase!r}")

    before = {path.as_posix(): _read(path) for path in PROTECTED}
    proc = subprocess.run(
        [sys.executable, "-m", "aeros.cli", "paper-readiness", "report", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        failures.append(f"paper-readiness report failed: {proc.stderr or proc.stdout}")
    else:
        payload = json.loads(proc.stdout)
        if payload.get("authority_status") != "report_only":
            failures.append("paper-readiness report is not report_only")
        if payload.get("paper_ready_verdict") != "not_asserted":
            failures.append("paper-readiness report asserted a paper-ready verdict")
        if payload.get("required_human_gate") is not True:
            failures.append("paper-readiness report does not require human gate")
        if "paper readiness" not in payload.get("does_not_prove", []):
            failures.append("paper-readiness report does_not_prove omits paper readiness")

    after = {path.as_posix(): _read(path) for path in PROTECTED}
    if before != after:
        failures.append("paper-readiness report modified protected research/governance files")

    if failures:
        print("FAIL: paper-readiness report problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: paper-readiness report is human-gated and non-authoritative")
    return 0


if __name__ == "__main__":
    sys.exit(main())
