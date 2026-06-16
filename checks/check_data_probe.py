#!/usr/bin/env python3
"""Validate small data probes and prevent full collection before probe evidence."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.data_first import project_mode  # noqa: E402
from aeros.runtime.data_probe import has_passing_probe, validate_probe_files  # noqa: E402


def _raw_data_files(root: Path) -> list[Path]:
    raw = root / "data" / "raw"
    if not raw.exists():
        return []
    out = []
    for path in raw.rglob("*"):
        if not path.is_file():
            continue
        if path.name in {"README.md", ".gitkeep", ".DS_Store"}:
            continue
        out.append(path)
    return out


def main() -> int:
    root = Path.cwd()
    failures = validate_probe_files(root)
    mode = project_mode(root)
    raw_files = _raw_data_files(root)
    if mode in {"active_research", "adopted"} and raw_files and not has_passing_probe(root):
        failures.append("full/raw data exists before any passing small data probe; run `aeros data probe plan/run/report` or document a receipt-backed exception")
    if failures:
        print("FAIL: data probe problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: data probe layer is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
