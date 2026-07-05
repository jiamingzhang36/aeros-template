#!/usr/bin/env python3
"""Citation Risk Radar — read-only advisory behind `aeros drive --goal citation-risk`.

Ranks manuscript author-year citations by how weakly they are backed: cited
sources absent from the paper registry, or matched but without full-text
grounding, with claim-bearing sentences escalated. This is advisory: it always
exits 0. It surfaces submission risk; it does not certify claims or approve
anything. A ledgered fixture keeps the parser honest across template changes.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aeros.runtime.citation_radar import build_citation_radar, format_citation_radar  # noqa: E402


def _fixture_ok() -> tuple[bool, list[str]]:
    """A grounded claim cite must not flag; an unregistered claim cite must flag."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_citation_radar_") as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "docs/manuscript").mkdir(parents=True)
        (tmp / "discovery/literature").mkdir(parents=True)
        (tmp / "docs/manuscript/paper_manuscript_draft.md").write_text(
            "We build on prior work (Alba and Wang 2024). "
            "An industry survey by Moran (2025) estimated a $1.6 billion cost.",
            encoding="utf-8",
        )
        (tmp / "discovery/literature/paper_registry.csv").write_text(
            "citation_key,title,authors,year,full_text_available,extraction_card\n"
            "alba2024,SSB restrictions,\"Alba, Charles and Wang, Xi\",2024,yes,extraction_card\n",
            encoding="utf-8",
        )
        res = build_citation_radar(tmp, top=12)
        if not res.active:
            failures.append(f"radar inactive on fixture: {res.reason}")
            return False, failures
        risks = {f["citation"] for f in res.findings}
        if not any("Moran" in r for r in risks):
            failures.append("expected unregistered claim cite 'Moran 2025' to be flagged")
        if any("Alba" in r for r in risks):
            failures.append("grounded cite 'Alba 2024' should not be a risk")
        if res.claim_bearing_at_risk < 1:
            failures.append("expected at least one claim-bearing at-risk citation")
    return not failures, failures


def main() -> int:
    ok, failures = _fixture_ok()
    if not ok:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    res = build_citation_radar(Path.cwd(), top=12)
    if not res.active:
        print(f"PASS: citation risk radar inactive ({res.reason})")
        return 0
    print(format_citation_radar(res))
    print(
        f"\nPASS: citation risk radar ran (advisory) — "
        f"{res.unknown} unknown-source, {res.ungrounded} ungrounded, "
        f"{res.claim_bearing_at_risk} claim-bearing at risk"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
