#!/usr/bin/env python3
"""Validate two-layer funnel rounds (parallel-generate -> champion).

Passes when there are no funnels, or while a round is still open. Once a round is
status: selected, it must have >=2 candidates, exactly one champion among them, a
selection_criterion stated up front, a rationale, and the criterion must not be
statistical significance alone (guards against post-hoc selection bias).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
CHECK_NAME = "check_funnel"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    try:
        from aeros.runtime.funnel import FUNNEL_DIR, load_funnel, validate_selected
    except Exception as exc:  # noqa: BLE001
        out = [f"could not import funnel: {exc}"]
        print(json.dumps({"check": CHECK_NAME, "status": "fail", "failures": out}) if as_json
              else f"FAIL: {out[0]}")
        return 1

    root = Path.cwd()
    fdir = root / FUNNEL_DIR
    if not fdir.exists():
        print(json.dumps({"check": CHECK_NAME, "status": "pass", "failures": []}) if as_json
              else "PASS: no funnels yet")
        return 0

    failures: list[str] = []
    selected = 0
    for path in sorted(fdir.glob("*.yml")):
        funnel = load_funnel(path)
        if funnel.status == "selected":
            selected += 1
            for p in validate_selected(funnel):
                failures.append(f"{path.name}: {p}")

    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": "fail" if failures else "pass",
                          "failures": failures}))
    elif failures:
        print("FAIL: funnel selection problems detected:")
        for f in failures:
            print(f"  - {f}")
    else:
        print(f"PASS: {selected} selected funnel round(s) valid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
