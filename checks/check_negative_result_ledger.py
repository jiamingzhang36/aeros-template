#!/usr/bin/env python3
"""Ensure all spec runs have terminal status, including failed/null/abandoned runs."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

SPEC_RUN_INDEX = Path('analysis/spec_run_index.csv')
NEGATIVE = Path('analysis/negative_result_ledger.csv')
TERMINAL = {'completed','failed_runtime','failed_validation','invalid_design','abandoned_with_reason','superseded'}


def _rows(path: Path) -> list[dict[str,str]]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    spec_rows = _rows(SPEC_RUN_INDEX)
    neg_rows = _rows(NEGATIVE)
    if not spec_rows and not neg_rows:
        print('PASS: negative result ledger inactive (no spec runs yet)')
        return 0
    failures: list[str] = []
    neg_keys = {(r.get('spec_id',''), r.get('run_id','')) for r in neg_rows}
    for row in spec_rows:
        key = (row.get('spec_id',''), row.get('run_id',''))
        status = row.get('status','').strip()
        registered = row.get('registered_result','').strip().lower() in {'true','yes','1'} or bool(row.get('result_id','').strip())
        if status not in TERMINAL:
            failures.append(f'{key}: status must be terminal {sorted(TERMINAL)}')
        if not registered and status != 'completed' and key not in neg_keys:
            failures.append(f'{key}: non-registered non-completed run must appear in negative_result_ledger')
    for row in neg_rows:
        if row.get('terminal_status','').strip() not in TERMINAL:
            failures.append(f"negative ledger {row.get('spec_id','')}/{row.get('run_id','')}: invalid terminal_status")
        if not row.get('reason','').strip():
            failures.append(f"negative ledger {row.get('spec_id','')}/{row.get('run_id','')}: missing reason")
    if failures:
        print('FAIL: negative/failed result ledger problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: negative result ledger valid ({len(spec_rows)} spec run(s), {len(neg_rows)} negative row(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
