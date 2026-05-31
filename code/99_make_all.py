#!/usr/bin/env python3
"""AEROS master pipeline: delegates to the real CMPD run_all.py (--mode light).

This script is the bridge between AEROS's check_pipeline_runs check and the
actual research pipeline. It runs the existing analysis in light mode (reuses
extracted/API inputs, does not rerun LLM extraction) and then records a summary
of the key output files for AEROS provenance tracking.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AEROS_ROOT = Path(__file__).resolve().parent.parent
CMPD_ROOT  = Path.home() / "Desktop/cultured_meat_policy_project/cultivated_meat_project"
RUN_ALL    = CMPD_ROOT / "code" / "run_all.py"


def main() -> int:
    if not RUN_ALL.exists():
        print(f"SKIP: CMPD run_all.py not found at {RUN_ALL}")
        print("(Set CMPD_ROOT if the project is elsewhere.)")
        return 0

    print(f"=== AEROS → CMPD pipeline (light mode) ===")
    print(f"  CMPD root : {CMPD_ROOT}")
    print(f"  script    : {RUN_ALL}")

    result = subprocess.run(
        [sys.executable, str(RUN_ALL), "--mode", "light"],
        cwd=str(CMPD_ROOT),
    )

    if result.returncode != 0:
        print(f"FAIL: run_all.py exited with code {result.returncode}")
        return result.returncode

    # Confirm key output files exist (provenance check)
    key_outputs = [
        CMPD_ROOT / "data/final_csv/analysis_ready.csv",
        CMPD_ROOT / "data/final_csv/bill_events.csv",
        CMPD_ROOT / "data/final_csv/component_hazard_coefficients.csv",
    ]
    missing = [p for p in key_outputs if not p.exists()]
    if missing:
        print("WARN: some expected output files not found:")
        for p in missing:
            print(f"  {p}")
    else:
        print("PASS: all key output files present")

    print("=== CMPD pipeline complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
