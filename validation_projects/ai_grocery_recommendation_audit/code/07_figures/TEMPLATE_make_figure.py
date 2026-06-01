#!/usr/bin/env python3
"""Template figure script with provenance recording."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.provenance import write_provenance_record


def main() -> None:
    output_path = Path("outputs/figure_example.svg")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("<!-- placeholder figure -->\n")

    record = write_provenance_record(
        output_path=output_path,
        script_or_source=Path(__file__).name,
        output_type="figure",
        description="placeholder figure example",
        input_paths=[],
        parameters={"notes": "replace with real plotting code"},
    )
    print(f"wrote {record['result_id']} -> {record['output_path']}")


if __name__ == "__main__":
    main()
