#!/usr/bin/env python3
"""Check preregistration happens-before outcome access/spec execution events."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.kernel.event_replay import (  # noqa: E402
    RETROSPECTIVE_PLAN_STATUSES,
    check_happens_before,
    preanalysis_plan_status,
)
from aeros.kernel.events import read_events  # noqa: E402


def main() -> int:
    root = Path.cwd()
    if not read_events(root):
        print('PASS: preregistration happens-before inactive (no event log yet)')
        return 0
    status, plan_id = preanalysis_plan_status(root)
    if status in RETROSPECTIVE_PLAN_STATUSES:
        # Not a violation, but never silent: the ordering guarantee does not
        # exist here and the report must say so rather than read as green.
        print(
            f'PASS (disclosed): analysis is retrospective, not preregistered '
            f'(plan {plan_id or "unnamed"}, status "{status}"). '
            'Happens-before ordering is not asserted; results carry no '
            'preregistration guarantee.'
        )
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
