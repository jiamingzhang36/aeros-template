#!/usr/bin/env python3
"""Gate-blocking: injected numbers that moved must be human-accepted (E).

Phase C surfaces drift in the decision packet (advisory). Phase E makes it bite:
if any injected number's source cell has moved (or no longer resolves) versus the
accepted lock (paper/numbers.lock.yml), this check FAILS, so a human gate cannot
pass while a headline coefficient has silently changed. The mechanical layer
detects; the human decides by reviewing and running:

    aeros number drift --update --owner <name> --note <why>

which advances the lock and appends an audit row to
decisions/number_acceptances.csv. Passes cleanly when there is nothing to track
(no registry / no lock) or every injected number matches the accepted lock.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.number_drift import compute_drift  # noqa: E402

CHECK_NAME = "check_number_drift"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    drifts = compute_drift(Path.cwd())
    failures: list[str] = []
    for d in drifts:
        if d.status == "changed":
            failures.append(
                f"{d.name}: source cell moved {d.baseline} -> {d.current}; review and "
                f"accept (aeros number drift --update --owner <name>)"
            )
        elif d.status == "new":
            failures.append(
                f"{d.name}: {d.current} not yet accepted into paper/numbers.lock.yml"
            )
        elif d.status == "unresolved":
            failures.append(f"{d.name}: source no longer resolves ({d.detail})")

    status = "fail" if failures else "pass"
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif failures:
        print("FAIL: injected numbers moved and need human acceptance:")
        for f in failures:
            print(f"  - {f}")
    else:
        print(f"PASS: all injected numbers match the accepted lock ({len(drifts)} tracked)")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
