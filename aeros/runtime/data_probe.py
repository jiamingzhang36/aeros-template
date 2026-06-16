"""Small-sample data probe utilities for AEROS.

A probe is a narrow feasibility test before full collection: access, parse,
sample, fields, coverage hint, and failure modes. It never approves a gate or
upgrades a claim.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

INVENTORY = Path("discovery/data_inventory.csv")
PROBE_ROOT = Path("data/probes")
PROBE_PLAN = Path("data/probes/probe_plan.yml")
PROBE_REPORT = Path("audits/data_probe_report.md")
FAILURE_TAXONOMY = Path("harness/probe_failure_taxonomy.yml")


@dataclass(frozen=True)
class DataProbeArgs:
    command: str
    source: str = ""
    limit: int = 25
    dry_run: bool = False


def _load_taxonomy(project_root: Path) -> dict[str, Any]:
    path = project_root / FAILURE_TAXONOMY
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    out = "_".join(part for part in out.split("_") if part)
    return out or "source"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def read_inventory(project_root: Path) -> list[dict[str, str]]:
    path = project_root / INVENTORY
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("data_id") or "").strip()]


def _find_source(rows: list[dict[str, str]], source: str) -> dict[str, str] | None:
    for row in rows:
        if source in {str(row.get("data_id", "")).strip(), str(row.get("dataset_name", "")).strip()}:
            return row
    return None


def _local_path(project_root: Path, row: dict[str, str]) -> Path | None:
    raw = str(row.get("link_or_path", "")).strip()
    if not raw or raw.startswith(("http://", "https://")):
        return None
    p = project_root / raw
    if p.exists():
        return p
    q = Path(raw).expanduser()
    if q.exists():
        return q
    return None


def write_probe_plan(project_root: Path, dry_run: bool = False) -> int:
    rows = read_inventory(project_root)
    items: list[dict[str, Any]] = []
    for row in rows:
        data_id = str(row.get("data_id", "")).strip()
        link = str(row.get("link_or_path", "")).strip()
        local = _local_path(project_root, row)
        if local:
            probe_class = "local_sample_probe"
            status = "runnable"
            command = ["python3", "-m", "aeros.cli", "data", "probe", "run", "--source", data_id, "--limit", "25"]
        elif link.startswith(("http://", "https://")):
            probe_class = "official_source_snapshot_probe"
            status = "requires_approval_or_manual_snapshot"
            command = []
        else:
            probe_class = "source_locator_probe"
            status = "needs_source_path_or_receipt"
            command = []
        items.append({
            "data_id": data_id,
            "dataset_name": row.get("dataset_name", ""),
            "probe_class": probe_class,
            "status": status,
            "link_or_path": link,
            "suggested_command": command,
            "required_report_fields": [
                "source_snapshot",
                "sample_rows",
                "fields_observed",
                "coverage_hint",
                "parse_status",
                "linkage_keys_observed",
                "failure_modes",
            ],
        })
    payload = {"version": 1, "generated_at": _now(), "policy": "AEROS-DATA-PROBE-001", "items": items}
    print(f"[data-probe] inventory rows: {len(rows)}")
    print(f"[data-probe] probe items: {len(items)}")
    for item in items:
        print(f"  - {item['data_id']} {item['probe_class']}/{item['status']}")
    if dry_run:
        print("[data-probe] dry-run: no files written")
        return 0
    path = project_root / PROBE_PLAN
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"[data-probe] wrote {_rel(project_root, path)}")
    return 0


def _sample_csv(path: Path, out: Path, limit: int) -> tuple[int, list[str]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            rows.append(row)
        fields = list(reader.fieldnames or [])
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), fields


def _sample_jsonl(path: Path, out: Path, limit: int) -> tuple[int, list[str]]:
    fields: set[str] = set()
    count = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with path.open(encoding="utf-8", errors="replace") as src, out.open("w", encoding="utf-8") as dst:
        for line in src:
            if count >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    fields.update(str(k) for k in obj.keys())
            except json.JSONDecodeError:
                pass
            dst.write(line + "\n")
            count += 1
    return count, sorted(fields)


def run_probe(project_root: Path, source: str, limit: int = 25, dry_run: bool = False) -> int:
    rows = read_inventory(project_root)
    row = _find_source(rows, source)
    if not row:
        print(f"FAIL: source not found in {INVENTORY}: {source}")
        return 1
    path = _local_path(project_root, row)
    data_id = str(row.get("data_id", source)).strip()
    if not path:
        print("REFUSED: data probe run only handles local sample paths in v1")
        print("Use `aeros data probe plan` and a human/source snapshot receipt for official-source/API/credentialed probes.")
        return 2
    probe_dir = project_root / PROBE_ROOT / _slug(data_id)
    ext = path.suffix.lower()
    sample_path = probe_dir / ("sample" + (".jsonl" if ext == ".jsonl" else ".csv"))
    print(f"[data-probe] source: {data_id}")
    print(f"[data-probe] local path: {_rel(project_root, path)}")
    if dry_run:
        print("[data-probe] dry-run: no files written")
        return 0
    try:
        if ext in {".csv", ".tsv"}:
            if ext == ".tsv":
                # Convert a small TSV sample through csv module with tab dialect.
                with path.open(newline="", encoding="utf-8", errors="replace") as handle:
                    reader = csv.DictReader(handle, delimiter="	")
                    rows_out = []
                    for idx, item in enumerate(reader):
                        if idx >= limit:
                            break
                        rows_out.append(item)
                    fields = list(reader.fieldnames or [])
                probe_dir.mkdir(parents=True, exist_ok=True)
                with sample_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows_out)
                sample_rows = len(rows_out)
            else:
                sample_rows, fields = _sample_csv(path, sample_path, limit)
        elif ext == ".jsonl":
            sample_rows, fields = _sample_jsonl(path, sample_path, limit)
        else:
            print(f"REFUSED: local probe v1 supports csv/tsv/jsonl, not {ext or '(no extension)'}")
            return 2
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: probe parse failed: {exc}")
        return 1
    taxonomy = _load_taxonomy(project_root)
    scorecard = {
        "completeness": sample_rows > 0,
        "schema_validity": bool(fields),
        "linkage_feasibility": False,
        "coverage_fit": bool(row.get("geography", "") or row.get("period", "")),
        "bias_risk_documented": False,
        "terms_release_fit_documented": False,
    }
    failure_types = [] if sample_rows > 0 and fields else ["schema_mismatch"]
    metadata = {
        "version": 1,
        "policy": "AEROS-DATA-PROBE-001",
        "data_id": data_id,
        "dataset_name": row.get("dataset_name", ""),
        "source_path": _rel(project_root, path),
        "source_snapshot": f"local file mtime={path.stat().st_mtime}",
        "generated_at": _now(),
        "limit": limit,
        "sample_rows": sample_rows,
        "fields_observed": fields,
        "coverage_hint": row.get("geography", "") + " | " + row.get("period", ""),
        "parse_status": "passed",
        "linkage_keys_observed": "",
        "failure_modes": [],
        "failure_types": failure_types,
        "failure_taxonomy_version": taxonomy.get("version", ""),
        "scorecard": scorecard,
        "sample_path": _rel(project_root, sample_path),
        "probe_verdict": "passed" if sample_rows > 0 else "failed",
    }
    meta_path = probe_dir / "probe_metadata.yml"
    meta_path.write_text(yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"[data-probe] wrote {_rel(project_root, sample_path)}")
    print(f"[data-probe] wrote {_rel(project_root, meta_path)}")
    return 0 if sample_rows > 0 else 1


def write_probe_report(project_root: Path, dry_run: bool = False) -> int:
    metas = sorted((project_root / PROBE_ROOT).glob("*/probe_metadata.yml"))
    rows: list[dict[str, Any]] = []
    for path in metas:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                data["metadata_path"] = _rel(project_root, path)
                rows.append(data)
        except yaml.YAMLError:
            rows.append({"metadata_path": _rel(project_root, path), "probe_verdict": "unreadable"})
    passed = [row for row in rows if row.get("probe_verdict") == "passed"]
    print(f"[data-probe] probe metadata files: {len(rows)}")
    print(f"[data-probe] passed probes: {len(passed)}")
    if dry_run:
        print("[data-probe] dry-run: no files written")
        return 0
    lines = [
        "# Data Probe Report",
        "",
        f"- Generated at: {_now()}",
        f"- Probe metadata files: {len(rows)}",
        f"- Passed probes: {len(passed)}",
        "",
        "## Probe Summary",
        "",
    ]
    if not rows:
        lines.append("No completed data probes found. Run `aeros data probe plan` and then a local or approved source-specific probe before full collection.")
    for row in rows:
        lines.extend([
            f"### {row.get('data_id', '(unknown)')}",
            "",
            f"- Verdict: {row.get('probe_verdict', 'unknown')}",
            f"- Source snapshot: {row.get('source_snapshot', '')}",
            f"- Sample rows: {row.get('sample_rows', '')}",
            f"- Fields observed: {', '.join(str(x) for x in (row.get('fields_observed') or []))}",
            f"- Coverage hint: {row.get('coverage_hint', '')}",
            f"- Metadata: {row.get('metadata_path', '')}",
            "",
        ])
    path = project_root / PROBE_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[data-probe] wrote {_rel(project_root, path)}")
    return 0


def has_passing_probe(project_root: Path) -> bool:
    for path in sorted((project_root / PROBE_ROOT).glob("*/probe_metadata.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and data.get("probe_verdict") == "passed":
            return True
    return False


def validate_probe_files(project_root: Path) -> list[str]:
    failures: list[str] = []
    for path in sorted((project_root / PROBE_ROOT).glob("*/probe_metadata.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            failures.append(f"{path}: unreadable probe metadata ({exc})")
            continue
        if not isinstance(data, dict):
            failures.append(f"{path}: probe metadata must be a mapping")
            continue
        data_id = str(data.get("data_id", path.parent.name))
        for key in ["source_snapshot", "sample_rows", "fields_observed", "coverage_hint", "parse_status", "failure_modes", "failure_types", "scorecard", "probe_verdict"]:
            if key not in data:
                failures.append(f"{data_id}: probe metadata missing {key}")
        if data.get("probe_verdict") == "passed" and int(data.get("sample_rows") or 0) <= 0:
            failures.append(f"{data_id}: passed probe must have sample_rows > 0")
    return failures
