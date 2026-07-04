#!/usr/bin/env python3
"""Check source-id consistency across data contract, inventory, and results."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.source_id_consistency import validate_source_id_consistency


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    report = validate_source_id_consistency(ROOT)
    if report["status"] != "PASS":
        for issue in report["issues"]:
            print(f"FAIL: {issue}")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_csv(root / "discovery" / "data_inventory.csv", [{"data_id": "D001", "source_name": "demo"}])
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "data_contract.yml").write_text(
            "raw_data:\n  expected_sources:\n    - source_id: D999\n",
            encoding="utf-8",
        )
        bad = validate_source_id_consistency(root)
        if bad["status"] != "FAIL" or not any("D999" in issue for issue in bad["issues"]):
            print("FAIL: fixture did not catch contract/inventory source_id drift")
            return 1

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_csv(root / "discovery" / "data_inventory.csv", [{"data_id": "D001", "source_name": "demo"}])
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "data_contract.yml").write_text(
            "raw_data:\n  expected_sources:\n    - source_id: D001\n",
            encoding="utf-8",
        )
        prov = root / "outputs" / ".provenance"
        prov.mkdir(parents=True, exist_ok=True)
        (prov / "R001.json").write_text(json.dumps({"result_id": "R001", "source_id": "D404"}), encoding="utf-8")
        bad = validate_source_id_consistency(root)
        if bad["status"] != "FAIL" or not any("D404" in issue for issue in bad["issues"]):
            print("FAIL: fixture did not catch provenance source_id drift")
            return 1

    print("PASS: source-id consistency check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
