"""Derived SQLite journal for AEROS control metadata.

The SQLite journal is a disposable projection over Git-tracked files. It is not
a source of truth and must not hold authority over claims, gates, releases, or
human admissions.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any

import yaml


DEFAULT_JOURNAL_PATH = Path("outputs/journal/aeros_journal.sqlite")


@dataclass(frozen=True)
class JournalBuildReport:
    status: str
    output_path: str
    dry_run: bool
    source_counts: dict[str, int]
    does_not_prove: tuple[str, ...] = (
        "scientific truth",
        "claim support",
        "gate approval",
        "paper readiness",
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["does_not_prove"] = list(self.does_not_prove)
        return data


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_artifacts(root: Path) -> list[tuple[str, str, int, str]]:
    candidates = [
        "project_manifest.yml",
        "evidence/result_index.csv",
        "evidence/claim_registry.md",
        "events/event_log.jsonl",
    ]
    rows: list[tuple[str, str, int, str]] = []
    for rel in candidates:
        path = root / rel
        if path.exists() and path.is_file():
            rows.append((rel, _sha256(path), path.stat().st_size, "core"))
    for folder, kind in [("outputs/.provenance", "provenance"), ("evidence/evidence_units", "evidence_unit"), ("evidence/result_admissions", "result_admission")]:
        base = root / folder
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                rows.append((path.relative_to(root).as_posix(), _sha256(path), path.stat().st_size, kind))
    return rows


def _iter_results(root: Path) -> list[dict[str, str]]:
    path = root / "evidence/result_index.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _iter_provenance(root: Path) -> list[dict[str, str]]:
    base = root / "outputs/.provenance"
    rows: list[dict[str, str]] = []
    if not base.exists():
        return rows
    for path in sorted(base.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        rows.append({
            "source_path": path.relative_to(root).as_posix(),
            "result_id": str(data.get("result_id", "")),
            "artifact_path": str(data.get("artifact_path", data.get("path", ""))),
            "sha256": str(data.get("sha256", data.get("artifact_sha256", ""))),
        })
    return rows


def _iter_evidence_units(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for folder, record_type in [("evidence/evidence_units", "evidence_unit"), ("evidence/result_admissions", "result_admission")]:
        base = root / folder
        if not base.exists():
            continue
        for path in sorted(base.glob("*.yml")) + sorted(base.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                continue
            rows.append({
                "source_path": path.relative_to(root).as_posix(),
                "record_type": record_type,
                "record_id": str(data.get("evidence_unit_id") or data.get("result_admission_id") or ""),
                "status": str(data.get("admission_status") or data.get("machine_status") or ""),
                "claim_effect": str(data.get("claim_effect", "")),
            })
    return rows


def _iter_events(root: Path) -> list[dict[str, str]]:
    path = root / "events/event_log.jsonl"
    rows: list[dict[str, str]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except Exception:
            data = {}
        rows.append({
            "event_id": str(data.get("event_id", data.get("id", ""))),
            "event_type": str(data.get("event_type", "")),
            "action": str(data.get("action", data.get("action_name", ""))),
            "source_path": "events/event_log.jsonl",
        })
    return rows


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=DELETE")
    return conn


def build_sqlite_journal(root: Path, output_path: Path | None = None, *, dry_run: bool = False) -> JournalBuildReport:
    root = root.resolve()
    rel_output = output_path or DEFAULT_JOURNAL_PATH
    output = (root / rel_output).resolve() if not rel_output.is_absolute() else rel_output
    artifacts = _iter_artifacts(root)
    results = _iter_results(root)
    provenance = _iter_provenance(root)
    evidence_units = _iter_evidence_units(root)
    events = _iter_events(root)
    counts = {
        "artifacts": len(artifacts),
        "results": len(results),
        "provenance": len(provenance),
        "evidence_units": len(evidence_units),
        "events": len(events),
    }
    if dry_run:
        return JournalBuildReport("DRY_RUN", output.relative_to(root).as_posix(), True, counts)

    conn = _connect(output)
    try:
        conn.executescript(
            """
            DROP TABLE IF EXISTS journal_metadata;
            DROP TABLE IF EXISTS artifacts;
            DROP TABLE IF EXISTS results;
            DROP TABLE IF EXISTS provenance;
            DROP TABLE IF EXISTS evidence_units;
            DROP TABLE IF EXISTS events;
            CREATE TABLE journal_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE artifacts (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, kind TEXT NOT NULL);
            CREATE TABLE results (result_id TEXT, output_type TEXT, path TEXT, script_or_source TEXT, linked_claims TEXT, source_path TEXT NOT NULL);
            CREATE TABLE provenance (source_path TEXT PRIMARY KEY, result_id TEXT, artifact_path TEXT, sha256 TEXT);
            CREATE TABLE evidence_units (source_path TEXT PRIMARY KEY, record_type TEXT, record_id TEXT, status TEXT, claim_effect TEXT);
            CREATE TABLE events (event_id TEXT, event_type TEXT, action TEXT, source_path TEXT NOT NULL);
            """
        )
        conn.execute("INSERT INTO journal_metadata VALUES (?, ?)", ("authority", "derived_index_only"))
        conn.execute("INSERT INTO journal_metadata VALUES (?, ?)", ("does_not_prove", "scientific truth;claim support;gate approval;paper readiness"))
        conn.executemany("INSERT INTO artifacts VALUES (?, ?, ?, ?)", artifacts)
        conn.executemany(
            "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    str(row.get("result_id", "")),
                    str(row.get("output_type", "")),
                    str(row.get("path", "")),
                    str(row.get("script_or_source", "")),
                    str(row.get("linked_claims", "")),
                    "evidence/result_index.csv",
                )
                for row in results
            ],
        )
        conn.executemany("INSERT INTO provenance VALUES (:source_path, :result_id, :artifact_path, :sha256)", provenance)
        conn.executemany("INSERT INTO evidence_units VALUES (:source_path, :record_type, :record_id, :status, :claim_effect)", evidence_units)
        conn.executemany("INSERT INTO events VALUES (:event_id, :event_type, :action, :source_path)", events)
        conn.commit()
    finally:
        conn.close()
    return JournalBuildReport("PASS", output.relative_to(root).as_posix(), False, counts)


def format_journal_report(report: JournalBuildReport) -> str:
    lines = [
        f"status: {report.status}",
        f"output_path: {report.output_path}",
        f"dry_run: {str(report.dry_run).lower()}",
        "source_counts:",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(report.source_counts.items()))
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.does_not_prove)
    return "\n".join(lines)
