#!/usr/bin/env python3
"""HARD gate: the number-injection registry is sound and fully sourced.

This is the reliable half of the old check_paper_numbers. It does NOT scan the
whole paper for stray numbers (that is the noisy, advisory half -- see
check_number_scan). It verifies only what can be verified by construction:

1. Every registered result path in evidence/result_index.csv exists.
2. Every paper/numbers.yml entry is grounded:
     - if it declares a cell-level `source:` block, the value must equal that
       exact cell (after the declared transform) -- STRONG, coincidence-proof;
     - otherwise it falls back to the weak aggregate trace (value rounds to some
       number in some registered file) and is reported as a soft warning to
       upgrade to a cell source.
3. No paper {{token}} is unresolved (a token with no registry entry is
   fabrication-by-omission).

Stays quiet (passes) when there is no paper and no registry yet.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.number_injection import (  # noqa: E402
    display_consistent,
    load_numbers,
    load_whitelist,
    matches,
    tokens_in,
    verified_values,
    verify_number,
)

RESULT_INDEX = Path("evidence/result_index.csv")
PAPER_GLOBS = [("paper", "*.tex"), ("paper", "*.md"), ("tex", "*.tex")]
CHECK_NAME = "check_number_registry"


def _paper_paths() -> list[Path]:
    found: list[Path] = []
    for base, pattern in PAPER_GLOBS:
        b = Path(base)
        if b.exists():
            found.extend(sorted(b.glob(pattern)))
    # Skip generated render artifacts (paper.rendered.tex) -- they are build
    # output, not an authored source.
    return [p for p in dict.fromkeys(found) if p.exists() and ".rendered." not in p.name]


def _emit(as_json: bool, status: str, failures: list[str], warnings: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({
            "check": CHECK_NAME, "status": status,
            "failures": failures, "warnings": warnings,
        }))
    elif status == "pass":
        print(f"PASS: {note or 'number registry sound'}")
        for w in warnings:
            print(f"  warning: {w}")
    else:
        print("FAIL: number registry problems:")
        for f in failures:
            print(f"  - {f}")
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    as_json = parser.parse_args(argv).json

    root = Path.cwd()
    failures: list[str] = []
    warnings: list[str] = []

    # 1. Registered result paths must exist.
    populated = 0
    if RESULT_INDEX.exists():
        with RESULT_INDEX.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                path_value = (row.get("path") or "").strip()
                if not path_value:
                    continue
                populated += 1
                if not Path(path_value).exists():
                    failures.append(
                        f"{row.get('result_id','?')}: registered output path missing: {path_value}"
                    )

    # 2. Registry entries grounded.
    try:
        registry = load_numbers(root)
    except ValueError as exc:
        return _emit(as_json, "fail", failures + [str(exc)], warnings)

    verified: list[float] | None = None
    whitelist = load_whitelist(root)
    strong = 0
    for name, spec in registry.items():
        if not isinstance(spec, dict) or spec.get("value") is None:
            failures.append(f"numbers.yml: '{name}' has no value")
            continue
        ok_disp, disp_detail = display_consistent(spec)
        if not ok_disp:
            failures.append(f"numbers.yml: '{name}': {disp_detail}")
        status, detail = verify_number(root, name, spec)
        if status == "ok":
            strong += 1
        elif status in {"mismatch", "error"}:
            failures.append(f"numbers.yml: '{name}': {detail}")
        elif status == "no_source":
            # Fall back to the weak aggregate trace; warn to upgrade.
            if verified is None:
                verified = verified_values(root)
            if matches(str(spec["value"]), verified, whitelist):
                warnings.append(
                    f"'{name}'={spec['value']} traces only weakly (no cell source); "
                    f"add a source: block to make it coincidence-proof"
                )
            else:
                failures.append(
                    f"numbers.yml: '{name}'={spec['value']} has no cell source and does "
                    f"not trace to any registered artifact or whitelist"
                )

    # 3. No unresolved {{tokens}} in the paper.
    papers = _paper_paths()
    for paper in papers:
        text = paper.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            for tok in tokens_in(line):
                if tok not in registry:
                    failures.append(
                        f"{paper}:{line_no}: unresolved number token {{{{{tok}}}}} "
                        f"(not in paper/numbers.yml)"
                    )

    note = (f"{strong} cell-sourced, {len(warnings)} weak, "
            f"{populated} result path(s), {len(papers)} paper(s)")
    return _emit(as_json, "fail" if failures else "pass", failures, warnings, note)


if __name__ == "__main__":
    sys.exit(main())
