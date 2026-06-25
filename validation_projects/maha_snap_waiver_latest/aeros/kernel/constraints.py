"""Kernel invariants for AEROS v0.4.

These constraints are the executable counterpart of the v0.3 invariants YAML.
They are deliberately small and hard: they reject illegal transitions rather
than documenting preferences.
"""
from __future__ import annotations

from collections.abc import Iterable

from .core import Action, Evidence, State


CLAIM_SUPPORT_TYPES = {"validated_result", "result_index", "provenance_record", "evidence_ledger", "claim_registry"}
PROBE_OR_EXCEPTION_TYPES = {"small_data_probe", "receipt_backed_exception", "human_review_receipt"}


def invariant_probe_not_claim(action: Action, evidence: Iterable[Evidence]) -> list[str]:
    failures: list[str] = []
    for item in evidence:
        if item.evidence_type == "small_data_probe" and item.used_for in {"claim", "claim_support", "final_claim"}:
            failures.append("probe evidence cannot directly support final claims")
    return failures


def invariant_human_receipt_not_claim(action: Action, evidence: Iterable[Evidence]) -> list[str]:
    failures: list[str] = []
    for item in evidence:
        if item.evidence_type == "human_review_receipt" and item.used_for in {"claim", "claim_support", "data_fact", "result"}:
            failures.append("human review receipts certify review, not empirical claims or data facts")
    return failures


def invariant_action_receipt_not_evidence(action: Action, evidence: Iterable[Evidence]) -> list[str]:
    failures: list[str] = []
    for item in evidence:
        if item.evidence_type == "action_receipt" and item.used_for in {"claim", "claim_support", "data_fact", "result"}:
            failures.append("action receipts are progress metadata, not empirical evidence")
    return failures


def invariant_backfill_requires_probe(state: State, action: Action, evidence: Iterable[Evidence]) -> list[str]:
    if action != Action.RUN_BACKFILL:
        return []
    if state in {State.PROBE_PASSED, State.BACKFILL_READY}:
        return []
    if any(item.evidence_type == "small_data_probe" and item.clipped_strength() >= 0.5 for item in evidence):
        return []
    if any(item.evidence_type == "receipt_backed_exception" for item in evidence):
        return []
    return ["run_backfill requires probe_passed state, passing probe evidence, or scoped exception"]


def invariant_claim_requires_validated_result(state: State, action: Action, evidence: Iterable[Evidence]) -> list[str]:
    if action != Action.AUDIT_CLAIM:
        return []
    if state not in {State.CLAIM_READY, State.GATE_READY}:
        return ["audit_claim requires claim_ready or gate_ready state"]
    types = {item.evidence_type for item in evidence}
    if not (types & CLAIM_SUPPORT_TYPES):
        return ["claim audit requires validated result/provenance/evidence/claim artifacts"]
    return []


def invariant_no_state_skips(state: State, action: Action) -> list[str]:
    if action == Action.REGISTER_RESULT and state != State.VALIDATED:
        return ["register_result requires validated state"]
    if action == Action.REQUEST_GATE and state != State.GATE_READY:
        return ["request_gate requires gate_ready state"]
    if action == Action.VALIDATE_DATA and state != State.BACKFILL_READY:
        return ["validate_data requires backfill_ready state"]
    return []


def evaluate_invariants(state: State, action: Action, evidence: list[Evidence]) -> list[str]:
    failures: list[str] = []
    failures.extend(invariant_probe_not_claim(action, evidence))
    failures.extend(invariant_action_receipt_not_evidence(action, evidence))
    failures.extend(invariant_human_receipt_not_claim(action, evidence))
    failures.extend(invariant_backfill_requires_probe(state, action, evidence))
    failures.extend(invariant_claim_requires_validated_result(state, action, evidence))
    failures.extend(invariant_no_state_skips(state, action))
    return failures
