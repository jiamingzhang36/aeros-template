#!/usr/bin/env python3
"""Circuit-breaker meta-monitor for repeated failures, exceptions, and degraded autonomy."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

PROBE_ROOT = Path('data/probes')
EXCEPTION_DIRS = [Path('decisions/exceptions'), Path('evidence/exceptions'), Path('data/exceptions'), Path('analysis/exceptions')]
THRESHOLDS = {
    'probe_failed_open_circuit': 3,
    'exception_count_open_circuit': 5,
}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    probe_failed = 0
    if PROBE_ROOT.exists():
        for path in PROBE_ROOT.glob('*/probe_metadata.yml'):
            try:
                data = _load(path)
            except yaml.YAMLError:
                continue
            if data.get('probe_verdict') == 'failed':
                probe_failed += 1
    exceptions = []
    for directory in EXCEPTION_DIRS:
        if directory.exists():
            exceptions.extend(sorted(directory.glob('*.yml')))
    failures: list[str] = []
    if probe_failed >= THRESHOLDS['probe_failed_open_circuit']:
        failures.append(f'circuit breaker OPEN: {probe_failed} failed probes; require human triage before further autonomous collection')
    if len(exceptions) >= THRESHOLDS['exception_count_open_circuit']:
        failures.append(f'circuit breaker OPEN: {len(exceptions)} exceptions; require human review of exception budget')
    if failures:
        print('FAIL: meta-monitor circuit breaker triggered:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: meta-monitor closed ({probe_failed} failed probe(s), {len(exceptions)} exception(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
