#!/usr/bin/env python3
"""Validate the architecture-freeze baseline document."""

from __future__ import annotations

from pathlib import Path
import sys


PATH = Path("docs/design/architecture_freeze_v1.md")
REQUIRED_MARKERS = [
    "AEROS does not decide what is true",
    "Five-layer model",
    "Feature admission rule",
    "Do-not-expand list",
    "ExecutionEnvelope must be real confinement",
    "observed writes are a subset of declared writes",
    "ClaimVector v1 is allowed only as an advisory language-boundary compiler",
    "Automatic reconcile is deferred until ResultRecord and ResultAdmission",
    "control_plane_action_ratio",
]


def main() -> int:
    if not PATH.exists():
        print(f"FAIL: missing {PATH}")
        return 1
    text = PATH.read_text(encoding="utf-8")
    failures = [f"{PATH}: missing marker {marker!r}" for marker in REQUIRED_MARKERS if marker not in text]
    if failures:
        print("FAIL: architecture freeze document is incomplete:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: architecture freeze baseline is recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
