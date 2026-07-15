#!/usr/bin/env python3
"""Validate one candidate specification result/exhibit pair before copyback."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _terms(raw: str) -> list[str]:
    if str(raw or "").strip().lower() in {"", "none", "na", "n/a"}:
        return []
    return [item.strip() for item in re.split(r"[;,|]", str(raw)) if item.strip()]


def _finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_specification_run(
    result_path: Path,
    exhibit_path: Path,
    *,
    source_path: Path | None = None,
    registry_path: Path | None = None,
    spec_id: str = "",
) -> list[str]:
    failures: list[str] = []
    if not result_path.is_file():
        return [f"missing result: {result_path}"]
    if not exhibit_path.is_file():
        return [f"missing exhibit: {exhibit_path}"]
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid result JSON: {exc}"]
    if not isinstance(payload, dict):
        return ["result JSON must be an object"]
    if payload.get("status") != "candidate_result":
        failures.append("result status must be candidate_result")
    if payload.get("admission_status") != "nonproduction":
        failures.append("admission_status must be nonproduction")
    result_id = str(payload.get("result_id") or "").strip()
    if not result_id:
        failures.append("result_id is missing")
    specification = payload.get("specification") or {}
    observed_spec_id = str(specification.get("spec_id") or "").strip()
    if not observed_spec_id:
        failures.append("specification.spec_id is missing")
    if spec_id and observed_spec_id != spec_id:
        failures.append(f"specification ID mismatch: {observed_spec_id} != {spec_id}")
    sample = payload.get("sample") or {}
    try:
        n_input = int(sample.get("n_input"))
        n_used = int(sample.get("n_used"))
        dropped = int(sample.get("dropped_missing_or_nonnumeric"))
    except (TypeError, ValueError):
        n_input = n_used = dropped = -1
        failures.append("sample counts must be integers")
    if n_used <= 0 or n_input < n_used or dropped != n_input - n_used:
        failures.append("sample counts are inconsistent")
    source = source_path or Path(str(sample.get("source") or ""))
    if not source.is_file():
        failures.append(f"source snapshot is missing: {source}")
    else:
        observed_hash = sha256(source.read_bytes()).hexdigest()
        if observed_hash != str(sample.get("source_sha256") or ""):
            failures.append("source hash does not match result sample snapshot")
    if registry_path is not None:
        if not registry_path.is_file():
            failures.append(f"specification registry is missing: {registry_path}")
        else:
            with registry_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                rows = [row for row in csv.DictReader(handle) if str(row.get("spec_id") or "").strip() == observed_spec_id]
            if len(rows) != 1:
                failures.append("specification registry must contain exactly one matching row")
            else:
                row = rows[0]
                expected = {
                    "estimator": str(row.get("estimator") or "").strip().lower(),
                    "outcome": str(row.get("outcome") or "").strip(),
                    "treatment": str(row.get("treatment") or "").strip(),
                    "controls": _terms(str(row.get("controls") or "")),
                    "fixed_effects": str(row.get("fixed_effects") or "none").strip().lower() or "none",
                    "cluster": str(row.get("cluster") or "none").strip().lower() or "none",
                    "weights": str(row.get("weights") or "none").strip().lower() or "none",
                }
                for key, value in expected.items():
                    observed = specification.get(key)
                    if key != "controls":
                        observed = str(observed or "").strip().lower()
                    if observed != value:
                        failures.append(f"specification snapshot mismatch for {key}")
    coefficients = ((payload.get("result") or {}).get("coefficients") or {})
    if not isinstance(coefficients, dict) or not coefficients:
        failures.append("result coefficients are missing")
        coefficients = {}
    for term, values in coefficients.items():
        if not isinstance(values, dict) or not _finite(values.get("estimate")) or not _finite(values.get("std_error")):
            failures.append(f"coefficient {term} is incomplete or non-finite")
    result_block = payload.get("result") or {}
    if not _finite(result_block.get("sse")) or float(result_block.get("sse", -1)) < 0:
        failures.append("SSE must be finite and non-negative")
    if result_block.get("r_squared") is not None and not _finite(result_block.get("r_squared")):
        failures.append("R-squared must be finite or null")
    try:
        with exhibit_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            exhibit_rows = list(csv.DictReader(handle))
    except OSError as exc:
        failures.append(f"cannot read exhibit: {exc}")
        exhibit_rows = []
    required_columns = {"result_id", "spec_id", "term", "estimate", "std_error", "n"}
    if exhibit_rows and not required_columns <= set(exhibit_rows[0]):
        failures.append("exhibit is missing required columns")
    if len(exhibit_rows) != len(coefficients):
        failures.append("exhibit row count does not match coefficient count")
    seen_terms: set[str] = set()
    for row in exhibit_rows:
        term = str(row.get("term") or "")
        if term in seen_terms:
            failures.append(f"duplicate exhibit term: {term}")
        seen_terms.add(term)
        if row.get("result_id") != result_id or row.get("spec_id") != observed_spec_id:
            failures.append(f"exhibit identity mismatch for term {term}")
        values = coefficients.get(term) or {}
        if not values:
            failures.append(f"exhibit term missing from result: {term}")
            continue
        if not _finite(row.get("estimate")) or not _finite(row.get("std_error")):
            failures.append(f"exhibit values are non-finite for term {term}")
        else:
            if abs(float(row["estimate"]) - float(values["estimate"])) > 1e-10:
                failures.append(f"estimate mismatch for term {term}")
            if abs(float(row["std_error"]) - float(values["std_error"])) > 1e-10:
                failures.append(f"standard-error mismatch for term {term}")
        try:
            if int(row.get("n") or -1) != n_used:
                failures.append(f"sample-size mismatch for term {term}")
        except ValueError:
            failures.append(f"invalid exhibit sample size for term {term}")
    if set(coefficients) != seen_terms:
        failures.append("result and exhibit term sets differ")
    if str(payload.get("candidate_exhibit") or "") != exhibit_path.as_posix():
        failures.append("candidate_exhibit path does not match validated exhibit")
    if not isinstance(payload.get("does_not_prove"), list) or not payload.get("does_not_prove"):
        failures.append("does_not_prove boundary is missing")
    return failures


def _self_fixture() -> list[str]:
    from aeros.runtime.job_actions import run_specification

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_spec_validator_") as name:
        root = Path(name)
        source = root / "sample.csv"
        registry = root / "registry.csv"
        result = root / "result.json"
        exhibit = root / "exhibit.csv"
        source.write_text("y,d\n1,0\n3,1\n5,2\n7,3\n", encoding="utf-8")
        registry.write_text(
            "spec_id,estimand_id,sample_id,outcome,treatment,controls,fixed_effects,cluster,weights,window,estimator,software,package_versions,protocol,status\n"
            "SP1,E1,S1,y,d,none,none,none,none,all,ols,python,stdlib,none,registered\n",
            encoding="utf-8",
        )
        if run_specification(source, registry, "SP1", result, exhibit) != 0:
            return ["fixture specification did not run"]
        failures.extend(validate_specification_run(result, exhibit, source_path=source, registry_path=registry, spec_id="SP1"))
        rows = list(csv.DictReader(exhibit.read_text(encoding="utf-8").splitlines()))
        rows[0]["result_id"] = "tampered"
        with exhibit.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        if not validate_specification_run(result, exhibit, source_path=source, registry_path=registry, spec_id="SP1"):
            failures.append("tampered exhibit was not rejected")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result")
    parser.add_argument("--exhibit")
    parser.add_argument("--source")
    parser.add_argument("--registry")
    parser.add_argument("--spec-id", default="")
    args = parser.parse_args()
    if any([args.result, args.exhibit, args.source, args.registry, args.spec_id]):
        if not all([args.result, args.exhibit, args.source, args.registry, args.spec_id]):
            failures = ["result, exhibit, source, registry, and spec-id must be supplied together"]
        else:
            failures = validate_specification_run(
                Path(args.result),
                Path(args.exhibit),
                source_path=Path(args.source),
                registry_path=Path(args.registry),
                spec_id=args.spec_id,
            )
    else:
        failures = _self_fixture()
    if failures:
        print("FAIL: candidate specification run is not internally consistent")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: candidate specification result and exhibit are internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
