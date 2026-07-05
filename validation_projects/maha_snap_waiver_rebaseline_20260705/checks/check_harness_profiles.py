#!/usr/bin/env python3
"""Validate check profile configuration."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from checks.run_harness_checks import CHECKS  # noqa: E402


def main() -> int:
    path = ROOT / "harness/check_profiles.yml"
    failures: list[str] = []
    if not path.exists():
        failures.append("missing harness/check_profiles.yml")
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        profiles = data.get("profiles") or {}
        for required in ["smoke", "lane:data", "lane:literature", "lane:method", "lane:claim", "lane:writing", "lane:compliance", "full"]:
            if required not in profiles:
                failures.append(f"missing profile {required}")
        known = set(CHECKS)
        for name, spec in profiles.items():
            checks = (spec or {}).get("checks")
            if checks == "all":
                continue
            if not isinstance(checks, list) or not checks:
                failures.append(f"profile {name}: checks must be a nonempty list or 'all'")
                continue
            for check in checks:
                if check not in known:
                    failures.append(f"profile {name}: unknown check {check}")
                if not (ROOT / "checks" / check).exists():
                    failures.append(f"profile {name}: missing file checks/{check}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: check profiles are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
