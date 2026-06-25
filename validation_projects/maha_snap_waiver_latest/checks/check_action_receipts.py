#!/usr/bin/env python3
"""Validate action receipts so hygiene cannot masquerade as research progress."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.action_receipt import validate_action_receipts  # noqa: E402


def main() -> int:
    failures = validate_action_receipts(Path.cwd())
    if failures:
        print("FAIL: action receipt problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: action receipts are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
