#!/usr/bin/env python3
"""Dataset-aware ideation guard (HLER borrow: feasibility-constrained hypotheses).

HLER's strongest measured result is that constraining hypothesis *generation* on
real data availability raises feasibility from ~41% to ~87%. AEROS mirrors that at
two levels: (1) structurally, D001a_framing now depends on D002_data_scouting so the
data audit precedes questioning (DATA_AUDIT -> QUESTIONING); (2) here, an output
guard: a data-dependent idea may not be advanced unless the data it needs has
actually been audited as feasible in discovery/data_inventory.csv.

Scoping (deliberately narrow, to avoid category errors): this guard ONLY fires for
idea-bank rows that OPT IN by setting `requires_data` to a truthy value. Purely
methodological ideas (e.g. "maintain a claim audit", "track coverage caveats") need
no dataset and stay exempt. The guard is therefore inert for projects whose idea
bank carries no data-dependent rows -- by design, not by accident.

A row that opts in must name the data it relies on via a `data_refs` column (one or
more data_id / intake_ref tokens, ';'- or ','-separated). Each referenced token must
resolve to a row in data_inventory.csv whose feasibility_status is confirmed (i.e.
not blank / tbd / unknown / infeasible / no). Advancing an empirical idea whose data
is merely "located" but not yet feasible is exactly the infeasible-hypothesis
failure HLER prevents.

Pass-quiet when: no idea_bank, no data_inventory, or no opted-in rows.

Run `python3 checks/check_dataset_aware_ideation.py --selftest` to verify the guard
actually catches the failure mode (and clears the feasible case).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


IDEA_BANK = Path("discovery/idea_bank.csv")
DATA_INVENTORY = Path("discovery/data_inventory.csv")

TRUTHY = {"yes", "true", "1", "y", "required", "empirical"}
# A referenced dataset counts as usable only if its feasibility is affirmatively
# confirmed. Everything tentative or negative is treated as not-yet-feasible.
FEASIBLE_OK = {"feasible", "confirmed", "validated", "collected", "available", "yes", "ok", "ready"}
ACTIVE_STATUSES = {"supported", "promoted_to_design", "under_verification", "revised"}


def _tokens(value: str) -> list[str]:
    raw = (value or "").replace(";", ",").split(",")
    return [t.strip() for t in raw if t.strip()]


def _inventory_feasible_ids(inv_rows: list[dict]) -> set[str]:
    """data_id / intake_ref tokens whose inventory row is confirmed feasible."""
    ok: set[str] = set()
    for r in inv_rows:
        feas = (r.get("feasibility_status", "") or "").strip().lower()
        access = (r.get("access_status", "") or "").strip().lower()
        # feasible if feasibility_status is affirmatively OK, or access_status is.
        if feas in FEASIBLE_OK or access in FEASIBLE_OK:
            for key in ("data_id", "intake_ref", "dataset_name"):
                tok = (r.get(key, "") or "").strip()
                if tok:
                    ok.add(tok)
    return ok


def _evaluate(idea_rows: list[dict], inv_rows: list[dict]) -> list[str]:
    failures: list[str] = []
    feasible_ids = _inventory_feasible_ids(inv_rows)
    for row in idea_rows:
        if (row.get("requires_data", "") or "").strip().lower() not in TRUTHY:
            continue  # opt-in only; methodological ideas are exempt
        if (row.get("status", "") or "").strip().lower() not in ACTIVE_STATUSES:
            continue  # only guards ideas actually being advanced
        idea_id = (row.get("idea_id", "") or "").strip() or "<no id>"
        refs = _tokens(row.get("data_refs", ""))
        if not refs:
            failures.append(
                f"{idea_id}: requires_data set but data_refs is empty -- a data-dependent "
                f"idea must name the inventory data it relies on"
            )
            continue
        unmet = [t for t in refs if t not in feasible_ids]
        if unmet:
            failures.append(
                f"{idea_id}: data_refs {unmet} are not confirmed-feasible in "
                f"{DATA_INVENTORY.name} (infeasible-hypothesis -- audit/validate the data "
                f"or reframe before advancing)"
            )
    return failures


def _load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    if not IDEA_BANK.exists() or not DATA_INVENTORY.exists():
        print("PASS: dataset-aware ideation guard inert "
              f"(missing {IDEA_BANK if not IDEA_BANK.exists() else DATA_INVENTORY})")
        return 0
    idea_rows = _load(IDEA_BANK)
    inv_rows = _load(DATA_INVENTORY)
    opted_in = [r for r in idea_rows
                if (r.get("requires_data", "") or "").strip().lower() in TRUTHY]
    if not opted_in:
        print("PASS: dataset-aware ideation guard inert "
              "(no idea-bank rows opt in via requires_data)")
        return 0
    failures = _evaluate(idea_rows, inv_rows)
    if failures:
        print("FAIL: data-dependent ideas not grounded in feasible inventory data:")
        print("\n".join(failures))
        return 1
    print(f"PASS: {len(opted_in)} data-dependent idea(s) grounded in feasible inventory data")
    return 0


def _selftest() -> int:
    inv = [
        {"data_id": "D_FEAS", "intake_ref": "ref_feas", "dataset_name": "Feasible set",
         "access_status": "obtained", "feasibility_status": "feasible"},
        {"data_id": "D_TBD", "intake_ref": "ref_tbd", "dataset_name": "Located only",
         "access_status": "located", "feasibility_status": "tbd"},
    ]
    # Case 1: empirical idea pointing at not-yet-feasible data -> must FAIL.
    bad = [{"idea_id": "E1", "status": "supported", "requires_data": "yes",
            "data_refs": "D_TBD"}]
    f1 = _evaluate(bad, inv)
    assert f1, "expected FAIL for idea referencing tbd-feasibility data"
    # Case 2: empirical idea with no data_refs at all -> must FAIL.
    bad2 = [{"idea_id": "E2", "status": "promoted_to_design", "requires_data": "yes",
             "data_refs": ""}]
    assert _evaluate(bad2, inv), "expected FAIL for empirical idea with empty data_refs"
    # Case 3: empirical idea on feasible data -> must PASS.
    good = [{"idea_id": "E3", "status": "supported", "requires_data": "yes",
             "data_refs": "D_FEAS"}]
    assert not _evaluate(good, inv), "expected PASS for idea on feasible data"
    # Case 4: methodological idea (no opt-in) -> exempt even with no data.
    meth = [{"idea_id": "M1", "status": "supported", "requires_data": "",
             "data_refs": ""}]
    assert not _evaluate(meth, inv), "methodological idea must be exempt"
    print("selftest PASS: guard fails infeasible/ungrounded empirical ideas, "
          "clears feasible ones, exempts methodological ones")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(main())
