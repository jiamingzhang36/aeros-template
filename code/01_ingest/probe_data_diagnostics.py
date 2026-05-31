#!/usr/bin/env python3
"""Project-specific data diagnostics probe template.

Instantiate this script for a concrete project. It should write
`discovery/data_diagnostics.yml` with `status: measured` and a dictionary of
numeric diagnostics used by `discovery/design_options.md` viability tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "discovery" / "data_diagnostics.yml"


def main() -> int:
    payload = {
        "status": "draft",
        "measured_on": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "code/01_ingest/probe_data_diagnostics.py",
        "diagnostics": {},
        "notes": {
            "template": (
                "Replace this scaffold with project-specific probes, then set "
                "status: measured and populate numeric diagnostics."
            )
        },
    }
    OUT.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"wrote template diagnostics scaffold -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
