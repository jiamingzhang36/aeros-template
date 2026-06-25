#!/usr/bin/env python3
"""MAHA wrapper pipeline orchestrator — HONEST SCAFFOLD (does not yet reproduce).

Reads execution/pipeline_manifest.yml. The real analysis lives in an external
source repo (~67 scripts) with no documented master run-order, and the wrapper by
policy does not ingest source raw data. So this orchestrator REPORTS the inventory
and explicitly REFUSES to claim or fabricate reproduction until the author confirms
the run-order and wires real invocation. It never writes or overwrites R001-R004.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML is required to read the pipeline manifest.")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "execution" / "pipeline_manifest.yml"


def _load():
    if not MANIFEST.exists():
        print(f"FAIL: missing {MANIFEST}")
        sys.exit(2)
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="MAHA wrapper pipeline orchestrator (scaffold).")
    parser.add_argument("--mode", choices=["smoke", "run", "status"], default="status")
    args = parser.parse_args()

    m = _load()
    repro = str(m.get("reproduction_status", "unknown"))
    order = str(m.get("run_order", "unknown"))
    steps = m.get("candidate_steps", {}) or {}
    families = [k for k in steps if k != "unmapped_source_scripts"]
    n_scripts = sum(
        len(v.get("scripts", []))
        for k, v in steps.items()
        if isinstance(v, dict) and k != "unmapped_source_scripts"
    )
    src = m.get("source_pipeline", {}) or {}

    print("MAHA wrapper pipeline orchestrator")
    print(f"  mode: {args.mode}")
    print(f"  reproduction_status: {repro}")
    print(f"  run_order: {order}")
    print(f"  candidate result-families: {len(families)} | inventoried source scripts: {n_scripts}")
    print(f"  source pipeline: {src.get('code_dir', '?')} (external; {src.get('total_scripts', '?')} scripts)")

    reproducing = (repro == "reproducing") and (order == "confirmed")
    if not reproducing:
        print()
        print("NOT REPRODUCING — run-order is not author-confirmed.")
        print("This wrapper does not yet reproduce R001-R004. To enable it:")
        print("  1. Confirm the real run-order + script->result mapping in execution/pipeline_manifest.yml")
        print("     (current groupings are filename inferences only).")
        print("  2. Decide how the wrapper invokes/mirrors the source pipeline and the controlled")
        print("     NielsenIQ data path (disconnected disk for the household-CI step).")
        print("  3. Set reproduction_status: reproducing and run_order: confirmed, then wire invocation.")
        print()
        print("No results were produced or modified. This orchestrator will not fabricate them.")
        # smoke = 'does the entrypoint execute cleanly'; that is satisfied. We do not
        # fail the smoke gate, but we also never claim reproduction.
        return 0

    print("run_order confirmed, but real source invocation is not wired in this scaffold.")
    print("Author must implement the confirmed invocation; refusing to fabricate results.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
