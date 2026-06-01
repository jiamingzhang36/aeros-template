#!/usr/bin/env python3
"""Offline smoke measurement audit for the AI grocery validation project.

This is not the final empirical run. It verifies that execution can produce
structured outputs, provenance, result index entries, and a bounded measurement
claim without calling external model APIs or downloading raw data.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "tables" / "measurement_smoke_summary.csv"
PROV = ROOT / "outputs" / ".provenance" / "R001.json"
RESULT_INDEX = ROOT / "evidence" / "result_index.csv"
CLAIMS = ROOT / "evidence" / "claim_registry.md"

RESPONSES = [
    {"persona": "low_income_snap", "run": 1, "items": 9, "vague_items": 3, "estimated_cost": 92.0, "tfp_budget": 85.0, "nutrition_flags": 2},
    {"persona": "low_income_snap", "run": 2, "items": 8, "vague_items": 2, "estimated_cost": 88.0, "tfp_budget": 85.0, "nutrition_flags": 2},
    {"persona": "moderate_budget", "run": 1, "items": 10, "vague_items": 1, "estimated_cost": 96.0, "tfp_budget": 120.0, "nutrition_flags": 1},
    {"persona": "moderate_budget", "run": 2, "items": 10, "vague_items": 1, "estimated_cost": 98.0, "tfp_budget": 120.0, "nutrition_flags": 1},
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_result_index() -> None:
    RESULT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if RESULT_INDEX.exists():
        with RESULT_INDEX.open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle) if row.get("result_id") != "R001"]
    fieldnames = ["result_id", "output_type", "path", "script_or_source", "description", "created_date", "linked_claims", "notes"]
    rows.append({
        "result_id": "R001",
        "output_type": "table",
        "path": "outputs/tables/measurement_smoke_summary.csv",
        "script_or_source": "code/02_analysis/run_measurement_smoke.py",
        "description": "Offline smoke summary for AI grocery recommendation measurement audit pipeline.",
        "created_date": datetime.now(timezone.utc).date().isoformat(),
        "linked_claims": "C001",
        "notes": "Toy validation output; not final empirical evidence.",
    })
    with RESULT_INDEX.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_claim_registry() -> None:
    CLAIMS.write_text(
        "# Claim Registry\n\n"
        "## Claim Types\n\n"
        "- descriptive\n- associational\n- causal\n- mechanism\n- external-validity\n- policy-translation\n- forecast\n\n"
        "## Registry\n\n"
        "| Claim ID | Claim | Type | Status | Evidence ID(s) | Result ID(s) | Boundary / Limitation | Approved |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| C001 | The execution pipeline can produce a bounded measurement summary for an AI grocery recommendation audit using the selected O1 design. | descriptive | draft |  | R001 | Smoke validation only; not final empirical evidence about real AI systems. | no |\n\n"
        "## Status Values\n\n"
        "- draft\n- supported\n- ambiguous\n- unsupported\n- retired\n\n"
        "## Rules\n\n"
        "- A claim cannot be marked supported without at least one evidence ID or result ID.\n"
        "- A causal claim requires a method card that supports causal language.\n"
        "- A forecast claim requires explicit forecast validation or must remain unsupported.\n"
        "- Policy translation must stay within the protected sample, geography, period, and outcome definitions.\n",
        encoding="utf-8",
    )


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    by_persona: dict[str, list[dict]] = {}
    for row in RESPONSES:
        by_persona.setdefault(row["persona"], []).append(row)

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["persona", "runs", "mean_affordability_ratio", "mean_vague_item_share", "mean_nutrition_flags"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for persona, rows in sorted(by_persona.items()):
            runs = len(rows)
            writer.writerow({
                "persona": persona,
                "runs": runs,
                "mean_affordability_ratio": round(sum(r["estimated_cost"] / r["tfp_budget"] for r in rows) / runs, 3),
                "mean_vague_item_share": round(sum(r["vague_items"] / r["items"] for r in rows) / runs, 3),
                "mean_nutrition_flags": round(sum(r["nutrition_flags"] for r in rows) / runs, 3),
            })

    _write_result_index()
    _write_claim_registry()
    PROV.write_text(json.dumps({
        "result_id": "R001",
        "output_path": "outputs/tables/measurement_smoke_summary.csv",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script_or_source": "code/02_analysis/run_measurement_smoke.py",
        "sha256": _sha256(OUT),
        "inputs": ["hard-coded toy RESPONSES in smoke script"],
        "claim_boundary": "smoke validation only; not final empirical evidence",
    }, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"wrote {PROV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
