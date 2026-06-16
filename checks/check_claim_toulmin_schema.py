#!/usr/bin/env python3
"""Validate optional Toulmin-style claim cards."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

CARD_DIRS = [Path('evidence/claims'), Path('claims')]
VALID_TYPES = {'descriptive','associational','causal','methodological','feasibility'}
VALID_MODES = {'confirmatory','exploratory'}
VALID_STRENGTH = {'unsupported','ambiguous','supported','contradicted'}
SCOPE_FIELDS = {'geography','time_period','population','industry','unit','data_source','measurement_level','claim_type'}
HIGH_RISK_GATE_CLASSES = {'claim_gate','override_gate'}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    cards = []
    for directory in CARD_DIRS:
        if directory.exists():
            cards.extend(sorted(directory.glob('*.yml')))
    if not cards:
        print('PASS: Toulmin claim cards inactive (no claim cards yet)')
        return 0
    failures: list[str] = []
    for path in cards:
        try:
            data = _load(path)
        except yaml.YAMLError as exc:
            failures.append(f'{path}: unreadable claim card ({exc})')
            continue
        cid = str(data.get('claim_id') or path.stem)
        if not str(data.get('claim_text','')).strip():
            failures.append(f'{cid}: missing claim_text')
        if str(data.get('claim_type','')).strip() not in VALID_TYPES:
            failures.append(f'{cid}: invalid claim_type')
        if str(data.get('mode','')).strip() not in VALID_MODES:
            failures.append(f'{cid}: invalid mode')
        strength = str(data.get('strength','')).strip()
        if strength not in VALID_STRENGTH:
            failures.append(f'{cid}: invalid strength')
        qualifier = data.get('qualifier')
        scope = data.get('scope')
        if not isinstance(scope, dict):
            failures.append(f'{cid}: missing scope vector')
            scope = {}
        missing_scope = sorted(field for field in SCOPE_FIELDS if field not in scope)
        if missing_scope:
            failures.append(f'{cid}: scope missing field(s): {missing_scope}')
        if str(scope.get('claim_type','')).strip() and str(scope.get('claim_type','')).strip() != str(data.get('claim_type','')).strip():
            failures.append(f'{cid}: scope.claim_type must match claim_type')
        if strength in {'ambiguous','supported'} and not qualifier:
            failures.append(f'{cid}: ambiguous/supported claim requires qualifier')
        if str(data.get('claim_type','')).strip() == 'causal' and not data.get('rebuttal'):
            failures.append(f'{cid}: causal claim requires rebuttal/threats')
        if data.get('contradicted_by') and strength == 'supported':
            failures.append(f'{cid}: claim with contradicted_by cannot be supported until rebuttal resolved')
        mode = str(data.get('mode','')).strip()
        if mode == 'exploratory' and strength == 'supported':
            gate_class = str(data.get('human_gate_class','')).strip()
            if gate_class not in HIGH_RISK_GATE_CLASSES:
                failures.append(f'{cid}: exploratory claim cannot be supported without claim/override gate')
        compiler = data.get('compiler_output') or {}
        if not isinstance(compiler, dict):
            failures.append(f'{cid}: compiler_output must be a mapping')
        elif compiler.get('scope_overreach') and str(data.get('human_gate_class','')).strip() not in HIGH_RISK_GATE_CLASSES:
            failures.append(f'{cid}: scope_overreach requires claim_gate or override_gate before release')
    if failures:
        print('FAIL: Toulmin claim schema problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: Toulmin claim cards valid ({len(cards)} card(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
