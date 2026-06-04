#!/usr/bin/env python3
"""Verify the SHA256 artifact manifest matches current result artifacts.

Passes when no manifest exists yet (opt-in; safe on a fresh template). When a
manifest is present, every listed artifact must still hash to its recorded
SHA256 -- otherwise an output changed since it was snapshotted, which breaks the
script -> artifact -> paper-number chain. Regenerate with `aeros manifest`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
CHECK_NAME = "check_artifact_manifest"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    try:
        from aeros.runtime.artifact_manifest import MANIFEST, verify_manifest
    except Exception as exc:  # noqa: BLE001
        msg = f"could not import artifact_manifest: {exc}"
        print(json.dumps({"check": CHECK_NAME, "status": "fail", "failures": [msg]}) if as_json
              else f"FAIL: {msg}")
        return 1

    root = Path.cwd()
    if not (root / MANIFEST).exists():
        if as_json:
            print(json.dumps({"check": CHECK_NAME, "status": "pass", "failures": []}))
        else:
            print("PASS: no artifact manifest yet (run `aeros manifest` to snapshot)")
        return 0

    problems = verify_manifest(root)
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": "fail" if problems else "pass",
                          "failures": problems}))
    elif problems:
        print("FAIL: artifact manifest drift detected:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("PASS: all manifested artifacts match their recorded SHA256")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
