#!/usr/bin/env python3
"""Validate the AEROS research graph against source registries.

The graph is observe-and-flag only. This check verifies relationship integrity;
it never mutates claim status, approvals, gate status, or runtime state.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.research_graph import validate_graph  # noqa: E402

CHECK_NAME = "check_research_graph"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    failures = validate_graph(Path.cwd())
    if args.json:
        print(json.dumps({"check": CHECK_NAME, "status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: research graph problems detected:")
        for failure in failures:
            print(f"  - {failure}")
        print("This check only flags relationship drift; it does not downgrade claims or gates.")
    else:
        print("PASS: research graph relationships are consistent")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
