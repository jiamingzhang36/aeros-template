"""Human-gated claim upgrade recommendation.

This module automates the review packet, not the upgrade itself. It may
recommend language and required next actions, but it never writes
evidence/claim_registry.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .claim_vector import ClaimVector, compile_claim_vector, format_claim_vector


@dataclass(frozen=True)
class ClaimUpgradeReview:
    claim_id: str
    recommendation: str
    authority_status: str
    required_human_gate: bool
    claim_vector: ClaimVector
    proposed_registry_action: str
    packet_path: str
    does_not_prove: tuple[str, ...] = (
        "scientific truth",
        "claim support",
        "gate approval",
        "paper readiness",
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["claim_vector"] = self.claim_vector.to_dict()
        data["does_not_prove"] = list(self.does_not_prove)
        return data


def review_claim_upgrade(
    root: Path,
    *,
    claim_id: str,
    evidence_status: str = "none",
    identification_level: str = "none",
    result_admission_status: str = "not_admitted",
    validation_status: str = "unvalidated",
) -> ClaimUpgradeReview:
    vector = compile_claim_vector(
        claim_id=claim_id,
        evidence_status=evidence_status,
        identification_level=identification_level,
        result_admission_status=result_admission_status,
        validation_status=validation_status,
    )
    if vector.claim_ceiling in {"associational", "descriptive", "causal_candidate"}:
        recommendation = "eligible_for_human_upgrade_review"
        proposed = "open human gate review; do not mutate claim registry automatically"
    elif vector.claim_ceiling == "contradiction_or_rejection":
        recommendation = "route_to_human_downgrade_or_revision_review"
        proposed = "open human revision review; do not mutate claim registry automatically"
    else:
        recommendation = "do_not_upgrade"
        proposed = "collect/admit evidence before registry change"
    packet_path = f"decisions/claim_upgrade/{claim_id}_upgrade_review.md"
    return ClaimUpgradeReview(
        claim_id=vector.claim_id,
        recommendation=recommendation,
        authority_status="recommendation_only",
        required_human_gate=True,
        claim_vector=vector,
        proposed_registry_action=proposed,
        packet_path=packet_path,
    )


def format_claim_upgrade_review(review: ClaimUpgradeReview) -> str:
    lines = [
        f"# Claim Upgrade Review: {review.claim_id}",
        "",
        f"- recommendation: {review.recommendation}",
        f"- authority_status: {review.authority_status}",
        f"- required_human_gate: {str(review.required_human_gate).lower()}",
        f"- proposed_registry_action: {review.proposed_registry_action}",
        "",
        "## ClaimVector",
        "",
        "```text",
        format_claim_vector(review.claim_vector),
        "```",
        "",
        "## Boundary",
        "",
        "This review does not modify evidence/claim_registry.md and does not approve any gate.",
        "",
        "does_not_prove:",
    ]
    lines.extend(f"- {item}" for item in review.does_not_prove)
    return "\n".join(lines)


def write_claim_upgrade_review(root: Path, review: ClaimUpgradeReview) -> Path:
    path = root / review.packet_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_claim_upgrade_review(review) + "\n", encoding="utf-8")
    return path
