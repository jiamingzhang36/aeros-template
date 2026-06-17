"""Phase 0 result registry and estimation adapter contract.

The registry boundary is the estimation call, not the manuscript. Adapters should
introspect fitted model objects and write records here so numbers are born with
spec provenance rather than rediscovered from the paper after the fact.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_REGISTRY = Path("evidence/result_registry.csv")
RESULT_INDEX = Path("evidence/result_index.csv")

REGISTRY_FIELDS = [
    "result_id",
    "values_json",
    "spec_id",
    "estimator",
    "formula",
    "fixed_effects_json",
    "cluster_json",
    "sample_filters_json",
    "code_ref_json",
    "data_snapshot_hash",
    "run_event_id",
    "output_path",
    "output_artifact_hash",
    "claim_type_eligibility",
    "adapter_name",
    "adapter_version",
    "registered_at",
    "notes",
]

RESULT_INDEX_FIELDS = ["result_id", "path", "script_or_source", "linked_claims"]

ELIGIBILITY_ORDER = [
    "none",
    "feasibility",
    "descriptive",
    "associational",
    "quasi_experimental_suggestive",
    "limited_causal",
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def infer_claim_type_eligibility(spec: dict[str, Any]) -> str:
    """Conservative eligibility derived from extracted estimator/spec facts.

    Markers are matched against whole tokens, not substrings: a design marker
    like ``rd`` must be its own token, otherwise a variable named ``hardness``
    would be misread as a regression-discontinuity design and an associational
    OLS would be over-claimed as quasi-experimental.
    """
    estimator = str(spec.get("estimator", "")).strip().lower()
    formula = str(spec.get("formula", "")).strip().lower()
    if not estimator and not formula:
        return "none"
    estimator_tokens = set(re.findall(r"[a-z0-9]+", estimator))
    formula_tokens = set(re.findall(r"[a-z0-9]+", formula))
    causal_tokens = {"iv", "2sls", "did", "rd", "rdd"}
    # Concatenated IV class names (IV2SLS, IVGMM) are single tokens, so also
    # check controlled estimator substrings — but never substring-match the
    # formula (that is what mislabeled "hardness" as an RD design).
    causal_estimator_substrings = ("2sls", "ivgmm", "ivliml")
    causal_phrases = ("difference-in-differences", "event-study", "event_study", "regression discontinuity")
    is_causal = (
        bool(estimator_tokens & causal_tokens)
        or bool(formula_tokens & causal_tokens)
        or any(sub in estimator for sub in causal_estimator_substrings)
        or any(phrase in estimator or phrase in formula for phrase in causal_phrases)
    )
    if is_causal:
        return "quasi_experimental_suggestive"
    if any(marker in estimator for marker in ("ols", "feols", "panelols", "glm", "logit", "probit", "statsmodels")):
        return "associational"
    return "descriptive"


@dataclass(frozen=True)
class ResultRecord:
    result_id: str
    values: dict[str, Any] | list[Any]
    spec_id: str
    spec_extracted: dict[str, Any]
    code_ref: dict[str, Any]
    data_snapshot_hash: str
    run_event_id: str
    output_path: str = ""
    output_artifact_hash: str = ""
    claim_type_eligibility: str = ""
    adapter_name: str = "manual-adapter"
    adapter_version: str = "0"
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    notes: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any], root: Path) -> "ResultRecord":
        spec = _loads_mapping(payload.get("spec_extracted"))
        output_path = str(payload.get("output_path") or payload.get("output_artifact") or "").strip()
        output_hash = str(payload.get("output_artifact_hash") or "").strip()
        if output_path and not output_hash:
            full = root / output_path
            if full.exists() and full.is_file():
                output_hash = _sha256_file(full)
        eligibility = str(payload.get("claim_type_eligibility") or "").strip() or infer_claim_type_eligibility(spec)
        return cls(
            result_id=str(payload.get("result_id", "")).strip(),
            values=payload.get("values") or payload.get("value") or {},
            spec_id=str(payload.get("spec_id", "")).strip(),
            spec_extracted=spec,
            code_ref=_loads_mapping(payload.get("code_ref")),
            data_snapshot_hash=str(payload.get("data_snapshot_hash", "")).strip(),
            run_event_id=str(payload.get("run_event_id", "")).strip(),
            output_path=output_path,
            output_artifact_hash=output_hash,
            claim_type_eligibility=eligibility,
            adapter_name=str(payload.get("adapter_name", "manual-adapter")).strip() or "manual-adapter",
            adapter_version=str(payload.get("adapter_version", "0")).strip() or "0",
            registered_at=str(payload.get("registered_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")),
            notes=str(payload.get("notes", "")),
        )

    def validate(self, root: Path | None = None) -> list[str]:
        failures: list[str] = []
        if not self.result_id:
            failures.append("missing result_id")
        if not self.spec_id:
            failures.append(f"{self.result_id or '?'}: missing spec_id")
        if not self.values:
            failures.append(f"{self.result_id or '?'}: missing values")
        for key in ("estimator", "formula"):
            if not str(self.spec_extracted.get(key, "")).strip():
                failures.append(f"{self.result_id or '?'}: spec_extracted missing {key}")
        if not self.code_ref.get("file"):
            failures.append(f"{self.result_id or '?'}: code_ref missing file")
        if not self.data_snapshot_hash:
            failures.append(f"{self.result_id or '?'}: missing data_snapshot_hash")
        if not self.run_event_id:
            failures.append(f"{self.result_id or '?'}: missing run_event_id")
        if self.claim_type_eligibility not in ELIGIBILITY_ORDER:
            failures.append(f"{self.result_id or '?'}: invalid claim_type_eligibility {self.claim_type_eligibility!r}")
        if self.output_path and self.output_artifact_hash:
            full = Path(self.output_path)
            if not full.is_absolute() and root is not None:
                full = root / full
            if full.exists() and full.is_file():
                actual = _sha256_file(full)
                if actual != self.output_artifact_hash:
                    failures.append(f"{self.result_id or '?'}: output_artifact_hash mismatch for {self.output_path}")
        return failures

    def to_row(self) -> dict[str, str]:
        spec = self.spec_extracted
        return {
            "result_id": self.result_id,
            "values_json": _json(self.values),
            "spec_id": self.spec_id,
            "estimator": str(spec.get("estimator", "")),
            "formula": str(spec.get("formula", "")),
            "fixed_effects_json": _json(spec.get("fixed_effects", [])),
            "cluster_json": _json(spec.get("cluster", [])),
            "sample_filters_json": _json(spec.get("sample_filters", [])),
            "code_ref_json": _json(self.code_ref),
            "data_snapshot_hash": self.data_snapshot_hash,
            "run_event_id": self.run_event_id,
            "output_path": self.output_path,
            "output_artifact_hash": self.output_artifact_hash,
            "claim_type_eligibility": self.claim_type_eligibility,
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "registered_at": self.registered_at,
            "notes": self.notes,
        }


def record_from_row(row: dict[str, str]) -> ResultRecord:
    spec = {
        "estimator": row.get("estimator", ""),
        "formula": row.get("formula", ""),
        "fixed_effects": json.loads(row.get("fixed_effects_json") or "[]"),
        "cluster": json.loads(row.get("cluster_json") or "[]"),
        "sample_filters": json.loads(row.get("sample_filters_json") or "[]"),
    }
    return ResultRecord(
        result_id=row.get("result_id", ""),
        values=json.loads(row.get("values_json") or "{}"),
        spec_id=row.get("spec_id", ""),
        spec_extracted=spec,
        code_ref=json.loads(row.get("code_ref_json") or "{}"),
        data_snapshot_hash=row.get("data_snapshot_hash", ""),
        run_event_id=row.get("run_event_id", ""),
        output_path=row.get("output_path", ""),
        output_artifact_hash=row.get("output_artifact_hash", ""),
        claim_type_eligibility=row.get("claim_type_eligibility", ""),
        adapter_name=row.get("adapter_name", ""),
        adapter_version=row.get("adapter_version", ""),
        registered_at=row.get("registered_at", ""),
        notes=row.get("notes", ""),
    )


def read_registry(root: Path) -> list[dict[str, str]]:
    path = root / RESULT_REGISTRY
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def upsert_record(root: Path, record: ResultRecord, *, dry_run: bool = False) -> Path:
    failures = record.validate(root)
    if failures:
        raise ValueError("; ".join(failures))
    path = root / RESULT_REGISTRY
    existing = read_registry(root)
    rows = [row for row in existing if row.get("result_id") != record.result_id]
    rows.append(record.to_row())
    rows.sort(key=lambda row: row.get("result_id", ""))
    if dry_run:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def register_payload(root: Path, payload: dict[str, Any], *, dry_run: bool = False) -> tuple[Path, ResultRecord]:
    """Register an in-memory payload dict (e.g. from an estimation adapter)."""
    if not isinstance(payload, dict):
        raise ValueError("result registry payload must be a JSON object")
    record = ResultRecord.from_payload(payload, root)
    path = upsert_record(root, record, dry_run=dry_run)
    return path, record


def register_payload_file(root: Path, payload_path: Path, *, dry_run: bool = False) -> tuple[Path, ResultRecord]:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    return register_payload(root, payload, dry_run=dry_run)


def sync_result_index(root: Path, *, dry_run: bool = False, backup: bool = True) -> tuple[Path, int]:
    """Derive result_index rows from the registry without destroying the index.

    The index is frequently hand-curated (extra columns like description,
    created_date, notes, and rows that predate the registry). This sync is
    therefore a non-destructive merge:
      - every existing column is preserved (the output schema is the union of the
        index's own header and the derived RESULT_INDEX_FIELDS),
      - existing rows are kept even if they have no registry row yet,
      - for ids present in the registry, only the derived fields are refreshed;
        hand-entered columns on the same row are left untouched,
      - the previous index is copied to a timestamped .bak before overwrite.
    """
    registry = read_registry(root)
    path = root / RESULT_INDEX
    existing_rows: list[dict[str, str]] = []
    existing_fields: list[str] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            existing_fields = list(reader.fieldnames or [])
            existing_rows = [dict(row) for row in reader]
    # Output schema = existing columns first (order preserved), then any derived
    # field the index does not already carry. Never drop a column.
    out_fields = list(existing_fields)
    for field_name in RESULT_INDEX_FIELDS:
        if field_name not in out_fields:
            out_fields.append(field_name)
    by_id: dict[str, dict[str, str]] = {
        row.get("result_id", ""): row for row in existing_rows if row.get("result_id")
    }
    for row in registry:
        result_id = row.get("result_id", "")
        if not result_id:
            continue
        code_ref = json.loads(row.get("code_ref_json") or "{}")
        entry = by_id.get(result_id, {})
        # Refresh only the registry-owned (derived) fields; preserve curated ones.
        entry["result_id"] = result_id
        entry["path"] = row.get("output_path", "") or entry.get("path", "")
        entry["script_or_source"] = (
            str(code_ref.get("file") or row.get("adapter_name") or "")
            or entry.get("script_or_source", "")
        )
        entry.setdefault("linked_claims", "")
        by_id[result_id] = entry
    rows = [by_id[key] for key in sorted(by_id)]
    if dry_run:
        return path, len(registry)
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(path, path.with_name(f"{path.name}.bak.{stamp}"))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field_name: row.get(field_name, "") for field_name in out_fields})
    return path, len(registry)
