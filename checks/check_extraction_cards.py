#!/usr/bin/env python3
"""Check extraction-card template and registry-linked extraction cards."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


REGISTRY = Path("discovery/literature/paper_registry.csv")
CARDS_DIR = Path("discovery/literature/extraction_cards")
REQUIRED_HEADINGS = [
    "## Full Citation",
    "## Full Text Status",
    "## Literature Function",
    "## Research Question",
    "## Data",
    "## Treatment / Exposure / Shock",
    "## Outcomes",
    "## Method / Identification",
    "## Key Assumptions",
    "## Main Findings",
    "## Limitations",
    "## What The Paper Does Not Claim",
    "## Direct Evidence Notes",
]


def missing_headings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [heading for heading in REQUIRED_HEADINGS if heading not in text]


def main() -> int:
    failures: list[str] = []
    template = CARDS_DIR / "TEMPLATE_extraction_card.md"
    if not template.exists():
        failures.append(f"missing {template}")
    else:
        missing = missing_headings(template)
        if missing:
            failures.append(f"{template}: missing headings {missing}")

    if REGISTRY.exists():
        with REGISTRY.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                paper_id = row.get("paper_id", "").strip()
                if not paper_id:
                    continue
                if row.get("extraction_card", "").strip() != "yes":
                    continue
                card = CARDS_DIR / f"{paper_id}.md"
                if not card.exists():
                    failures.append(f"{paper_id}: registry says extraction_card=yes but {card} is missing")
                    continue
                missing = missing_headings(card)
                if missing:
                    failures.append(f"{card}: missing headings {missing}")

    if failures:
        print("FAIL: extraction card problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: extraction card template and registry-linked cards are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
