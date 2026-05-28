#!/usr/bin/env python3
"""Run the default AEROS harness checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CHECKS = [
    "check_stage_agents.py",
    "check_skill_layer.py",
    "check_discovery_completeness.py",
    "check_idea_bank.py",
    "check_feasibility_matrix.py",
    "check_literature_registry.py",
    "check_literature_functions.py",
    "check_extraction_cards.py",
    "check_synthesis_grounding.py",
    "check_citation_audit.py",
    "check_gap_grounding.py",
    "check_no_raw_data_changes.py",
    "check_data_contract.py",
    "check_protected_definitions.py",
    "check_claim_registry.py",
    "check_paper_numbers.py",
    "check_output_reproducibility.py",
    "check_task_contract.py",
    "check_agent_run_report.py",
    "check_pipeline_runs.py",
    "check_replication_package.py",
]


def main() -> int:
    check_dir = Path("checks")
    failures = 0
    for check in CHECKS:
        path = check_dir / check
        print(f"==> {path}")
        result = subprocess.run([sys.executable, str(path)], check=False)
        if result.returncode != 0:
            failures += 1
    if failures:
        print(f"FAIL: {failures} harness check(s) failed")
        return 1
    print("PASS: all harness checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
