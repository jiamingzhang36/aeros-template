#!/usr/bin/env python3
"""Validate the derived readiness vector."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.readiness import build_readiness_vector  # noqa: E402


REQUIRED_KEYS = {"data", "literature", "analysis", "claims", "paper", "compliance", "release"}


def main() -> int:
    vector = build_readiness_vector(Path.cwd())
    readiness = vector.get("readiness") or {}
    missing = REQUIRED_KEYS - set(readiness)
    if missing:
        print("FAIL: readiness vector missing keys:")
        for key in sorted(missing):
            print(f"- {key}")
        return 1
    if "does_not_prove" not in vector:
        print("FAIL: readiness vector missing does_not_prove")
        return 1
    print("PASS: readiness vector is derivable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
