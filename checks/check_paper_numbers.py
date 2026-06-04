#!/usr/bin/env python3
"""Anti-fabrication check: every reported number must trace to a verified result.

Motivation (triple-sourced): Team Paper Lite ("any number in the paper must trace
back to a result file, a log line, a script"); AutoResearchClaw's VerifiedRegistry
("unverified numbers sanitized"); and the empirical-research failure mode of
hallucinated numerical results (arXiv 2509.08713). This is a NON-LLM anchor: a
deterministic cross-reference the model cannot talk its way past.

What it does
------------
1. Verifies registered result paths exist (the original conservative behavior).
2. Scans the paper for estimate-like numbers (decimals and percentages -- high
   signal, low false positive) and requires each to either:
     - match a numeric value found in a registered result artifact (within the
       paper's stated rounding precision), or
     - appear in an explicit allow-list (paper/number_whitelist.txt) for
       legitimately non-result numbers (declared N, constants, thresholds).
   Otherwise the number is flagged as unverified / possibly fabricated.

It stays quiet when there is no real paper yet (template default passes).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

RESULT_INDEX = Path("evidence/result_index.csv")
PAPER_FILES = [Path("paper/draft.md")]
PAPER_GLOBS = [("paper", "*.tex"), ("paper", "*.md")]
WHITELIST = Path("paper/number_whitelist.txt")
CHECK_NAME = "check_paper_numbers"

# Estimate-like tokens: signed decimals (0.34, -1.2) and percentages (12.5%, 9%).
NUMBER_RE = re.compile(r"(?<![\w.])([-+]?\d+\.\d+\s*%?|\d+\s*%)(?![\w])")
PLACEHOLDER_MARKERS = ("placeholder", "todo", "to be written", "draft skeleton")

# Cross-reference words: a number right after one of these is a label, not an
# estimate (e.g. "Table 3.2", "Figure 2.5", "Section 4.1", "Version 2.0").
REFERENCE_WORDS = {
    "table", "tables", "figure", "figures", "fig", "panel", "panels",
    "section", "sections", "sec", "subsection", "appendix", "appendices",
    "equation", "equations", "eq", "eqn", "column", "columns", "col", "row",
    "rows", "chapter", "version", "v", "step", "footnote", "note", "model",
    "models", "specification", "specifications", "spec", "no", "number",
    "page", "pp", "item", "line", "stage", "gate", "hypothesis",
}
_PREV_WORD_RE = re.compile(r"([A-Za-z]+)\.?\s*$")


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status, "failures": failures}))
    elif status == "pass":
        print(f"PASS: {note or 'paper numbers verified'}")
    else:
        print("FAIL: unverified numbers / result problems detected:")
        for f in failures:
            print(f"  - {f}")
    return 0 if status == "pass" else 1


def _paper_paths() -> list[Path]:
    found: list[Path] = []
    for base, pattern in PAPER_GLOBS:
        b = Path(base)
        if b.exists():
            found.extend(sorted(b.glob(pattern)))
    for p in PAPER_FILES:
        if p.exists() and p not in found:
            found.append(p)
    return [p for p in dict.fromkeys(found) if p.exists()]


def _load_whitelist() -> set[str]:
    if not WHITELIST.exists():
        return set()
    out: set[str] = set()
    for line in WHITELIST.read_text(encoding="utf-8").splitlines():
        token = line.split("#", 1)[0].strip().replace(" ", "")
        if token:
            out.add(token.rstrip("%"))
    return out


def _numeric_tokens(text: str) -> list[float]:
    vals: list[float] = []
    for m in re.finditer(r"[-+]?\d+(?:\.\d+)?", text):
        try:
            vals.append(float(m.group(0)))
        except ValueError:
            continue
    return vals


def _verified_values() -> list[float]:
    """All numeric values found in registered result artifact files."""
    values: list[float] = []
    if not RESULT_INDEX.exists():
        return values
    with RESULT_INDEX.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            path_value = (row.get("path") or "").strip()
            if not path_value:
                continue
            p = Path(path_value)
            if not p.exists() or not p.is_file():
                continue
            try:
                values.extend(_numeric_tokens(p.read_text(encoding="utf-8", errors="ignore")))
            except OSError:
                continue
    return values


def _matches(paper_num: str, verified: list[float], whitelist: set[str]) -> bool:
    raw = paper_num.replace(" ", "")
    bare = raw.rstrip("%")
    if bare in whitelist:
        return True
    try:
        value = float(bare)
    except ValueError:
        return True  # unparseable -> do not flag
    decimals = len(bare.split(".")[1]) if "." in bare else 0
    eps = 0.5 * (10 ** (-decimals)) + 1e-9
    for v in verified:
        # direct match (same representation)
        if abs(round(v, decimals) - round(value, decimals)) <= eps:
            return True
        # a percentage in the paper may be stored as a fraction in the artifact
        # (12.5%  <->  0.125): accept ONLY this one cross-form, not arbitrary x100.
        if raw.endswith("%") and abs(round(v * 100.0, decimals) - round(value, decimals)) <= eps:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    failures: list[str] = []

    # 1. Conservative: registered result paths must exist.
    populated = 0
    if RESULT_INDEX.exists():
        with RESULT_INDEX.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                path_value = (row.get("path") or "").strip()
                if not path_value:
                    continue
                populated += 1
                if not Path(path_value).exists():
                    failures.append(f"{row.get('result_id','?')}: registered output path missing: {path_value}")

    # 2. Anti-fabrication: scan the paper for estimate-like numbers.
    papers = _paper_paths()
    if not papers:
        return _emit(as_json, "pass" if not failures else "fail", failures,
                     note=f"no paper file yet; {populated} result path(s) checked")

    whitelist = _load_whitelist()
    verified = _verified_values()
    scanned_numbers = 0
    for paper in papers:
        text = paper.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text.lower() for marker in PLACEHOLDER_MARKERS) and not verified:
            continue  # placeholder draft, nothing to verify
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in NUMBER_RE.finditer(line):
                token = m.group(1).strip()
                prev = _PREV_WORD_RE.search(line[:m.start()])
                if prev and prev.group(1).lower() in REFERENCE_WORDS:
                    continue  # cross-reference label (Table 3.2, Figure 2.5), not an estimate
                scanned_numbers += 1
                if not _matches(token, verified, whitelist):
                    snippet = line.strip()[:80]
                    failures.append(
                        f"{paper}:{line_no}: '{token}' not traceable to any registered result "
                        f"or whitelist  | {snippet}"
                    )

    if failures:
        return _emit(as_json, "fail", failures)
    return _emit(as_json, "pass", [],
                 note=f"{scanned_numbers} reported number(s) trace to verified results "
                      f"({len(verified)} verified values, {populated} result path(s))")


if __name__ == "__main__":
    sys.exit(main())
