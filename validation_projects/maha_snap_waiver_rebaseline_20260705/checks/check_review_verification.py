#!/usr/bin/env python3
"""Enforce the skill-review verification gate mechanically.

The econometric review skills (code-review-econ, causal-id-review, etc.) may
grade a data-dependent finding HIGH/MED only after checking it on the real data.
This check turns that discipline into a gate: in any review report under
`audits/skill_runs/`, a finding that (a) carries a HIGH/MED severity grade AND
(b) mentions a data-dependent concept (missingness, convergence, separation,
collinearity, overlap/balance, merge match) MUST also carry a verification
marker — `(checked)`, `(verified)`, an explicit number/percent, `UNVERIFIED`, or
`NOT RUN`. Code-only findings (no data keyword) are never flagged.

It cannot verify the number is correct; it enforces that a data-dependent
severity claim is not made without an explicit verification status — exactly the
discipline whose absence let an associational OLS finding be graded HIGH from the
code pattern alone. PASS if the review dir is absent (skill not used here).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REVIEW_DIR = Path("audits/skill_runs")

# Severity graded in a finding position: "(HIGH)", "(LOW-MED)", "— MED", "MED —".
SEVERITY = re.compile(r"\((?:[^)]*\b(?:HIGH|MED|MEDIUM)\b[^)]*)\)|(?:—|--)\s*(?:HIGH|MED|MEDIUM)\b|\b(?:HIGH|MED|MEDIUM)\b\s*(?:—|--)")
# Data-dependent concepts (must be checked on real data before grading).
DATA_KEYWORDS = re.compile(
    r"(missing\w*|impute\w*|imputation|fillna|converg\w*|separat\w*|"
    r"collinear\w*|zero[- ]?variance|overlap\w*|imbalanc\w*|balance test|unmatched|"
    r"duplicate\w*|match diagnost\w*|\bmerge\w*|drops? rows|dropped observ\w*)",
    re.I,
)
# Acceptable verification markers.
VERIFIED = re.compile(r"\(checked\)|\(verified\)|\bUNVERIFIED\b|\bNOT[ -]?RUN\b|\d+(?:\.\d+)?\s*%|n\s*=\s*\d|\bp\s*=|\bp<|0%", re.I)

# Lines that are gate documentation, not findings.
SKIP_LINE = re.compile(r"verification gate|MANDATORY|data-dependent finding|cheap check", re.I)


def _is_finding(line: str) -> bool:
    s = line.lstrip()
    return bool(re.match(r"(\d+\.|[-*])\s", s) or "**" in line)


def main() -> int:
    if not REVIEW_DIR.exists():
        print("PASS: no audits/skill_runs review reports (review skills not in use here)")
        return 0
    failures: list[str] = []
    n_reports = 0
    for path in sorted(REVIEW_DIR.rglob("*.md")):
        n_reports += 1
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if SKIP_LINE.search(raw) or not _is_finding(raw):
                continue
            if not SEVERITY.search(raw):
                continue
            if not DATA_KEYWORDS.search(raw):
                continue  # code-only finding — no data check required
            if not VERIFIED.search(raw):
                failures.append(f"{path}:{i}: HIGH/MED data-dependent finding lacks a "
                                f"verification marker ((checked)/UNVERIFIED/NOT RUN/number): {raw.strip()[:90]}")
    if failures:
        print("FAIL: review findings graded without verification:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASS: data-dependent review findings carry verification markers ({n_reports} report(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
