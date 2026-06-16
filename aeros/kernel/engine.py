"""Integrity transition checks for AEROS v0.4 compatibility states.

This engine rejects formal illegality, not scientific inadequacy. The typed
artifact graph and claim compiler are the preferred v0.5 abstraction for claim
admissibility.
"""
from __future__ import annotations

from .constraints import evaluate_invariants
from .core import Action, Evidence, State, TransitionResult


class KernelEngine:
    """Apply compatibility state transitions through integrity rules.

    This is not a central scientific referee. It only rejects illegal jumps or
    evidence laundering in the high-level state narrative.
    """

    TRANSITIONS: dict[tuple[State, Action], State] = {
        (State.INVENTORY, Action.SCAN_DATA): State.SCANNED,
        (State.SCANNED, Action.RUN_PROBE): State.PROBE_PASSED,
        (State.PROBE_READY, Action.RUN_PROBE): State.PROBE_PASSED,
        (State.PROBE_PASSED, Action.RUN_BACKFILL): State.BACKFILL_READY,
        (State.BACKFILL_READY, Action.VALIDATE_DATA): State.VALIDATED,
        (State.VALIDATED, Action.REGISTER_RESULT): State.CLAIM_READY,
        (State.CLAIM_READY, Action.AUDIT_CLAIM): State.GATE_READY,
        (State.GATE_READY, Action.REQUEST_GATE): State.RELEASED,
    }

    MIN_STRENGTH: dict[Action, float] = {
        Action.SCAN_DATA: 0.2,
        Action.RUN_PROBE: 0.5,
        Action.RUN_BACKFILL: 0.4,
        Action.VALIDATE_DATA: 0.6,
        Action.REGISTER_RESULT: 0.6,
        Action.AUDIT_CLAIM: 0.5,
        Action.REQUEST_GATE: 0.2,
    }

    def apply(self, state: State | str, action: Action | str, artifacts: list[Evidence]) -> TransitionResult:
        old_state = state if isinstance(state, State) else State(str(state))
        act = action if isinstance(action, Action) else Action(str(action))
        evidence_strength = max((item.clipped_strength() for item in artifacts), default=0.0)
        reasons: list[str] = []
        blocking = evaluate_invariants(old_state, act, artifacts)
        if blocking:
            return TransitionResult(False, old_state, act, None, evidence_strength, reasons, blocking)

        target = self.TRANSITIONS.get((old_state, act))
        if target is None:
            blocking = [f"illegal transition: {old_state.value} + {act.value}"]
            return TransitionResult(False, old_state, act, None, evidence_strength, reasons, blocking)

        required = self.MIN_STRENGTH.get(act, 0.0)
        if evidence_strength < required:
            blocking = [f"evidence strength {evidence_strength:.2f} below required {required:.2f} for {act.value}"]
            return TransitionResult(False, old_state, act, None, evidence_strength, reasons, blocking)

        reasons.append(f"accepted {old_state.value} + {act.value} -> {target.value}")
        reasons.append(f"max evidence strength {evidence_strength:.2f}")
        return TransitionResult(True, old_state, act, target, evidence_strength, reasons, [])
