#!/usr/bin/env python3
"""Exercise risk-based completion review and content-addressed reuse."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aeros.runtime.completion_review import build_review_packet, classify_completion_review  # noqa: E402
from aeros.runtime.critic import CriticVerdict, load_cached_verdict, save_cached_verdict  # noqa: E402


def _contract(*, stage: str, lane: str, outputs: list[str], raw: dict | None = None):
    return SimpleNamespace(
        task_id="T-REVIEW",
        goal="fixture review",
        stage=stage,
        work_lane=lane,
        allowed_outputs=outputs,
        raw=raw or {},
    )


def main() -> int:
    failures: list[str] = []
    low = classify_completion_review(
        _contract(stage="maintenance", lane="harness", outputs=["agent_runs/report.md"]),
        ["agent_runs/report.md"],
    )
    high = classify_completion_review(
        _contract(stage="analysis", lane="method", outputs=["outputs/analysis/model.csv"]),
        ["outputs/analysis/model.csv"],
    )
    critical = classify_completion_review(
        _contract(stage="claim", lane="claim", outputs=["evidence/claim_registry.md"]),
        ["evidence/claim_registry.md"],
    )
    if low.risk != "low" or low.required:
        failures.append("low-risk bookkeeping work incorrectly requires a critic")
    if high.risk != "high" or not high.required or high.human_gate_required:
        failures.append("analysis output did not require an independent critic")
    if critical.risk != "critical" or not critical.required or not critical.human_gate_required:
        failures.append("claim authority surface did not require critic plus human gate")

    with tempfile.TemporaryDirectory(prefix="aeros_completion_review_") as tmp:
        root = Path(tmp)
        output = root / "outputs" / "analysis" / "model.csv"
        output.parent.mkdir(parents=True)
        output.write_text("term,estimate\nx,1.0\n", encoding="utf-8")
        contract = _contract(
            stage="analysis",
            lane="method",
            outputs=["outputs/analysis/model.csv"],
        )
        candidate = SimpleNamespace(
            accepted_outputs=("outputs/analysis/model.csv",),
            observed_writes=("outputs/analysis/model.csv",),
            denied_writes=(),
            undeclared_writes=(),
        )
        check = SimpleNamespace(name="check_fixture.py", passed=True, exit_code=0, failures=[])
        first = build_review_packet(root, contract, candidate, [check])
        second = build_review_packet(root, contract, candidate, [check])
        if first["review_key"] != second["review_key"]:
            failures.append("unchanged completion evidence produced an unstable review key")
        verdict = CriticVerdict(
            verdict="pass",
            provider="fixture",
            model="fixture",
            review_key=first["review_key"],
        )
        save_cached_verdict(root, verdict)
        cached = load_cached_verdict(root, first["review_key"])
        if cached is None or not cached.cached or cached.verdict != "pass":
            failures.append("content-addressed critic verdict was not reused")
        output.write_text("term,estimate\nx,2.0\n", encoding="utf-8")
        changed = build_review_packet(root, contract, candidate, [check])
        if changed["review_key"] == first["review_key"]:
            failures.append("artifact change did not invalidate the critic review key")

    payload = {"status": "fail" if failures else "pass", "failures": failures}
    if "--json" in sys.argv:
        print(json.dumps(payload))
    elif failures:
        print("FAIL: completion review")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: completion review is risk-based, bounded, and content-addressed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
