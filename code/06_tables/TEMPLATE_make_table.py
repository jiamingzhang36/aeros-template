#!/usr/bin/env python3
"""Template table script with provenance recording."""

from __future__ import annotations

from pathlib import Path
import sys
import csv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.provenance import write_provenance_record


def main() -> None:
    output_path = Path("outputs/table_example.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["col_a", "col_b"])
        writer.writeheader()
        writer.writerow({"col_a": "a", "col_b": "1"})
        writer.writerow({"col_a": "b", "col_b": "2"})

    record = write_provenance_record(
        output_path=output_path,
        script_or_source=Path(__file__).name,
        output_type="table",
        description="placeholder table example",
        input_paths=[],
        parameters={"notes": "replace with real pipeline"},
    )
    print(f"wrote {record['result_id']} -> {record['output_path']}")


if __name__ == "__main__":
    main()
