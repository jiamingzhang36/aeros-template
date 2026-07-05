#!/usr/bin/env python3
"""Validate analytical provenance: preanalysis plan, spec space, and spec run index."""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import yaml

POLICY = Path('harness/analysis_integrity.yml')
PAP = Path('analysis/preanalysis_plan.yml')
SPEC_SPACE = Path('analysis/spec_space.yml')
SPEC_RUN_INDEX = Path('analysis/spec_run_index.csv')
DEVIATION_LOG = Path('analysis/deviation_log.yml')
RESULT_INDEX = Path('evidence/result_index.csv')
REQUIRED_SPEC_COLUMNS = ['spec_id','run_id','mode','preplanned','registered_result','result_id','script_or_source','output_path','status','selection_reason','deviation_ref']


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return data if isinstance(data, dict) else {}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    if not PAP.exists() and not SPEC_SPACE.exists() and not SPEC_RUN_INDEX.exists():
        print('PASS: analysis ledger inactive (no analysis artifacts yet)')
        return 0
    failures: list[str] = []
    if not PAP.exists():
        failures.append('analysis/preanalysis_plan.yml missing while analysis ledger is active')
    if not SPEC_SPACE.exists():
        failures.append('analysis/spec_space.yml missing while analysis ledger is active')
    if not SPEC_RUN_INDEX.exists():
        failures.append('analysis/spec_run_index.csv missing while analysis ledger is active')
    pap = _load(PAP)
    if pap:
        if str(pap.get('status','')).strip() == 'locked' and not str(pap.get('locked_at','')).strip():
            failures.append('locked preanalysis_plan requires locked_at')
        if str(pap.get('claim_mode','')).strip() not in {'confirmatory','exploratory'}:
            failures.append('preanalysis_plan claim_mode must be confirmatory or exploratory')
    rows = _read_csv(SPEC_RUN_INDEX)
    if SPEC_RUN_INDEX.exists():
        with SPEC_RUN_INDEX.open(newline='', encoding='utf-8') as handle:
            header = csv.DictReader(handle).fieldnames or []
        for col in REQUIRED_SPEC_COLUMNS:
            if col not in header:
                failures.append(f'spec_run_index missing required column: {col}')
    registered = [r for r in rows if str(r.get('registered_result','')).strip().lower() in {'true','yes','1'} or str(r.get('result_id','')).strip()]
    result_rows = _read_csv(RESULT_INDEX)
    result_ids = {str(r.get('result_id','')).strip() for r in result_rows if str(r.get('result_id','')).strip()}
    registered_ids = {str(r.get('result_id','')).strip() for r in registered if str(r.get('result_id','')).strip()}
    for rid in result_ids:
        if rid and rid not in registered_ids:
            failures.append(f'result_index result {rid} is not represented as registered in spec_run_index')
    if rows:
        share = len(registered) / len(rows)
        policy = _load(POLICY)
        signals = policy.get('specification_search_signals', {}) if isinstance(policy, dict) else {}
        fail_below = float(signals.get('registered_share_fail_below', 0.05))
        if share < fail_below:
            failures.append(f'registered result share too low: {len(registered)}/{len(rows)}')
        for row in rows:
            mode = str(row.get('mode','')).strip()
            preplanned = str(row.get('preplanned','')).strip().lower() in {'true','yes','1'}
            deviation = str(row.get('deviation_ref','')).strip()
            if mode == 'confirmatory' and not preplanned and not deviation:
                failures.append(f"{row.get('spec_id','(missing)')}: confirmatory non-preplanned spec requires deviation_ref")
            if str(row.get('selection_reason','')).strip().lower() in {'significant','p<0.05','best result'}:
                failures.append(f"{row.get('spec_id','(missing)')}: selection_reason cannot be significance-only")
    if failures:
        print('FAIL: analysis ledger problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: analysis ledger valid ({len(rows)} spec run(s), {len(registered)} registered result(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
