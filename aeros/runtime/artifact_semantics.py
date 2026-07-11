"""Orthogonal artifact-state semantics and legacy output-intent projection."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

SELECTION = {"lead", "candidate", "accepted", "rejected"}
PROCESSING = {"raw", "staging", "intermediate", "processed"}
ADMISSION = {"nonproduction", "canonical_candidate", "canonical", "result_eligible", "claim_review_eligible"}

LEGACY_OUTPUT_INTENT_MAP = {
    "lead_queue": ("lead", "raw", "nonproduction"),
    "candidate_queue": ("candidate", "raw", "nonproduction"),
    "probe_only": ("accepted", "staging", "nonproduction"),
    "staging_artifact": ("accepted", "staging", "nonproduction"),
    "canonical_candidate": ("accepted", "processed", "canonical_candidate"),
    "canonical_update": ("accepted", "processed", "canonical"),
    "audit_note": ("accepted", "staging", "nonproduction"),
}


@dataclass(frozen=True)
class ArtifactSemantics:
    selection_status: str
    processing_stage: str
    admission_status: str
    source: str = "declared"

    def to_dict(self) -> dict[str, str]:
        return self.__dict__.copy()


def compile_legacy_output_intent(intent: str) -> ArtifactSemantics:
    values = LEGACY_OUTPUT_INTENT_MAP.get(str(intent or "").strip())
    if not values:
        raise ValueError(f"unknown legacy output_intent {intent!r}")
    return ArtifactSemantics(*values, source="compiled_from_output_intent")


def parse_artifact_semantics(data: dict[str, Any], legacy_intent: str = "") -> ArtifactSemantics:
    if not any(data.get(k) for k in ("selection_status", "processing_stage", "admission_status")):
        return compile_legacy_output_intent(legacy_intent)
    result = ArtifactSemantics(
        str(data.get("selection_status") or "").strip(),
        str(data.get("processing_stage") or "").strip(),
        str(data.get("admission_status") or "").strip(),
    )
    failures = validate_artifact_semantics(result)
    if failures:
        raise ValueError("; ".join(failures))
    return result


def validate_artifact_semantics(value: ArtifactSemantics) -> list[str]:
    failures: list[str] = []
    if value.selection_status not in SELECTION:
        failures.append(f"invalid selection_status {value.selection_status!r}")
    if value.processing_stage not in PROCESSING:
        failures.append(f"invalid processing_stage {value.processing_stage!r}")
    if value.admission_status not in ADMISSION:
        failures.append(f"invalid admission_status {value.admission_status!r}")
    if value.selection_status == "rejected" and value.admission_status != "nonproduction":
        failures.append("rejected artifacts must remain nonproduction")
    if value.admission_status in {"canonical", "result_eligible", "claim_review_eligible"} and value.processing_stage != "processed":
        failures.append("authoritative admission requires processing_stage=processed")
    return failures

