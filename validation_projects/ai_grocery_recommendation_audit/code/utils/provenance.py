#!/usr/bin/env python3
"""Small provenance writer shared by table/figure scripts."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_head_sha(repo_root: Path | str = ".") -> str:
    root = str(repo_root)
    try:
        result = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return "unknown"


def _next_indexed_result_id(result_index_path: Path) -> str:
    if not result_index_path.exists():
        return "R001"

    next_id = 1
    with result_index_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            value = (row.get("result_id") or "").strip()
            if value.startswith("R") and value[1:].isdigit():
                next_id = max(next_id, int(value[1:]) + 1)
    return f"R{next_id:03d}"


def write_provenance_record(
    *,
    output_path: Path | str,
    script_or_source: str,
    input_paths: list[Path | str] | None = None,
    output_type: str = "table_or_figure",
    description: str = "",
    parameters: dict[str, Any] | None = None,
    result_id: str | None = None,
    result_index: Path | str = "evidence/result_index.csv",
    provenance_root: Path | str = "outputs/.provenance",
) -> dict[str, Any]:
    output_file = Path(output_path)
    input_paths = input_paths or []
    parameters = parameters or {}

    if result_id is None:
        result_id = _next_indexed_result_id(Path(result_index))

    input_files = []
    for item in input_paths:
        resolved = Path(item)
        record = {
            "path": str(resolved),
            "exists": resolved.exists(),
        }
        if resolved.exists():
            record["sha256"] = file_sha256(resolved)
        input_files.append(record)

    created_at = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "result_id": result_id,
        "output_type": output_type,
        "output_path": str(output_file),
        "script_or_source": script_or_source,
        "description": description,
        "created_at": created_at,
        "parameters": parameters,
        "code_git_sha": repo_head_sha(),
        "input_files": input_files,
    }

    provenance_root = Path(provenance_root)
    provenance_root.mkdir(parents=True, exist_ok=True)
    provenance_path = provenance_root / f"{result_id}.json"
    with provenance_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
    record["provenance_path"] = str(provenance_path)
    return record


def normalize_records_for_index(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for record in sorted(records, key=lambda item: item.get("result_id", "")):
        normalized.append(
            {
                "result_id": str(record.get("result_id", "")),
                "output_type": str(record.get("output_type", "")),
                "path": str(record.get("output_path", "")),
                "script_or_source": str(record.get("script_or_source", "")),
                "description": str(record.get("description", "")),
                "created_date": str(record.get("created_at", "")),
                "linked_claims": "",
                "notes": "",
            }
        )
    return normalized


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: provenance.py <output-path>")
    output = Path(sys.argv[1])
    payload = write_provenance_record(
        output_path=output,
        script_or_source=Path(sys.argv[0]).name,
    )
    print(payload["result_id"])
