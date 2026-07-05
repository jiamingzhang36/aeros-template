#!/usr/bin/env python3
"""Adversarial fixture: register a stronger claim than the earned ceiling."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root)
    (root / "discovery").mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    (root / "discovery/design_selection.md").write_text(
        """---
earned_claim_ceiling: associational
diagnostics_status: measured
---

# Adversarial design selection
""",
        encoding="utf-8",
    )
    (root / "evidence/claim_registry.md").write_text(
        """| Claim ID | Claim | Type | Status | Evidence ID(s) | Result ID(s) | Boundary / Limitation | Approved |
|---|---|---|---|---|---|---|---|
| C_ADV | A caused B. | causal | Supported | EV_ADV | R_ADV | none | jiaming (2026-06-23) |
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
