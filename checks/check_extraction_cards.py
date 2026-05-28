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
    "## Inclusion Decision",
    "## Content Summary",
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
SUMMARY_HEADINGS = [
    "## Full Citation",
    "## Inclusion Decision",
    "## Content Summary",
    "## Research Question",
    "## Main Findings",
    "## Relevance To This Project",
    "## Direct Evidence Notes",
    "## Opened Source",
]
PLACEHOLDERS = {"", "tbd", "todo", "not stated", "unknown", "n/a", "na"}


def missing_headings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [heading for heading in REQUIRED_HEADINGS if heading not in text]


def section_text(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    start += len(heading)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        next_heading = len(text)
    return text[start:next_heading].strip()


def has_substantive_content(value: str) -> bool:
    lines = [line.strip(" |-:\t") for line in value.splitlines()]
    words = [line for line in lines if line and line.lower() not in PLACEHOLDERS]
    return bool(words)


def missing_summary_content(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [
        heading
        for heading in SUMMARY_HEADINGS
        if not has_substantive_content(section_text(text, heading))
    ]


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
                if row.get("status", "").strip() in {"extracted", "included"}:
                    missing_content = missing_summary_content(card)
                    if missing_content:
                        failures.append(f"{card}: missing substantive summary content under {missing_content}")

    if failures:
        print("FAIL: extraction card problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: extraction card template and registry-linked cards are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
