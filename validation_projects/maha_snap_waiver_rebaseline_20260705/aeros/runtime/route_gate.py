"""Early route-decision gate helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


ROUTE_PATH = Path("discovery/route_decision.yml")
ROUTE_SENSITIVE_TERMS = (
    "source_capture",
    "recapture",
    "denominator",
    "negative seed",
    "base universe",
    "official source",
    "data_access",
    "portal",
)


def load_route_decision(root: Path) -> dict[str, Any]:
    path = root / ROUTE_PATH
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def selected_route_status(root: Path) -> dict[str, Any]:
    data = load_route_decision(root)
    current = data.get("current_decision") or {}
    selected = str(data.get("selected_route") or current.get("route") or "").strip()
    status = str(data.get("decision_status") or "").strip()
    return {
        "route": selected,
        "decision_status": status,
        "decision_ref": str(current.get("decision_ref") or "").strip(),
        "allowed_routes": list(data.get("allowed_routes") or []),
    }


def route_required_for_intent(intent: str) -> bool:
    value = str(intent or "").lower()
    return any(term in value for term in ROUTE_SENSITIVE_TERMS)


def validate_route_early_gate(root: Path, *, intent: str = "") -> dict[str, Any]:
    status = selected_route_status(root)
    route = status.get("route", "")
    decision_status = status.get("decision_status", "")
    failures: list[str] = []
    if route_required_for_intent(intent):
        if route in {"", "pending", "TBD", "tbd"}:
            failures.append("route-sensitive work requires selected_route before source/data expansion")
        if decision_status not in {"proposed", "human_approved"}:
            failures.append("route-sensitive work requires decision_status proposed or human_approved")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "route": route,
        "decision_status": decision_status,
        "does_not_prove": [
            "that the selected route is correct",
            "that data access exists",
            "that source coverage is sufficient",
            "that a gate is approved",
        ],
    }
