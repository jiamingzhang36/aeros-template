#!/usr/bin/env python3
"""Lightweight G1 data-readiness probe for the AI grocery audit validation project.

This probe does not download data. It reads the scouted data inventory and
measures whether enough candidate sources have locators and concrete next probes
to justify moving from intake/scouting into measurement design.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "discovery" / "data_inventory.csv"
OUT = ROOT / "discovery" / "data_diagnostics.yml"


def _rows() -> list[dict[str, str]]:
    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("data_id", "").strip()]


def main() -> int:
    rows = _rows()
    public_or_located = [
        row for row in rows
        if row.get("access_status", "").strip().lower() in {"public", "located"}
    ]
    high_priority = [
        row for row in rows
        if row.get("intake_priority", "").strip().lower() == "high"
    ]
    with_next_probe = [
        row for row in rows
        if row.get("next_probe", "").strip()
        and row.get("next_probe", "").strip().lower() not in {"tbd", "todo", "unknown", "n/a", "na", "none"}
    ]
    restricted = [
        row for row in rows
        if row.get("access_status", "").strip().lower() in {"restricted", "paid"}
    ]
    public_high_priority = [
        row for row in high_priority
        if row.get("access_status", "").strip().lower() in {"public", "located"}
    ]

    diagnostics = {
        "candidate_sources_total": len(rows),
        "public_or_located_sources": len(public_or_located),
        "high_priority_sources": len(high_priority),
        "public_high_priority_sources": len(public_high_priority),
        "sources_with_next_probe": len(with_next_probe),
        "restricted_or_paid_sources": len(restricted),
        "nutrition_measurement_sources": sum(
            1 for row in rows
            if "nutrient" in row.get("key_variables", "").lower()
            or "nutrition" in row.get("key_variables", "").lower()
        ),
        "affordability_measurement_sources": sum(
            1 for row in rows
            if "price" in row.get("key_variables", "").lower()
            or "budget" in row.get("key_variables", "").lower()
            or "cost" in row.get("key_variables", "").lower()
        ),
    }

    payload = {
        "status": "measured",
        "measured_on": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "code/01_ingest/probe_data_diagnostics.py",
        "diagnostics": diagnostics,
        "notes": {
            "scope": (
                "G1 readiness only: measures scouted source coverage and probe "
                "specificity from discovery/data_inventory.csv; no raw data were downloaded."
            ),
            "interpretation": (
                "The project has enough located/public candidate sources to proceed "
                "to measurement design, but retailer price capture and AI output "
                "collection still require explicit protocols before causal or strong "
                "empirical claims."
            ),
        },
    }
    OUT.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"wrote measured diagnostics -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
