#!/usr/bin/env python3
"""Validate the early discovery route-decision scaffold."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


ROUTE_DECISION = Path("discovery/route_decision.yml")
REQUIRED_ROUTES = {
    "negative_seed_first",
    "base_universe_first",
    "coverage_probe_first",
    "literature_gap_first",
    "data_access_first",
    "document_first",
    "registry_first",
    "hybrid",
}
NEGATIVE_SEED_TERMS = {"illegal", "scam", "fraud", "penalty", "enforcement", "complaint", "lawsuit", "court"}


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    failures: list[str] = []
    data = _load(ROUTE_DECISION)
    if not data:
        failures.append("missing or empty discovery/route_decision.yml")
    allowed = set(str(item) for item in data.get("allowed_routes") or [])
    missing = REQUIRED_ROUTES - allowed
    if missing:
        failures.append(f"route_decision missing allowed routes: {sorted(missing)}")
    rules = data.get("route_rules") or {}
    hypotheses = data.get("route_hypotheses") or {}
    for route in REQUIRED_ROUTES:
        rule = rules.get(route) or {}
        if not rule.get("default_when"):
            failures.append(f"{route}: missing default_when")
        if not rule.get("first_actions"):
            failures.append(f"{route}: missing first_actions")
        hypothesis = hypotheses.get(route) or {}
        if not str(hypothesis.get("hypothesis") or "").strip():
            failures.append(f"{route}: missing route_hypotheses.hypothesis")
        if not str(hypothesis.get("falsification_probe") or "").strip():
            failures.append(f"{route}: missing route_hypotheses.falsification_probe")
        if not str(hypothesis.get("promotion_condition") or "").strip():
            failures.append(f"{route}: missing route_hypotheses.promotion_condition")
    negative_rule_text = " ".join(str(item).lower() for item in ((rules.get("negative_seed_first") or {}).get("default_when") or []))
    if not any(term in negative_rule_text for term in NEGATIVE_SEED_TERMS):
        failures.append("negative_seed_first must explicitly cover illegal/scam/enforcement/complaint phenomena")
    decision = data.get("current_decision") or {}
    selected = str(data.get("selected_route") or decision.get("route") or "").strip()
    decision_route = str(decision.get("route") or selected or "").strip()
    allowed_or_pending = allowed | {"", "pending", "TBD", "tbd"}
    if selected not in allowed_or_pending:
        failures.append(f"selected_route is invalid: {selected}")
    if decision_route not in allowed_or_pending:
        failures.append(f"current_decision.route is invalid: {decision_route}")
    status = str(data.get("decision_status") or "").strip()
    if status not in {"pending", "proposed", "human_approved", "blocked"}:
        failures.append(f"decision_status is invalid: {status}")
    if status == "human_approved" and (decision_route not in allowed or not str(decision.get("decision_ref") or "").strip()):
        failures.append("human_approved route decisions require an allowed route and decision_ref")
    if not data.get("does_not_prove"):
        failures.append("route_decision missing does_not_prove boundary")
    if failures:
        print("FAIL: discovery route decision problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: discovery route decision scaffold is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
