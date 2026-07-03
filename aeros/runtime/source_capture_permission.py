"""Permission tiering for source capture work.

This module separates low-risk public staging capture from work that needs a
route-level or human approval. It is advisory guardrail logic, not a fetcher and
not evidence admission.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


POLICY_PATH = Path("harness/source_capture_permission_policy.yml")

GREEN_INTENTS = {"probe_only", "staging_artifact", "audit_note"}
YELLOW_INTENTS = {"canonical_candidate"}
RED_INTENTS = {"canonical_update"}

RED_PATH_MARKERS = (
    "data/raw/",
    "evidence/claim_registry",
    "docs/protected_definitions",
    "decisions/approvals/",
    "decisions/decision_log",
    "paper/",
    "replication/",
    "compliance/",
)

STAGING_PATH_MARKERS = (
    "work/",
    "source_snapshots/",
    "audits/",
    "quality_reports/",
    "outputs/context/",
    "evidence/delta_log.jsonl",
)

RED_TEXT_MARKERS = (
    "api key",
    "apikey",
    "credential",
    "login",
    "password",
    "paid",
    "paywall",
    "nielsen",
    "private",
    "irb",
    "personal data",
    "pii",
    "tos",
    "robots",
    "redistribution",
    "public release",
    "canonical update",
)

YELLOW_TEXT_MARKERS = (
    "batch",
    "many pages",
    "portal",
    "chrome",
    "browser",
    "scrape",
    "crawl",
    "rate limit",
    "captcha",
    "cloudflare",
    "canonical candidate",
)

GREEN_TEXT_MARKERS = (
    "public",
    "official",
    "openalex",
    "zotero",
    "local pdf",
    "doi",
    "metadata",
    "snapshot",
    "source",
)

DOES_NOT_PROVE = [
    "that a source exists or was fetched",
    "that fetched content is the target document",
    "that staging evidence is admissible canonical evidence",
    "that terms, license, privacy, IRB, or release review is satisfied",
    "that a gate, claim, or paper-ready decision is approved",
]


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / POLICY_PATH
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _flatten_output_intents(output_intents: Any) -> list[str]:
    if isinstance(output_intents, dict):
        return [str(value).strip() for value in output_intents.values() if str(value).strip()]
    if isinstance(output_intents, list):
        return [str(value).strip() for value in output_intents if str(value).strip()]
    return []


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def classify_source_capture_permission(
    root: Path,
    *,
    lane: str = "",
    task_mode: str = "",
    intent: str = "",
    output_intents: Any = None,
    allowed_to_touch: list[str] | None = None,
) -> dict[str, Any]:
    """Classify capture permission as green/yellow/red.

    Green means no human approval is needed for public staging capture. Yellow
    means one route/session approval should cover a bounded batch. Red means a
    human approval is required before the action.
    """

    _load_policy(root)  # Keep policy presence visible to packaging/sync checks.
    outputs = _flatten_output_intents(output_intents)
    paths = [str(path) for path in (allowed_to_touch or [])]
    text = " ".join([lane, task_mode, intent, " ".join(outputs), " ".join(paths)]).lower()
    reasons: list[str] = []

    if any(intent in RED_INTENTS for intent in outputs) or _has_any(text, RED_TEXT_MARKERS) or _has_any(text, RED_PATH_MARKERS):
        tier = "red_human_required"
        approval_required = "human_required"
        reasons.append("credentials/cost/privacy/protected/canonical-or-release risk detected")
    elif any(intent in YELLOW_INTENTS for intent in outputs) or _has_any(text, YELLOW_TEXT_MARKERS):
        tier = "yellow_route_level"
        approval_required = "route_level"
        reasons.append("batch/browser/portal/canonical-candidate capture needs bounded route approval")
    elif (
        task_mode == "source_capture"
        and outputs
        and set(outputs).issubset(GREEN_INTENTS)
        and not _has_any(text, RED_PATH_MARKERS)
        and (any(marker in text for marker in STAGING_PATH_MARKERS) or _has_any(text, GREEN_TEXT_MARKERS))
    ):
        tier = "green_public_staging"
        approval_required = "none_for_staging_public_capture"
        reasons.append("public/local staging capture with probe/staging/audit outputs only")
    else:
        tier = "yellow_route_level"
        approval_required = "route_level"
        reasons.append("risk cannot be proven green; require bounded route/session approval")

    return {
        "status": "ADVISORY",
        "tier": tier,
        "approval_required": approval_required,
        "allowed_without_human_approval": approval_required == "none_for_staging_public_capture",
        "rationale": reasons,
        "required_controls": [
            "write only declared staging/probe/audit outputs",
            "validate fetched content identity before extraction or synthesis",
            "do not write data/raw, canonical data, claims, paper, release, or approval artifacts",
            "record staging receipt/delta; promotion to canonical remains separate",
        ],
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_source_capture_permission(report: dict[str, Any]) -> str:
    lines = [
        "# AEROS Source Capture Permission",
        "",
        f"tier: {report.get('tier')}",
        f"approval_required: {report.get('approval_required')}",
        f"allowed_without_human_approval: {report.get('allowed_without_human_approval')}",
        "rationale:",
    ]
    lines.extend(f"- {item}" for item in report.get("rationale") or [])
    lines.append("required_controls:")
    lines.extend(f"- {item}" for item in report.get("required_controls") or [])
    lines.append("does_not_prove:")
    lines.extend(f"- {item}" for item in report.get("does_not_prove") or [])
    return "\n".join(lines) + "\n"
