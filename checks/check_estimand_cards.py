#!/usr/bin/env python3
"""Validate optional estimand cards."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

DIRS = [Path('analysis/estimands'), Path('evidence/estimands')]
REQUIRED = ['estimand_id','unit','population','treatment_or_exposure','comparison','outcome','time_horizon','target_parameter','interpretation']


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    cards = []
    for directory in DIRS:
        if directory.exists():
            cards.extend(sorted(directory.glob('*.yml')))
    if not cards:
        print('PASS: estimand cards inactive (no estimand cards yet)')
        return 0
    failures: list[str] = []
    for path in cards:
        try:
            data = _load(path)
        except yaml.YAMLError as exc:
            failures.append(f'{path}: unreadable estimand card ({exc})')
            continue
        eid = data.get('estimand_id') or path.stem
        for field in REQUIRED:
            if not str(data.get(field,'')).strip():
                failures.append(f'{eid}: missing {field}')
    if failures:
        print('FAIL: estimand card problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: estimand cards valid ({len(cards)} card(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
