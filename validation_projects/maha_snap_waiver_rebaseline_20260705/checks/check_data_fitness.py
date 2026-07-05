#!/usr/bin/env python3
"""HARD gate: every acquired dataset has a human-ratified 口径 (fitness) entry.

The data-layer analog of the claim registry. `check_data_provenance` proves a
datum is *real and traceable*; this proves a human has judged it *fit for the
research need* — the semantic-fitness / 口径 decision the roadmap keeps on the
human side (mirrors how the claim gate keeps claim ratification human).

For every dataset registered in `evidence/data_index.csv`, the
`evidence/data_fitness_ledger.md` table must carry a row with a non-placeholder
**Definition (口径)** (what was operationally measured), **Intended use** (the
research need / claim it serves), **Fitness** (the human's fit-for-purpose
judgment incl. known limits), and a filled **Ratified-by** sign-off.

Stays quiet (passes) when there is no `data_index.csv` yet (the data-acquisition
layer is opt-in). Run `python checks/check_data_fitness.py --selftest`.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

DATA_INDEX = Path("evidence/data_index.csv")
LEDGER = Path("evidence/data_fitness_ledger.md")
CHECK_NAME = "check_data_fitness"
# header substrings -> logical field
_COLS = {"data id": "data_id", "definition": "definition",
         "intended": "intended", "fitness": "fitness", "ratified": "ratified"}
_REQUIRED = ("definition", "intended", "fitness", "ratified")
_PLACEHOLDER = ("pending", "todo", "tbd", "<!--", "name + date", "")


def _data_ids(index_text: str) -> list[str]:
    rows = list(csv.DictReader(index_text.splitlines()))
    return [(r.get("data_id") or "").strip() for r in rows if (r.get("data_id") or "").strip()]


def _split_row(line: str) -> list[str]:
    cells = line.split("|")
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [c.strip() for c in cells]


def parse_ledger(md_text: str) -> dict[str, dict[str, str]]:
    """Parse the markdown table into {data_id: {field: value}}."""
    table_lines = [ln for ln in md_text.splitlines() if ln.strip().startswith("|")]
    header_idx = None
    colmap: dict[int, str] = {}
    for i, ln in enumerate(table_lines):
        cells = _split_row(ln)
        low = [c.lower() for c in cells]
        if any("data id" in c for c in low):
            for j, c in enumerate(low):
                for key, field in _COLS.items():
                    if key in c:
                        colmap[j] = field
            header_idx = i
            break
    if header_idx is None or "data_id" not in colmap.values():
        return {}
    out: dict[str, dict[str, str]] = {}
    for ln in table_lines[header_idx + 1:]:
        cells = _split_row(ln)
        if set("".join(cells)) <= set("-: "):  # separator row
            continue
        rec = {colmap[j]: cells[j] for j in colmap if j < len(cells)}
        did = rec.get("data_id", "")
        if did:
            out[did] = rec
    return out


def _placeholder(val: str) -> bool:
    low = val.strip().lower()
    return (not low) or any(low.startswith(p) for p in _PLACEHOLDER if p)


def audit(data_ids: list[str], ledger_text: str | None) -> list[str]:
    if ledger_text is None:
        return [f"missing {LEDGER} (register fitness for each dataset in data_index.csv)"]
    ledger = parse_ledger(ledger_text)
    failures: list[str] = []
    for did in data_ids:
        rec = ledger.get(did)
        if rec is None:
            failures.append(f"{did}: no row in data_fitness_ledger.md")
            continue
        for field in _REQUIRED:
            if _placeholder(rec.get(field, "")):
                label = "Ratified-by sign-off" if field == "ratified" else field
                failures.append(f"{did}: {label} is empty/placeholder")
    return failures


def _emit(as_json: bool, status: str, failures: list[str], note: str = "") -> int:
    if as_json:
        print(json.dumps({"check": CHECK_NAME, "status": status,
                          "failures": failures, "note": note}, ensure_ascii=False))
    elif status == "pass":
        print(f"PASS: every registered dataset has a ratified 口径/fitness entry{(' — ' + note) if note else ''}")
    else:
        print("FAIL: data-fitness (口径) gate:")
        for f in failures:
            print(f"  - {f}")
        print("Resolve in evidence/data_fitness_ledger.md (definition + intended use + "
              "fitness judgment + Ratified-by) for each dataset in data_index.csv.")
    return 0 if status == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate the 口径/fitness ledger.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not DATA_INDEX.exists():
        return _emit(args.json, "pass", [], "no data_index.csv yet")
    data_ids = _data_ids(DATA_INDEX.read_text(encoding="utf-8"))
    ledger_text = LEDGER.read_text(encoding="utf-8") if LEDGER.exists() else None
    failures = audit(data_ids, ledger_text)
    return _emit(args.json, "fail" if failures else "pass", failures, f"{len(data_ids)} dataset(s)")


def _selftest() -> int:
    header = ("| Data ID | Definition (口径) | Intended use | Fitness | Ratified-by |\n"
              "|---|---|---|---|---|\n")
    ok = header + "| ds1 | NAICS 3116 emp | meatpacking proxy | fit, known limits | jiaming (2026-06-14) |\n"
    unsigned = header + "| ds1 | NAICS 3116 emp | meatpacking proxy | fit | pending |\n"
    empty = header + "| ds1 | NAICS 3116 emp |  | fit | jiaming |\n"
    cases = [
        ("complete + signed -> pass", audit(["ds1"], ok) == [], True),
        ("missing ledger -> fail", audit(["ds1"], None) != [], True),
        ("missing dataset row -> fail", any("no row" in x for x in audit(["ds2"], ok)), True),
        ("unsigned -> fail", any("Ratified-by" in x for x in audit(["ds1"], unsigned)), True),
        ("empty field -> fail", any("intended" in x for x in audit(["ds1"], empty)), True),
    ]
    res = all(got is want for _, got, want in cases)
    for name, got, want in cases:
        print(f"  [{'ok' if got is want else 'FAIL'}] {name}")
    print("SELFTEST PASS" if res else "SELFTEST FAIL")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(main())
