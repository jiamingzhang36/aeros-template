"""Owner decision rules for task preflight.

The decision log is useful only if selected owner decisions can be read as
rules before work starts. This module parses structured follow-up metadata from
`decisions/decision_log.csv` and surfaces deterministic blocks such as do-not
patterns. It does not interpret free-form rationale, approve gates, or decide
scientific validity.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import json
import re
from typing import Any

DECISION_LOG = Path("decisions/decision_log.csv")

DOES_NOT_PROVE = [
    "that free-form rationale has been semantically understood",
    "that the owner decision is scientifically correct",
    "that a blocked task is never useful",
    "that gate approval, claim support, or paper readiness is granted",
]


@dataclass(frozen=True)
class OwnerDecisionRule:
    decision_id: str
    task_id: str
    owner: str
    do_not: tuple[str, ...]
    stop_condition: str
    binding_constraint: str
    campaign_budget: str
    expected_yield_per_task: str
    superseded_by: str
    source_column: str

    @property
    def active(self) -> bool:
        return not self.superseded_by.strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "task_id": self.task_id,
            "owner": self.owner,
            "do_not": list(self.do_not),
            "stop_condition": self.stop_condition,
            "binding_constraint": self.binding_constraint,
            "campaign_budget": self.campaign_budget,
            "expected_yield_per_task": self.expected_yield_per_task,
            "superseded_by": self.superseded_by,
            "active": self.active,
            "source_column": self.source_column,
        }


def _split_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    text = str(value).strip()
    if not text:
        return ()
    if text.startswith("["):
        try:
            loaded = json.loads(text)
            if isinstance(loaded, list):
                return tuple(str(item).strip() for item in loaded if str(item).strip())
        except Exception:
            pass
    parts = re.split(r"[|;]\s*|,\s*", text)
    return tuple(part.strip() for part in parts if part.strip())


def _parse_followup(value: str) -> dict[str, Any]:
    text = (value or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            loaded = json.loads(text)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}
    # Lightweight key=value; key2=value2 parser for humans who do not want JSON.
    out: dict[str, Any] = {}
    for chunk in re.split(r";\s*", text):
        if "=" not in chunk:
            continue
        key, raw = chunk.split("=", 1)
        key = key.strip().lower().replace("-", "_").replace(" ", "_")
        if key:
            out[key] = raw.strip()
    return out


def _first(row: dict[str, str], *names: str) -> str:
    lower = {str(k).strip().lower().replace("-", "_").replace(" ", "_"): v for k, v in row.items()}
    for name in names:
        value = lower.get(name.strip().lower().replace("-", "_").replace(" ", "_"))
        if value:
            return str(value).strip()
    return ""


def _merge_rule_data(row: dict[str, str]) -> tuple[dict[str, Any], str]:
    followup = _parse_followup(row.get("Follow-up", ""))
    data: dict[str, Any] = dict(followup)
    explicit = {
        "do_not": _first(row, "do_not", "do not", "do_not_patterns"),
        "stop_condition": _first(row, "stop_condition", "stop condition"),
        "binding_constraint": _first(row, "binding_constraint", "binding constraint"),
        "campaign_budget": _first(row, "campaign_budget", "campaign budget"),
        "expected_yield_per_task": _first(row, "expected_yield_per_task", "expected yield per task"),
        "superseded_by": _first(row, "superseded_by", "superseded by"),
    }
    for key, value in explicit.items():
        if value:
            data[key] = value
    source = "Follow-up" if followup else "structured_columns"
    return data, source


def load_owner_decision_rules(root: Path, path: str | Path | None = None) -> list[OwnerDecisionRule]:
    log_path = Path(path) if path else root / DECISION_LOG
    if not log_path.is_absolute():
        log_path = root / log_path
    if not log_path.exists():
        return []
    rules: list[OwnerDecisionRule] = []
    with log_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            data, source = _merge_rule_data({k: (v or "") for k, v in row.items()})
            do_not = _split_list(data.get("do_not") or data.get("do_not_patterns"))
            if not do_not and not data.get("stop_condition") and not data.get("binding_constraint"):
                continue
            rules.append(
                OwnerDecisionRule(
                    decision_id=str(row.get("Decision ID") or "").strip(),
                    task_id=str(row.get("Task ID") or "").strip(),
                    owner=str(row.get("Owner") or "").strip(),
                    do_not=do_not,
                    stop_condition=str(data.get("stop_condition") or "").strip(),
                    binding_constraint=str(data.get("binding_constraint") or "").strip(),
                    campaign_budget=str(data.get("campaign_budget") or "").strip(),
                    expected_yield_per_task=str(data.get("expected_yield_per_task") or "").strip(),
                    superseded_by=str(data.get("superseded_by") or "").strip(),
                    source_column=source,
                )
            )
    return rules


def evaluate_owner_decision_rules(root: Path, *, lane: str = "", intent: str = "", task_id: str = "") -> dict[str, Any]:
    rules = load_owner_decision_rules(root)
    active = [rule for rule in rules if rule.active]
    blob = f"{lane} {intent} {task_id}".lower()
    blocks: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    for rule in active:
        for pattern in rule.do_not:
            needle = pattern.lower().strip()
            if needle and needle in blob:
                blocks.append({
                    "decision_id": rule.decision_id,
                    "pattern": pattern,
                    "reason": f"owner decision do_not pattern matched: {pattern}",
                    "owner": rule.owner,
                })
        if rule.stop_condition or rule.binding_constraint:
            constraints.append({
                "decision_id": rule.decision_id,
                "stop_condition": rule.stop_condition,
                "binding_constraint": rule.binding_constraint,
                "campaign_budget": rule.campaign_budget,
                "expected_yield_per_task": rule.expected_yield_per_task,
            })
    return {
        "status": "BLOCKED" if blocks else "CLEAR",
        "active_rule_count": len(active),
        "blocks": blocks,
        "constraints": constraints,
        "rules": [rule.to_dict() for rule in active],
        "does_not_prove": DOES_NOT_PROVE,
    }
