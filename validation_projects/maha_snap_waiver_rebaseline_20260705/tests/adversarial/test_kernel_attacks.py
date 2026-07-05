"""Adversarial kernel tests for AEROS v0.4.

These tests are intentionally small: they encode attacks that previously caused
progress laundering or state skips.
"""
from aeros.kernel import Action, Evidence, KernelEngine, State


def test_fake_progress_attack_rejected():
    engine = KernelEngine()
    evidence = [Evidence("agent_runs/action_receipts/cleanup.yml", 0.95, "action_receipt", "result")]
    result = engine.apply(State.SCANNED, Action.RUN_PROBE, evidence)
    assert not result.accepted
    assert any("action receipts" in item for item in result.blocking_invariants)


def test_probe_bypass_attack_rejected():
    engine = KernelEngine()
    evidence = [Evidence("data/backfill/backfill_queue.yml", 0.9, "backfill_queue", "collection")]
    result = engine.apply(State.SCANNED, Action.RUN_BACKFILL, evidence)
    assert not result.accepted
    assert any("run_backfill requires" in item for item in result.blocking_invariants)


def test_receipt_laundering_claim_attack_rejected():
    engine = KernelEngine()
    evidence = [Evidence("evidence/receipts/review.md", 0.95, "human_review_receipt", "claim")]
    result = engine.apply(State.CLAIM_READY, Action.AUDIT_CLAIM, evidence)
    assert not result.accepted
    assert any("claim audit requires" in item for item in result.blocking_invariants)


def test_valid_probe_transition_accepted():
    engine = KernelEngine()
    evidence = [Evidence("data/probes/source/probe_metadata.yml", 0.72, "small_data_probe", "feasibility")]
    result = engine.apply(State.SCANNED, Action.RUN_PROBE, evidence)
    assert result.accepted
    assert result.new_state == State.PROBE_PASSED
