#!/usr/bin/env python3
"""Check universal intake/adoption artifacts when an adoption exists."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ADOPTION_DIR = Path("adoption")
PACKET = Path("decisions/adoption/adoption_packet.md")
STATE = Path("aeros_state.yml")
REQUIRED = [
    ADOPTION_DIR / "source_manifest.yml",
    ADOPTION_DIR / "inventory_report.md",
    ADOPTION_DIR / "evidence_map.yml",
    ADOPTION_DIR / "extracted_drafts.md",
    ADOPTION_DIR / "gap_plan.yml",
    PACKET,
]


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    if not ADOPTION_DIR.exists() and not PACKET.exists():
        print("SKIP: no adoption artifacts present")
        return 0

    failures: list[str] = []
    for path in REQUIRED:
        if not path.exists():
            failures.append(f"missing adoption artifact: {path}")
        elif path.stat().st_size == 0:
            failures.append(f"empty adoption artifact: {path}")

    state = _load_yaml(STATE)
    if state:
        if str(state.get("current_gate", "")) != "G0":
            failures.append("adoption must not advance formal current_gate beyond G0")
        if str(state.get("gate_status", "")) != "open":
            failures.append("adoption must leave gate_status open")
        decisions = state.get("gate_decisions", [])
        if decisions:
            approvals = [d for d in decisions if isinstance(d, dict) and d.get("decision") == "approve"]
            if approvals:
                failures.append("adoption must not create gate approval decisions")
        adoption = state.get("adoption", {})
        if not isinstance(adoption, dict) or not adoption.get("human_approval_required"):
            failures.append("state.adoption.human_approval_required must be true")

    packet = PACKET.read_text(encoding="utf-8") if PACKET.exists() else ""
    for required_text in (
        "Candidate gate:",
        "Formal current gate after adoption: G0",
        "Gate status after adoption: open",
        "Do not treat candidate claims as supported claims",
    ):
        if required_text not in packet:
            failures.append(f"adoption packet missing required text: {required_text}")

    if failures:
        print("FAIL: adoption packet check failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1

    print("PASS: adoption packet artifacts and conservative gate semantics are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
