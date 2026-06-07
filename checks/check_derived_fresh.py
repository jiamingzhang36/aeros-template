#!/usr/bin/env python3
"""Derived artifacts must be fresh w.r.t. their sources (B2).

Each derived file under evidence/derived/ that was stamped by its generator has a
<output>.sources.json sidecar recording the sha256 of every source it read. This
check recomputes those hashes; if a source changed since the derived file was
generated, the derived file (and any number injected from it) is stale and the
generator must be re-run. Passes cleanly when there are no sidecars.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.derived import check_freshness  # noqa: E402

CHECK_NAME = "check_derived_fresh"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    problems = check_freshness(Path.cwd())
    status = "fail" if problems else "pass"
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": problems}))
    elif problems:
        print("FAIL: stale derived artifacts (regenerate):")
        for p in problems:
            print(f"  - {p}")
    else:
        print("PASS: all derived artifacts are fresh w.r.t. their sources")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
