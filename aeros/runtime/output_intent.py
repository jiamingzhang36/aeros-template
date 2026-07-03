"""Output intent validation for staging/canonical boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract import Contract


VALID_OUTPUT_INTENTS = {
    "probe_only",
    "lead_queue",
    "candidate_queue",
    "staging_artifact",
    "canonical_candidate",
    "canonical_update",
    "audit_note",
}

DOES_NOT_PROVE = [
    "that an output exists",
    "that an output is admissible evidence",
    "that a canonical candidate should be promoted",
    "that a gate is approved",
]


def contract_output_intents(contract: Contract) -> dict[str, str]:
    raw = contract.raw.get("output_intents") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(path).strip(): str(intent).strip() for path, intent in raw.items() if str(path).strip()}


def validate_output_intents(contract: Contract) -> list[str]:
    failures: list[str] = []
    intents = contract_output_intents(contract)
    for path, intent in intents.items():
        if intent not in VALID_OUTPUT_INTENTS:
            failures.append(f"{contract.task_id}: output {path!r} has invalid output_intent {intent!r}")
    for path in intents:
        if path not in contract.allowed_outputs and not any(str(path).startswith(prefix.rstrip("/") + "/") for prefix in contract.allowed_outputs):
            failures.append(f"{contract.task_id}: output_intent path {path!r} is not listed in allowed_outputs")
    return failures


def validate_all_output_intents(_root: Path, contracts: dict[str, tuple[Contract, Path]]) -> list[str]:
    failures: list[str] = []
    for _task_id, (contract, _path) in sorted(contracts.items()):
        failures.extend(validate_output_intents(contract))
    return failures
