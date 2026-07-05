#!/usr/bin/env python3
"""Validate the derived-vs-asserted attack surface audit."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

AUDIT = Path('harness/derived_vs_asserted_audit.yml')
REQUIRED = {'progress_label','spec_run_index','qualifier','rebuttal','contradicted_by','claim_ceiling','claim_type'}


def main() -> int:
    if not AUDIT.exists():
        print(f'FAIL: missing {AUDIT}')
        return 1
    data = yaml.safe_load(AUDIT.read_text(encoding='utf-8')) or {}
    fields = data.get('fields', {}) if isinstance(data, dict) else {}
    failures = []
    for field in sorted(REQUIRED - set(fields)):
        failures.append(f'missing audit field: {field}')
    for name, meta in fields.items() if isinstance(fields, dict) else []:
        if not isinstance(meta, dict):
            failures.append(f'{name}: audit entry must be a mapping')
            continue
        for key in ['current_status','target_status','derive_from','risk']:
            if key not in meta:
                failures.append(f'{name}: missing {key}')
    if failures:
        print('FAIL: derived-vs-asserted audit problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: derived-vs-asserted audit valid ({len(fields)} field(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
