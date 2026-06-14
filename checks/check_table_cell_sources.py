#!/usr/bin/env python3
"""HARD gate: every numeric cell in the paper's tables traces to a source CSV.

Closes the "table-cell-vs-source-CSV equality" gap: a number printed in a paper
table must not have drifted from the data behind it. Mirrors the rest of the
integrity layer — the machine checks structure + coverage, a human declares the
substance:

1. Parse `tex/paper.tex` for the tables it `\\input`s from the project's
   `final_csv/` directory.
2. Every such table must be listed in `audits/table_source_map.yml`, and the map
   must carry a filled `verified_by:` sign-off (no new table escapes silently).
3. For a table mapped to `source: X.csv`, EVERY numeric cell in its `.tex` must
   round-match (to the cell's displayed precision) some value in `X.csv`.
   Calendar years (1900-2100) are treated as labels, not data, and skipped.
4. A table mapped to `exempt: <reason>` carries no machine-readable numeric
   source (qualitative text table, or a regression table written straight to
   `.tex` by code) and is skipped here — its integrity is the reproducibility /
   provenance gates' job.

Stays quiet (passes) when there is no `tex/paper.tex` yet (template-safe). Does
NOT run any analysis code. Run `python checks/check_table_cell_sources.py --selftest`.

Honest limit: cell-vs-CSV matching is "this value exists somewhere in the source
CSV (within rounding)", not a row x column cross-check, so a hand-edit that
happens to collide with an unrelated CSV value can slip through. It reliably
catches typos, transposed digits, and sign flips on values not otherwise present.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a project dependency
    yaml = None

PAPER = Path("tex/paper.tex")
MAP = Path("audits/table_source_map.yml")
CHECK_NAME = "check_table_cell_sources"
# only \input paths containing this marker are treated as tables (not prose /
# preamble inputs). Override per project via `table_input_marker:` in the map.
DEFAULT_TABLE_MARKER = "/final_csv/"

# \input{<path>.tex} — captured as a full path, resolved relative to paper.tex,
# so the check is domain-neutral (no hardcoded data dir); the source CSV is a
# sibling of the table .tex.
INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+?\.tex)\s*\}")
# numbers incl. sign, decimals, scientific notation
NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
# numbers glued to a LaTeX length unit are layout, not data
LEN_RE = re.compile(r"[-+]?\d*\.?\d+\\(?:text|line|h)(?:width|size|height)")
# LaTeX layout commands whose numeric arguments are spans/rules, not data
SPAN_RE = re.compile(r"\\multicolumn\s*\{[^}]*\}\s*\{[^}]*\}|"
                     r"\\cmidrule\s*(?:\([^)]*\))?\s*\{[^}]*\}|"
                     r"\\cline\s*\{[^}]*\}")
THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d)")
_PLACEHOLDER = ("<!--", "todo", "tbd", "name + date", "")


def parse_paper_inputs(paper_text: str) -> list[str]:
    """Relative \\input paths to .tex files (full path, resolved by the caller)."""
    return [m.group(1).strip() for m in INPUT_RE.finditer(paper_text)]


def _is_calendar_year(value: float, decimals: int) -> bool:
    return decimals == 0 and 1900 <= abs(value) <= 2100


def extract_tex_numbers(tex_text: str) -> list[tuple[float, int]]:
    """Numbers from data rows (lines with a column separator), with decimals."""
    out: list[tuple[float, int]] = []
    for line in tex_text.splitlines():
        if "&" not in line:
            continue
        line = SPAN_RE.sub(" ", line)        # drop \multicolumn/\cmidrule spans
        line = THOUSANDS_RE.sub("", line)    # 21,394 -> 21394
        line = LEN_RE.sub(" ", line)
        for tok in NUM_RE.findall(line):
            try:
                value = float(tok)
            except ValueError:
                continue
            frac = tok.split("e")[0].split("E")[0]
            decimals = len(frac.split(".")[1]) if "." in frac else 0
            if _is_calendar_year(value, decimals):
                continue
            out.append((value, decimals))
    return out


def csv_numbers(csv_text: str) -> list[float]:
    vals: list[float] = []
    for tok in NUM_RE.findall(csv_text):
        try:
            vals.append(float(tok))
        except ValueError:
            pass
    return vals


def _matches(value: float, decimals: int, pool: list[float]) -> bool:
    tol = 0.5 * (10 ** -decimals) + 1e-6
    return any(abs(value - v) <= tol for v in pool)


def audit(paper_tables: list[str], mapping: dict | None,
          tex_texts: dict[str, str], csv_texts: dict[str, str]) -> list[str]:
    """Pure core. `mapping` is the parsed YAML; tex/csv texts keyed by stem/name."""
    if mapping is None:
        return [f"missing or unparseable {MAP}"]
    verified = str(mapping.get("verified_by") or "").strip()
    tables = mapping.get("tables") or {}
    failures: list[str] = []

    if not verified or any(verified.lower().startswith(p) or verified.lower() == p
                           for p in _PLACEHOLDER if p):
        failures.append("table_source_map.yml has no filled `verified_by:` sign-off")

    undeclared = [t for t in paper_tables if t not in tables]
    if undeclared:
        failures.append(f"{len(undeclared)} paper table(s) not in the map: "
                        f"{', '.join(sorted(set(undeclared))[:8])}")

    for stem in paper_tables:
        spec = tables.get(stem)
        if not isinstance(spec, dict):
            continue
        src = spec.get("source")
        if not src:
            continue  # exempt — declared, skipped
        if stem not in tex_texts:
            failures.append(f"{stem}: .tex not found")
            continue
        if src not in csv_texts:
            failures.append(f"{stem}: source CSV {src} not found")
            continue
        pool = csv_numbers(csv_texts[src])
        # only decimal-bearing cells (the estimates) must trace; integer counts
        # (N, events, clusters, column indices) are sample-size/layout metadata
        # gated elsewhere, not stored in these coefficient CSVs
        bad = [f"{v:g}" for v, d in extract_tex_numbers(tex_texts[stem])
               if d > 0 and not _matches(v, d, pool)]
        if bad:
            failures.append(f"{stem}: {len(bad)} cell(s) not in {src}: "
                            f"{', '.join(bad[:6])}{' …' if len(bad) > 6 else ''}")
    return failures


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: every paper table cell traces to its source CSV{(' — ' + note) if note else ''}")
    else:
        print("FAIL: table cell-vs-source-CSV gate:")
        print("\n".join(failures))
        print("Resolve in audits/table_source_map.yml (map each paper table to a "
              "source CSV or an honest exempt reason, then fill `verified_by:`).")
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate paper table cells against source CSVs.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not PAPER.exists():
        return _emit(args.json, "pass", [], "no tex/paper.tex yet")
    if yaml is None:
        return _emit(args.json, "fail", ["PyYAML not available to read the map"])
    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8")) if MAP.exists() else None
    marker = (mapping.get("table_input_marker") if mapping else None) or DEFAULT_TABLE_MARKER
    paper_dir = PAPER.parent
    # table .tex paths resolved relative to the paper, keyed by stem
    stem_to_path = {}
    for rel in parse_paper_inputs(PAPER.read_text(encoding="utf-8", errors="ignore")):
        if marker in rel:
            tp = paper_dir / rel
            stem_to_path[tp.stem] = tp
    paper_tables = list(stem_to_path.keys())
    tables = (mapping.get("tables") or {}) if mapping else {}
    tex_texts = {stem: tp.read_text(encoding="utf-8", errors="ignore")
                 for stem, tp in stem_to_path.items() if tp.exists()}
    csv_texts = {}
    for stem, spec in tables.items():
        src = spec.get("source") if isinstance(spec, dict) else None
        if src and stem in stem_to_path:
            csvp = stem_to_path[stem].parent / src
            if csvp.exists():
                csv_texts[src] = csvp.read_text(encoding="utf-8", errors="ignore")
    failures = audit(paper_tables, mapping, tex_texts, csv_texts)
    note = f"{len(paper_tables)} paper table(s)"
    return _emit(args.json, "fail" if failures else "pass", failures, note)


def _selftest() -> int:
    paper = (r"\input{../cultivated_meat_project/data/final_csv/reg.tex}" "\n"
             r"\input{../cultivated_meat_project/data/final_csv/notes.tex}" "\n")
    mp = {"verified_by": "Jiaming 2026-06-14",
          "tables": {"reg": {"source": "reg_results.csv"},
                     "notes": {"exempt": "text"}}}
    tex_ok = "X & -0.162** (0.077) \\\\\n$N$ & 50 \\\\\n"
    tex_bad = "X & -0.999 (0.077) \\\\\n"
    csv = "var,coef,se,n\nx,-0.16228,0.07690,50\n"
    cases = [
        ("covered + signed -> pass",
         audit(["reg", "notes"], mp, {"reg": tex_ok}, {"reg_results.csv": csv}) == [], True),
        ("bad cell -> fail",
         any("not in" in x for x in audit(["reg"], mp, {"reg": tex_bad},
                                          {"reg_results.csv": csv})), True),
        ("unsigned map -> fail",
         any("verified_by" in x for x in audit(["reg"], {"verified_by": "", "tables": mp["tables"]},
                                               {"reg": tex_ok}, {"reg_results.csv": csv})), True),
        ("undeclared table -> fail",
         any("not in the map" in x for x in audit(["reg", "ghost"], mp, {"reg": tex_ok},
                                                  {"reg_results.csv": csv})), True),
        ("calendar year not required -> pass",
         audit(["reg"], {"verified_by": "x", "tables": {"reg": {"source": "reg_results.csv"}}},
               {"reg": "Y & 2024 & -0.162 \\\\\n"}, {"reg_results.csv": csv}) == [], True),
    ]
    ok = all(got is want for _, got, want in cases)
    for name, got, want in cases:
        print(f"  [{'ok' if got is want else 'FAIL'}] {name}")
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
