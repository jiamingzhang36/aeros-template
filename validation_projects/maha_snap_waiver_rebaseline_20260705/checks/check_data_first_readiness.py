#!/usr/bin/env python3
"""Validate that active research projects are driven by data state, not empty process."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.data_first import detect_gaps, project_mode, read_inventory, scan_project  # noqa: E402

DATA_STATE = Path("data/data_state.yml")
GAP_PLAN = Path("data/data_gap_plan.yml")
BACKFILL_QUEUE = Path("data/backfill/backfill_queue.yml")


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    root = Path.cwd()
    mode = project_mode(root)
    if mode == "template":
        print("PASS: data-first readiness inactive in template mode")
        return 0
    failures: list[str] = []
    state = _load(DATA_STATE) or scan_project(root)
    rows = read_inventory(root)
    gaps = detect_gaps(root, state)
    if not DATA_STATE.exists():
        failures.append("active/adopted project missing data/data_state.yml; run `aeros data scan`")
    if not rows:
        failures.append("active/adopted project has no populated discovery/data_inventory.csv rows")
    if gaps and not GAP_PLAN.exists() and not BACKFILL_QUEUE.exists():
        failures.append("data gaps detected but neither data/data_gap_plan.yml nor data/backfill/backfill_queue.yml exists")
    if failures:
        print("FAIL: data-first readiness problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: data-first readiness valid ({mode}, {len(rows)} inventory row(s), {len(gaps)} gap(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
