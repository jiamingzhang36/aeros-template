"""Core typed objects for the AEROS v0.4 formal kernel.

The kernel intentionally exposes a small state/action calculus. Everything else
in AEROS should either produce artifacts/events or ask this kernel whether a
transition is legal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class State(str, Enum):
    INVENTORY = "inventory"
    SCANNED = "scanned"
    PROBE_READY = "probe_ready"
    PROBE_PASSED = "probe_passed"
    BACKFILL_READY = "backfill_ready"
    VALIDATED = "validated"
    CLAIM_READY = "claim_ready"
    GATE_READY = "gate_ready"
    RELEASED = "released"


class Action(str, Enum):
    SCAN_DATA = "scan_data"
    RUN_PROBE = "run_probe"
    RUN_BACKFILL = "run_backfill"
    VALIDATE_DATA = "validate_data"
    REGISTER_RESULT = "register_result"
    AUDIT_CLAIM = "audit_claim"
    REQUEST_GATE = "request_gate"


@dataclass(frozen=True)
class Evidence:
    artifact: str
    strength: float
    evidence_type: str
    used_for: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def clipped_strength(self) -> float:
        return max(0.0, min(1.0, float(self.strength)))


@dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    old_state: State
    action: Action
    new_state: State | None
    evidence_strength: float
    reasons: list[str]
    blocking_invariants: list[str] = field(default_factory=list)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def evidence_strength(artifact: str | Path, *, used_for: str = "") -> Evidence:
    """Conservative evidence function E: artifact -> strength in [0, 1].

    This is deterministic and intentionally conservative. It does not read
    claims from prose; it only recognizes AEROS artifact classes and minimal
    success markers.
    """
    path = Path(artifact)
    rel = path.as_posix()
    data = _load_yaml(path)

    if rel.endswith("probe_metadata.yml"):
        verdict = str(data.get("probe_verdict", "")).strip()
        sample_rows = int(data.get("sample_rows") or 0)
        strength = 0.72 if verdict == "passed" and sample_rows > 0 else 0.18
        return Evidence(rel, strength, "small_data_probe", used_for, data)

    if "data_state.yml" in rel:
        return Evidence(rel, 0.35, "data_scan", used_for, data)

    if "data_gap_plan.yml" in rel:
        return Evidence(rel, 0.35, "gap_plan", used_for, data)

    if "backfill_queue.yml" in rel:
        return Evidence(rel, 0.45, "backfill_queue", used_for, data)

    if rel.endswith(".json") and "outputs/.provenance" in rel:
        return Evidence(rel, 0.8, "provenance_record", used_for, data)

    if "result_index.csv" in rel:
        return Evidence(rel, 0.65, "result_index", used_for, {})

    if "evidence_ledger.csv" in rel:
        return Evidence(rel, 0.65, "evidence_ledger", used_for, {})

    if "claim_registry.md" in rel:
        return Evidence(rel, 0.55, "claim_registry", used_for, {})

    if "action_receipts" in rel:
        return Evidence(rel, 0.12, "action_receipt", used_for, data)

    if "receipts" in rel or "exceptions" in rel:
        return Evidence(rel, 0.25, "human_review_receipt", used_for, data)

    return Evidence(rel, 0.0, "unknown", used_for, {})
