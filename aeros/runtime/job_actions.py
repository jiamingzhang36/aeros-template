"""Deterministic local actions emitted by the ResearchJob compiler."""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path


def data_probe(source: Path, output: Path, target: str) -> int:
    if not source.is_file():
        return 2
    digest = sha256(source.read_bytes()).hexdigest()
    rows = 0
    columns: list[str] = []
    if source.suffix.lower() in {".csv", ".tsv"}:
        delimiter = "\t" if source.suffix.lower() == ".tsv" else ","
        with source.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            try:
                columns = [str(x) for x in next(reader)]
            except StopIteration:
                columns = []
            rows = sum(1 for _ in reader)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "model": "AEROS-RESEARCH-JOB-DATA-PROBE-001",
        "target": target,
        "source": str(source),
        "source_sha256": digest,
        "rows_observed": rows,
        "columns_observed": columns,
        "status": "probe_observed",
        "does_not_prove": ["data fitness", "canonical admission", "claim support"],
    }, indent=2) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["data-probe"])
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    return data_probe(Path(args.source), Path(args.output), args.target)


if __name__ == "__main__":
    raise SystemExit(main())

