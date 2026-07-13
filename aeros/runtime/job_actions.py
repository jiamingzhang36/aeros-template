"""Deterministic local actions emitted by the ResearchJob compiler."""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys


def data_probe(source: Path, output: Path, target: str) -> int:
    if not source.is_file():
        return 2
    digest = sha256(source.read_bytes()).hexdigest()
    rows = 0
    columns: list[str] = []
    if source.suffix.lower() in {".csv", ".tsv"}:
        delimiter = "\t" if source.suffix.lower() == ".tsv" else ","
        with source.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            try:
                columns = [str(x) for x in next(reader)]
            except StopIteration:
                columns = []
            rows = sum(1 for _ in reader)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "model": "AEROS-RESEARCH-JOB-DATA-PROBE-001",
        "target": target,
        "source": str(source),
        "source_sha256": digest,
        "rows_observed": rows,
        "columns_observed": columns,
        "status": "probe_observed",
        "does_not_prove": ["data fitness", "canonical admission", "claim support"],
    }, indent=2) + "\n", encoding="utf-8")
    return 0


def _terms(raw: str) -> list[str]:
    if str(raw or "").strip().lower() in {"", "none", "na", "n/a"}:
        return []
    return [item.strip() for item in re.split(r"[;,|]", str(raw)) if item.strip()]


def _meaningful(raw: str) -> bool:
    return str(raw or "").strip().lower() not in {"", "none", "na", "n/a", "no"}


def _invert(matrix: list[list[float]]) -> list[list[float]]:
    n = len(matrix)
    augmented = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            raise ValueError("design matrix is singular")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        scale = augmented[col][col]
        augmented[col] = [value / scale for value in augmented[col]]
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            augmented[row] = [value - factor * base for value, base in zip(augmented[row], augmented[col])]
    return [row[n:] for row in augmented]


def run_specification(source: Path, registry: Path, spec_id: str, output: Path, exhibit: Path) -> int:
    if not source.is_file() or source.suffix.lower() != ".csv" or not registry.is_file():
        return 2
    with registry.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        specs = [row for row in csv.DictReader(handle) if str(row.get("spec_id", "")).strip() == spec_id]
    if len(specs) != 1:
        return 3
    spec = specs[0]
    estimator = str(spec.get("estimator", "")).strip().lower()
    if estimator not in {"ols", "linear_ols"}:
        return 4
    unsupported = [field for field in ("fixed_effects", "cluster", "weights") if _meaningful(str(spec.get(field, "")))]
    if unsupported:
        return 5
    outcome = str(spec.get("outcome", "")).strip()
    treatment = str(spec.get("treatment", "")).strip()
    controls = _terms(str(spec.get("controls", "")))
    variables = [treatment, *controls]
    if not outcome or not treatment or len(set(variables)) != len(variables):
        return 6
    x_rows: list[list[float]] = []
    y_values: list[float] = []
    n_input = 0
    with source.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {outcome, *variables} <= set(reader.fieldnames or []):
            return 7
        for row in reader:
            n_input += 1
            try:
                y = float(str(row[outcome]).strip())
                x = [1.0, *[float(str(row[name]).strip()) for name in variables]]
            except (TypeError, ValueError):
                continue
            if not all(math.isfinite(value) for value in [y, *x]):
                continue
            y_values.append(y)
            x_rows.append(x)
    n = len(y_values)
    k = len(variables) + 1
    if n <= k:
        return 8
    xtx = [[sum(row[i] * row[j] for row in x_rows) for j in range(k)] for i in range(k)]
    xty = [sum(row[i] * y for row, y in zip(x_rows, y_values)) for i in range(k)]
    try:
        inverse = _invert(xtx)
    except ValueError:
        return 9
    beta = [sum(inverse[i][j] * xty[j] for j in range(k)) for i in range(k)]
    fitted = [sum(value * coefficient for value, coefficient in zip(row, beta)) for row in x_rows]
    residuals = [actual - predicted for actual, predicted in zip(y_values, fitted)]
    degrees_freedom = n - k
    sse = sum(value * value for value in residuals)
    sigma2 = sse / degrees_freedom
    std_errors = [math.sqrt(max(0.0, sigma2 * inverse[i][i])) for i in range(k)]
    mean_y = sum(y_values) / n
    tss = sum((value - mean_y) ** 2 for value in y_values)
    r_squared = 1.0 - sse / tss if tss > 0 else None
    source_hash = sha256(source.read_bytes()).hexdigest()
    terms = ["intercept", *variables]
    coefficients = {
        term: {"estimate": beta[index], "std_error": std_errors[index]}
        for index, term in enumerate(terms)
    }
    result_id = f"R-CAND-{spec_id}-{source_hash[:8]}"
    payload = {
        "model": "AEROS-RUN-SPECIFICATION-001",
        "status": "candidate_result",
        "admission_status": "nonproduction",
        "result_id": result_id,
        "sample": {"source": str(source), "source_sha256": source_hash, "n_input": n_input, "n_used": n, "dropped_missing_or_nonnumeric": n_input - n},
        "specification": {"spec_id": spec_id, "estimator": estimator, "outcome": outcome, "treatment": treatment, "controls": controls, "fixed_effects": "none", "cluster": "none", "weights": "none"},
        "run_record": {"executor": "python_stdlib_ols", "python_version": sys.version.split()[0], "degrees_freedom": degrees_freedom},
        "result": {"coefficients": coefficients, "r_squared": r_squared, "sse": sse},
        "diagnostics": {"matrix_full_rank": True, "homoskedastic_standard_errors_only": True, "unsupported_features_rejected": ["fixed_effects", "cluster", "weights"]},
        "candidate_exhibit": str(exhibit),
        "does_not_prove": ["causal identification", "specification validity", "canonical Result admission", "claim support", "paper readiness"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    exhibit.parent.mkdir(parents=True, exist_ok=True)
    with exhibit.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["result_id", "spec_id", "term", "estimate", "std_error", "n"])
        writer.writeheader()
        for term in terms:
            writer.writerow({"result_id": result_id, "spec_id": spec_id, "term": term, "estimate": coefficients[term]["estimate"], "std_error": coefficients[term]["std_error"], "n": n})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["data-probe", "run-specification"])
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--spec-id", default="")
    parser.add_argument("--exhibit", default="")
    args = parser.parse_args()
    if args.action == "data-probe":
        return data_probe(Path(args.source), Path(args.output), args.target) if args.target else 2
    if not args.registry or not args.spec_id or not args.exhibit:
        return 2
    return run_specification(Path(args.source), Path(args.registry), args.spec_id, Path(args.output), Path(args.exhibit))


if __name__ == "__main__":
    raise SystemExit(main())
