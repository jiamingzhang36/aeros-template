"""Estimation adapters: introspect fitted model objects into registry payloads.

The result adapter contract (harness/result_adapter_contract.yml) states that
result numbers should be *born* from fit-object introspection, not hand-copied
from prose. Until this module existed the contract was declarative only and every
record was typed by hand — which is exactly the "agent prose" the contract bans.

This implements the ``python_statsmodels`` adapter. It duck-types the results
object (``params`` / ``bse`` / ``pvalues`` indexed by term, ``model``, ``nobs``,
``cov_type`` / ``cov_kwds``) so statsmodels itself need not be importable here and
the adapter can be unit-tested with a lightweight fake fit.

What the adapter records is *what was run*. It never certifies identification or
approves a claim — that boundary stays with the harness and the human gate.
"""
from __future__ import annotations

import re
from typing import Any

ADAPTER_NAME = "python_statsmodels"
ADAPTER_VERSION = "1"

# Terms that are model scaffolding rather than substantive coefficients.
_NON_SUBSTANTIVE = {"intercept", "const"}


def _native(value: Any) -> Any:
    """Coerce numpy scalars / pandas values to plain Python numbers."""
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except (ValueError, TypeError):
            pass
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


def _series_get(series: Any, term: str) -> Any:
    """Read series[term] for a pandas Series or a plain mapping."""
    try:
        return series[term]
    except (KeyError, TypeError, IndexError):
        getter = getattr(series, "get", None)
        return getter(term) if callable(getter) else None


def _terms(fit: Any) -> list[str]:
    params = getattr(fit, "params", None)
    index = getattr(params, "index", None)
    if index is not None:
        return [str(t) for t in index]
    if isinstance(params, dict):
        return [str(t) for t in params]
    return []


def _formula(model: Any) -> str:
    formula = getattr(model, "formula", None)
    return str(formula) if formula else ""


def _fixed_effects(formula: str) -> list[str]:
    """Best-effort: treat C(<var>) absorption terms in the formula as fixed
    effects. This is a heuristic, not a guarantee — callers may override by
    passing ``fixed_effects`` explicitly."""
    return sorted(set(re.findall(r"C\(\s*([A-Za-z_]\w*)\s*\)", formula or "")))


def _cluster(fit: Any) -> list[str]:
    cov_type = str(getattr(fit, "cov_type", "") or "")
    if "cluster" not in cov_type.lower():
        return []
    cov_kwds = getattr(fit, "cov_kwds", None) or {}
    groups = cov_kwds.get("groups") if isinstance(cov_kwds, dict) else None
    name = getattr(groups, "name", None)
    if name:
        return [str(name)]
    cols = getattr(groups, "columns", None)
    if cols is not None:
        return [str(c) for c in cols]
    return ["cluster"]


def _values_for_term(fit: Any, term: str) -> dict[str, Any]:
    nobs = getattr(fit, "nobs", None)
    return {
        "coefficient": _native(_series_get(getattr(fit, "params", {}), term)),
        "standard_error": _native(_series_get(getattr(fit, "bse", {}), term)),
        "p_value": _native(_series_get(getattr(fit, "pvalues", {}), term)),
        "n": int(nobs) if nobs is not None else 0,
    }


def payload_from_statsmodels(
    fit: Any,
    *,
    result_id: str,
    spec_id: str,
    data_snapshot_hash: str,
    run_event_id: str,
    term: str | None = None,
    code_ref: dict[str, Any] | None = None,
    output_path: str = "",
    output_artifact_hash: str = "",
    fixed_effects: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Build a result-registry payload by introspecting a fitted statsmodels result.

    ``term`` selects a single coefficient (the common paper case). When omitted,
    every substantive term is emitted as a ``{term: {coefficient, ...}}`` mapping.
    The returned dict is accepted by ``ResultRecord.from_payload`` /
    ``register_payload``.
    """
    model = getattr(fit, "model", None)
    estimator = type(model).__name__ if model is not None else type(fit).__name__
    formula = _formula(model)
    fe = fixed_effects if fixed_effects is not None else _fixed_effects(formula)

    if term is not None:
        values: dict[str, Any] = _values_for_term(fit, term)
    else:
        values = {
            t: _values_for_term(fit, t)
            for t in _terms(fit)
            if t.lower() not in _NON_SUBSTANTIVE
        }

    return {
        "result_id": result_id,
        "values": values,
        "spec_id": spec_id,
        "spec_extracted": {
            "estimator": estimator,
            "formula": formula,
            "fixed_effects": fe,
            "cluster": _cluster(fit),
            "sample_filters": [],
        },
        "code_ref": code_ref or {},
        "data_snapshot_hash": data_snapshot_hash,
        "run_event_id": run_event_id,
        "output_path": output_path,
        "output_artifact_hash": output_artifact_hash,
        "adapter_name": ADAPTER_NAME,
        "adapter_version": ADAPTER_VERSION,
        "notes": notes,
    }
