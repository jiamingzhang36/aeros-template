"""Advisory ClaimVector compiler.

ClaimVector is a language-boundary compiler, not a claim adjudicator. It maps
current evidence/admission/identification inputs to allowed and forbidden claim
language, and it always leaves formal claim upgrades to the human gate and
claim registry workflow.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


EVIDENCE_STATUSES = {"none", "candidate_support", "admitted_support", "contradicts"}
IDENTIFICATION_LEVELS = {"none", "descriptive", "associational", "causal"}
ADMISSION_STATUSES = {"not_admitted", "needs_review", "human_admitted", "rejected"}
VALIDATION_STATUSES = {"unvalidated", "validated", "robust"}


@dataclass(frozen=True)
class ClaimVector:
    claim_id: str
    evidence_status: str
    identification_level: str
    result_admission_status: str
    validation_status: str
    claim_ceiling: str
    allowed_language: tuple[str, ...]
    forbidden_language: tuple[str, ...]
    upgrade_recommendation: str
    required_human_gate: bool = True
    authority_status: str = "advisory_only"
    does_not_prove: tuple[str, ...] = field(default_factory=lambda: (
        "scientific truth",
        "claim support",
        "gate approval",
        "paper readiness",
    ))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("allowed_language", "forbidden_language", "does_not_prove"):
            data[key] = list(data[key])
        return data


def _validate_choice(name: str, value: str, allowed: set[str]) -> str:
    value = (value or "").strip() or "none"
    if value not in allowed:
        raise ValueError(f"{name} must be one of {sorted(allowed)}; got {value!r}")
    return value


def compile_claim_vector(
    *,
    claim_id: str,
    evidence_status: str = "none",
    identification_level: str = "none",
    result_admission_status: str = "not_admitted",
    validation_status: str = "unvalidated",
) -> ClaimVector:
    claim_id = (claim_id or "").strip() or "CANDIDATE"
    evidence_status = _validate_choice("evidence_status", evidence_status, EVIDENCE_STATUSES)
    identification_level = _validate_choice("identification_level", identification_level, IDENTIFICATION_LEVELS)
    result_admission_status = _validate_choice("result_admission_status", result_admission_status, ADMISSION_STATUSES)
    validation_status = _validate_choice("validation_status", validation_status, VALIDATION_STATUSES)

    forbidden = {
        "proves",
        "paper-ready",
        "establishes",
        "demonstrates definitively",
        "is supported",
    }
    allowed: list[str] = []
    ceiling = "no_claim"
    recommendation = "do not upgrade; collect/admit evidence first"

    if result_admission_status == "rejected" or evidence_status == "contradicts":
        ceiling = "contradiction_or_rejection"
        allowed = ["evidence contradicts or fails to admit the claim", "claim requires revision or withdrawal review"]
        forbidden.update({"confirms", "supports", "causes", "effect", "impact"})
        recommendation = "route to human claim-revision review"
    elif result_admission_status != "human_admitted":
        ceiling = "candidate_only"
        allowed = ["candidate evidence may suggest", "requires evidence admission before use"]
        forbidden.update({"supports", "supported", "causes", "effect", "impact", "robustly shows"})
        recommendation = "request ResultAdmission before any claim upgrade"
    elif evidence_status not in {"candidate_support", "admitted_support"}:
        ceiling = "admitted_context_only"
        allowed = ["provides context for", "is consistent with background discussion"]
        forbidden.update({"supports", "causes", "effect", "impact"})
        recommendation = "do not upgrade; admitted evidence is not support-bearing"
    elif identification_level in {"none", "descriptive"}:
        ceiling = "descriptive"
        allowed = ["describes", "is observed in", "is consistent with descriptive evidence"]
        forbidden.update({"causes", "effect", "impact", "identifies"})
        recommendation = "eligible only for human descriptive-claim review"
    elif identification_level == "associational":
        ceiling = "associational"
        allowed = ["is associated with", "is correlated with", "suggests a relationship with"]
        forbidden.update({"causes", "caused by", "effect", "impact", "identifies"})
        recommendation = "eligible for human associational-claim review"
    else:
        ceiling = "causal_candidate" if validation_status in {"validated", "robust"} else "causal_design_unvalidated"
        allowed = ["is consistent with a causal interpretation", "under the stated design, estimates an effect of"]
        forbidden.update({"proves causality", "definitively causes", "paper-ready"})
        recommendation = "eligible for human causal-claim review; do not auto-upgrade"

    return ClaimVector(
        claim_id=claim_id,
        evidence_status=evidence_status,
        identification_level=identification_level,
        result_admission_status=result_admission_status,
        validation_status=validation_status,
        claim_ceiling=ceiling,
        allowed_language=tuple(allowed),
        forbidden_language=tuple(sorted(forbidden)),
        upgrade_recommendation=recommendation,
    )


def format_claim_vector(vector: ClaimVector) -> str:
    lines = [
        f"claim_id: {vector.claim_id}",
        f"authority_status: {vector.authority_status}",
        f"claim_ceiling: {vector.claim_ceiling}",
        f"upgrade_recommendation: {vector.upgrade_recommendation}",
        f"required_human_gate: {str(vector.required_human_gate).lower()}",
        "allowed_language:",
    ]
    lines.extend(f"- {item}" for item in vector.allowed_language)
    lines.append("forbidden_language:")
    lines.extend(f"- {item}" for item in vector.forbidden_language)
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in vector.does_not_prove)
    return "\n".join(lines)
