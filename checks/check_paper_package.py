#!/usr/bin/env python3
"""Check that the paper package draft is audit-ready without overclaiming."""

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

FORBIDDEN_UNBOUNDED_CLAIMS = [
    r"\bproves?\b",
    r"\bcausal effect\b",
    r"\ball (?:AI|grocery|recommendation)",
    r"\breal consumers?\b",
    r"\bdeployed AI systems?\b",
    r"\bnutrition fairness\b",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def main() -> int:
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

    draft_lower = draft.lower()
    if "c002" not in draft_lower:
        failures.append(f"{PAPER_DRAFT}: draft should reference the active claim ID C002")
    if "current-codex-session" not in draft_lower and "current codex-session" not in draft_lower:
        failures.append(
            f"{PAPER_DRAFT}: draft should state the current-Codex-session pilot boundary"
        )
    if "not" not in draft_lower or "final" not in draft_lower:
        failures.append(f"{PAPER_DRAFT}: draft should explicitly avoid final-claim language")

    for pattern in FORBIDDEN_UNBOUNDED_CLAIMS:
        if re.search(pattern, draft, flags=re.I):
            failures.append(f"{PAPER_DRAFT}: possible unbounded claim matched /{pattern}/")

    if claim_registry and "C002" not in claim_registry:
        failures.append(f"{CLAIM_REGISTRY}: active claim C002 not found")
    if replication_report and "not public" not in replication_report.lower() and "not yet release-ready" not in replication_report.lower():
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
