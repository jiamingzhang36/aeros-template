#!/usr/bin/env python3
"""Check that the paper package draft is audit-ready without overclaiming.

This check derives its expectations from the project (the active claims in the
claim registry, the registered manuscript) rather than hardcoding a specific
demo project's claim IDs or domain vocabulary. Overclaim detection is
negation-aware: a descriptive paper that explicitly says it does NOT identify a
causal effect is being careful, not overclaiming, and must not be flagged.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


PAPER_DRAFT = Path("paper/draft.md")
CLAIM_REGISTRY = Path("evidence/claim_registry.md")
REPLICATION_REPORT = Path("audits/replication_package_report.md")

REQUIRED_SECTION_PATTERNS = {
    "research question": r"^##\s+.*(research question|question)",
    "design": r"^##\s+.*(design|method)",
    "evidence/results": r"^##\s+.*(evidence|results|findings)",
    "claim boundary": r"^##\s+.*(claim|boundary|claim ceiling)",
    "limitations": r"^##\s+.*(limitation|scope)",
    "replication": r"^##\s+.*(replication|reproducibility)",
}

# Generic overclaim guards for an empirical paper. Domain-specific terms are NOT
# hardcoded here; they belong in a project's own language_constraints. Each match
# is negation-checked before being flagged.
OVERCLAIM_PATTERNS = [
    r"\bproves?\b",
    r"\bcausal effects?\b",
    r"\bcausally\b",
]
# A match preceded (within a short window) by one of these is a bounded
# disclaimer ("does not identify a causal effect"), not an overclaim.
NEGATORS = re.compile(
    r"\b(not|no|never|without|cannot|can't|isn't|aren't|doesn't|does not|do not|"
    r"rather than|neither|nor|preclude[sd]?|avoid(?:s|ed)?)\b",
    flags=re.I,
)

# Evidence that the replication package preserves a "release is not yet approved"
# boundary -- accept any of these, not one exact phrase.
RELEASE_BOUNDARY_MARKERS = [
    "not public", "not yet release-ready", "not approved", "not release-ready",
    "release blocker", "human approval is required", "before final replication release",
    "before release", "release-approval", "approval-required",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _template_mode() -> bool:
    manifest = Path("project_manifest.yml")
    if not manifest.exists():
        return False
    text = manifest.read_text(encoding="utf-8", errors="replace").lower()
    return "project_mode: template" in text or "name: aeros project" in text


def _nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _active_claim_ids(claim_registry: str) -> list[str]:
    """Claim IDs from registry table rows whose Status is not draft/retired."""
    ids: list[str] = []
    for line in claim_registry.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        cid, status = cells[0], cells[3].lower()
        if re.fullmatch(r"C\d+", cid) and status not in {"draft", "retired", ""}:
            ids.append(cid)
    return ids


def _overclaims(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in OVERCLAIM_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.I):
            window = text[max(0, m.start() - 40):m.start()]
            if NEGATORS.search(window):
                continue  # bounded disclaimer, not an overclaim
            hits.append(pattern)
            break
    return hits


def main() -> int:
    if _template_mode():
        print("PASS: paper package check inactive in template mode")
        return 0

    failures: list[str] = []

    if not PAPER_DRAFT.exists():
        failures.append(f"missing {PAPER_DRAFT}")
    if not CLAIM_REGISTRY.exists():
        failures.append(f"missing {CLAIM_REGISTRY}")
    if not REPLICATION_REPORT.exists():
        failures.append(f"missing {REPLICATION_REPORT}")

    draft = _read(PAPER_DRAFT)
    claim_registry = _read(CLAIM_REGISTRY)
    replication_report = _read(REPLICATION_REPORT)

    if PAPER_DRAFT.exists() and _nonempty_lines(draft) < 20:
        failures.append(f"{PAPER_DRAFT}: draft is too short for a paper package checkpoint")

    for label, pattern in REQUIRED_SECTION_PATTERNS.items():
        if not re.search(pattern, draft, flags=re.I | re.M):
            failures.append(f"{PAPER_DRAFT}: missing section for {label}")

    # The registry must declare at least one active claim, and the draft must
    # reference one of those actual claim IDs (derived, not hardcoded).
    active_ids = _active_claim_ids(claim_registry)
    if claim_registry and not active_ids:
        failures.append(f"{CLAIM_REGISTRY}: no active claim rows found")
    elif active_ids and not any(re.search(rf"\b{cid}\b", draft) for cid in active_ids):
        failures.append(
            f"{PAPER_DRAFT}: draft should reference at least one active claim ID "
            f"({', '.join(active_ids)})"
        )

    if draft and ("not" not in draft.lower() or "final" not in draft.lower()):
        failures.append(f"{PAPER_DRAFT}: draft should explicitly avoid final-claim language")

    for pattern in _overclaims(draft):
        failures.append(f"{PAPER_DRAFT}: possible unbounded claim matched /{pattern}/")

    if replication_report and not any(
        m in replication_report.lower() for m in RELEASE_BOUNDARY_MARKERS
    ):
        failures.append(
            f"{REPLICATION_REPORT}: should preserve the boundary that public release is not approved"
        )

    if failures:
        print("FAIL: paper package problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: paper package draft is audit-ready and bounded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
