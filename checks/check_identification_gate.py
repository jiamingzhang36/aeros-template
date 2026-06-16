#!/usr/bin/env python3
"""Validate optional identification gate cards before strong empirical claims."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

POLICY = Path('harness/analysis_integrity.yml')
GATE_DIRS = [Path('analysis/identification'), Path('audits/identification')]


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    cards = []
    for directory in GATE_DIRS:
        if directory.exists():
            cards.extend(sorted(directory.glob('*.yml')))
    if not cards:
        print('PASS: identification gate inactive (no identification cards yet)')
        return 0
    policy = _load(POLICY)
    checks = policy.get('identification_checks', {}) if isinstance(policy, dict) else {}
    failures: list[str] = []
    for path in cards:
        try:
            data = _load(path)
        except yaml.YAMLError as exc:
            failures.append(f'{path}: unreadable identification card ({exc})')
            continue
        cid = str(data.get('claim_id') or path.stem)
        claim_type = str(data.get('claim_type','')).strip() or 'descriptive'
        required = checks.get(claim_type, {}).get('required', []) if isinstance(checks.get(claim_type, {}), dict) else []
        for field in required:
            if data.get(field) is not True:
                failures.append(f'{cid}: {claim_type} identification gate requires {field}: true')
        verdict = str(data.get('verdict','')).strip()
        if verdict == 'passed' and failures:
            failures.append(f'{cid}: verdict cannot be passed while required fields are missing')
        if claim_type == 'causal' and not data.get('qualifier_updates'):
            failures.append(f'{cid}: causal identification gate must provide qualifier_updates')
    if failures:
        print('FAIL: identification gate problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: identification gates valid ({len(cards)} card(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
