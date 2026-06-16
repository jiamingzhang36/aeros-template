#!/usr/bin/env python3
"""Validate event log replay determinism and content-addressed events."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.kernel.event_replay import replay  # noqa: E402
from aeros.kernel.events import read_events  # noqa: E402


def main() -> int:
    root = Path.cwd()
    events = read_events(root)
    if not events:
        print('PASS: event log inactive (no events/event_log.jsonl yet)')
        return 0
    state1 = replay(root)
    state2 = replay(root)
    failures = list(state1.violations)
    if state1.digest != state2.digest:
        failures.append('event replay is not deterministic')
    for event in events:
        for key, refs in [('input', event.inputs), ('output', event.outputs)]:
            for ref in refs:
                if not isinstance(ref, dict):
                    failures.append(f'{event.event_id}: {key} ref is not content-addressed mapping')
                    continue
                if 'path' not in ref or 'sha256' not in ref or 'bytes' not in ref or 'exists' not in ref:
                    failures.append(f'{event.event_id}: {key} ref missing path/sha256/bytes/exists')
    if failures:
        print('FAIL: event log replay problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: event log replay deterministic ({state1.event_count} event(s), digest={state1.digest[:12]})')
    return 0

if __name__ == '__main__':
    sys.exit(main())
