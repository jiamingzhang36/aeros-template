#!/usr/bin/env python3
"""Validate owner decision rules are enforced by task preflight."""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.owner_decisions import evaluate_owner_decision_rules, load_owner_decision_rules  # noqa: E402
from aeros.runtime.task_preflight import build_task_preflight  # noqa: E402

HEADER = ["Date", "Decision ID", "Task ID", "Agent Recommendation", "Critic Verdict", "Human Decision", "Rationale", "Owner", "Follow-up"]


def _write_log(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        followup = json.dumps({
            "do_not": ["parcel-price", "official-only purity"],
            "binding_constraint": "numerator_size",
            "campaign_budget": 8,
            "expected_yield_per_task": 3,
        })
        _write_log(root / "decisions" / "decision_log.csv", [
            {
                "Date": "2026-07-05",
                "Decision ID": "D-OWNER-001",
                "Task ID": "owner_rule",
                "Agent Recommendation": "",
                "Critic Verdict": "",
                "Human Decision": "approved direction boundary",
                "Rationale": "Do not reopen parcel-price route without human approval.",
                "Owner": "human",
                "Follow-up": followup,
            },
            {
                "Date": "2026-07-05",
                "Decision ID": "D-OLD",
                "Task ID": "owner_rule",
                "Agent Recommendation": "",
                "Critic Verdict": "",
                "Human Decision": "superseded",
                "Rationale": "old rule",
                "Owner": "human",
                "Follow-up": json.dumps({"do_not": ["safe-current-route"], "superseded_by": "D-OWNER-001"}),
            },
        ])
        rules = load_owner_decision_rules(root)
        if len(rules) != 2:
            failures.append("expected two parsed owner decision rules")
        eval_report = evaluate_owner_decision_rules(root, lane="data", intent="reopen parcel-price source route")
        if eval_report.get("status") != "BLOCKED":
            failures.append("owner do_not rule did not block matching intent")
        if not eval_report.get("constraints"):
            failures.append("owner constraints were not surfaced")
        preflight = build_task_preflight(root, lane="data", intent="reopen parcel-price source route")
        if preflight.get("status") != "BLOCKED":
            failures.append("task preflight did not inherit owner decision block")
        if not preflight.get("owner_decision_blocks"):
            failures.append("task preflight missing owner_decision_blocks")
        clean = build_task_preflight(root, lane="data", intent="safe-current-route source audit")
        if clean.get("status") == "BLOCKED":
            failures.append("superseded owner rule should not block current work")

    if failures:
        print("FAIL: owner decision rule problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: owner decision rules are enforced by preflight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
