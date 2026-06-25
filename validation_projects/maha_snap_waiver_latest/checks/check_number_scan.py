#!/usr/bin/env python3
"""ADVISORY: scan the paper for estimate-like numbers that do not trace.

This is the noisy half of the old check_paper_numbers. On a real hand-written
paper the aggregate trace flags hundreds of perfectly legitimate numbers
(summary stats, coefficients, CI bounds) because it can only ask "does this
value appear somewhere in a registered file?", not "is this the right value
here?". That is a useful review aid but a terrible gate -- a noisy hard gate
either blocks forever or trains the author to ignore it (alarm fatigue).

So this check NEVER fails: it always returns status=pass and lists the
untraceable numbers under `warnings`. The reliable gate is check_number_registry
(cell-level injection). Drive the warning count down by converting numbers to
{{tokens}} sourced in paper/numbers.yml -- do not silence them by whitelisting.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.number_injection import (  # noqa: E402
    load_whitelist,
    matches,
    tokens_in,
    verified_values,
)

PAPER_GLOBS = [("paper", "*.tex"), ("paper", "*.md"), ("tex", "*.tex")]
CHECK_NAME = "check_number_scan"

NUMBER_RE = re.compile(r"(?<![\w.])([-+]?\d+\.\d+\s*%?|\d+\s*%)(?![\w])")
PLACEHOLDER_MARKERS = ("placeholder", "todo", "to be written", "draft skeleton")
REFERENCE_WORDS = {
    "table", "tables", "figure", "figures", "fig", "panel", "panels",
    "section", "sections", "sec", "subsection", "appendix", "appendices",
    "equation", "equations", "eq", "eqn", "column", "columns", "col", "row",
    "rows", "chapter", "version", "v", "step", "footnote", "note", "model",
    "models", "specification", "specifications", "spec", "no", "number",
    "page", "pp", "item", "line", "stage", "gate", "hypothesis",
}
_PREV_WORD_RE = re.compile(r"([A-Za-z]+)\.?\s*$")


def _paper_paths() -> list[Path]:
    found: list[Path] = []
    for base, pattern in PAPER_GLOBS:
        b = Path(base)
        if b.exists():
            found.extend(sorted(b.glob(pattern)))
    # Skip generated render artifacts (paper.rendered.tex) -- build output.
    return [p for p in dict.fromkeys(found) if p.exists() and ".rendered." not in p.name]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    root = Path.cwd()
    papers = _paper_paths()
    whitelist = load_whitelist(root)
    verified = verified_values(root)

    warnings: list[str] = []
    scanned = 0
    injected = 0
    for paper in papers:
        text = paper.read_text(encoding="utf-8", errors="ignore")
        if any(m in text.lower() for m in PLACEHOLDER_MARKERS) and not verified:
            continue
        injected += sum(len(tokens_in(line)) for line in text.splitlines())
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in NUMBER_RE.finditer(line):
                token = m.group(1).strip()
                prev = _PREV_WORD_RE.search(line[: m.start()])
                if prev and prev.group(1).lower() in REFERENCE_WORDS:
                    continue
                scanned += 1
                if not matches(token, verified, whitelist):
                    warnings.append(f"{paper}:{line_no}: '{token}' | {line.strip()[:70]}")

    # Coverage: of all the estimate-like figures the paper *displays*, how many
    # are injection-sourced ({{tokens}}) vs still raw hand-typed numbers.
    displayed = injected + scanned
    coverage = (injected / displayed * 100.0) if displayed else 0.0
    note = (f"{scanned} raw number(s) scanned, {len(warnings)} untraceable; "
            f"injection coverage {injected}/{displayed} = {coverage:.0f}% "
            f"(advisory only; gate on check_number_registry)")
    if as_json:
        print(json.dumps({
            "check": CHECK_NAME, "status": "pass",
            "failures": [], "warnings": warnings, "note": note,
            "coverage": {"injected": injected, "displayed": displayed,
                         "percent": round(coverage, 1)},
        }))
    else:
        print(f"PASS (advisory): {note}")
        for w in warnings[:40]:
            print(f"  warning: {w}")
        if len(warnings) > 40:
            print(f"  ... and {len(warnings) - 40} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
