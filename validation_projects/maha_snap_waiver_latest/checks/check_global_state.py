#!/usr/bin/env python3
"""Validate the derived global state index if present."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.global_state import validate_global_state  # noqa: E402


def main() -> int:
    failures = validate_global_state(Path.cwd())
    if failures:
        print("FAIL: global state problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: global state is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
