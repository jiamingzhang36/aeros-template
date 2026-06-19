#!/usr/bin/env python3
"""Build a machine-readable index for agent run reports."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "agent_runs"
INDEX_PATH = REPORTS_DIR / "INDEX.csv"


RUN_METADATA_FIELDS = [
    "run_file",
    "run_id",
    "task_id",
    "task_name",
    "agent",
    "date",
    "mode",
    "work_mode",
    "completion_status",
    "branch_commit",
    "start_commit",
    "end_commit",
    "updated_at",
    "requires_critic",
    "requires_human_gate",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_metadata(lines: list[str], label: str) -> str:
    for line in lines:
        match = re.match(rf"^\s*[-*]\s*{re.escape(label)}\s*:\s*(.*)$", line)
        if match:
            return match.group(1).strip()
        match = re.match(rf"^\s*{re.escape(label)}\s*:\s*(.*)$", line)
        if match:
            return match.group(1).strip()
    return ""


def _extract_task_id(path: Path) -> str:
    text = _read_text(path)
    lines = text.splitlines()
    task_id = _extract_metadata(lines, "Task ID")
    if task_id:
        return task_id

    task = _extract_metadata(lines, "Task")
    if task:
        return Path(task).stem.split("_")[0]
    return ""


def _extract_task_name(path: Path) -> str:
    text = _read_text(path)
    return _extract_metadata(text.splitlines(), "Task")


def _extract_field(path: Path, field: str) -> str:
    return _extract_metadata(_read_text(path).splitlines(), field)


def _run_report_files() -> list[Path]:
    files = [
        path
        for path in sorted(REPORTS_DIR.glob("*.md"))
        if not path.name.startswith(("TEMPLATE_", "EXAMPLE_")) and path.name != "INDEX.csv"
    ]
    return files


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in _run_report_files():
        timestamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        task_id = _extract_task_id(path)
        row: dict[str, Any] = {
            "run_file": str(path.relative_to(ROOT)),
            "run_id": _extract_field(path, "Run ID"),
            "task_id": task_id,
            "task_name": _extract_task_name(path),
            "agent": _extract_field(path, "Agent") or _extract_field(path, "Executor"),
            "date": _extract_field(path, "Date"),
            "mode": _extract_field(path, "Mode") or _extract_field(path, "Work mode"),
            "work_mode": _extract_field(path, "Work mode"),
            "completion_status": _extract_field(path, "Completion Status")
            or _extract_field(path, "Completion status"),
            "branch_commit": _extract_field(path, "Branch / commit"),
            "start_commit": _extract_field(path, "Start commit"),
            "end_commit": _extract_field(path, "End commit"),
            "requires_critic": _extract_field(path, "Critic required"),
            "requires_human_gate": _extract_field(path, "Human gate required"),
            "updated_at": timestamp,
        }
        # Ensure all keys exist
        for field in RUN_METADATA_FIELDS:
            row.setdefault(field, "")
        rows.append(row)
    return rows


def write_index(rows: list[dict[str, str]]) -> None:
    if not rows and INDEX_PATH.exists():
        print(f"unchanged 0 row(s) -> {INDEX_PATH}")
        return
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=RUN_METADATA_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    content = buffer.getvalue()
    if INDEX_PATH.exists() and INDEX_PATH.read_text(encoding="utf-8") == content:
        print(f"unchanged {len(rows)} row(s) -> {INDEX_PATH}")
        return
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(content, encoding="utf-8")
    print(f"wrote {len(rows)} row(s) -> {INDEX_PATH}")


def main() -> int:
    rows = build_rows()
    write_index(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
