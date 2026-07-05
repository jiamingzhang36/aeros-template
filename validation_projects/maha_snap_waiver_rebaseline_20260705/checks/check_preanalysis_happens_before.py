#!/usr/bin/env python3
"""Check preregistration happens-before outcome access/spec execution events."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.kernel.event_replay import check_happens_before  # noqa: E402
from aeros.kernel.events import read_events  # noqa: E402


def main() -> int:
    root = Path.cwd()
    if not read_events(root):
        print('PASS: preregistration happens-before inactive (no event log yet)')
        return 0
    failures = check_happens_before(root)
    if failures:
        print('FAIL: preregistration happens-before violations detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print('PASS: preregistration happens-before constraints hold')
    return 0

if __name__ == '__main__':
    sys.exit(main())
