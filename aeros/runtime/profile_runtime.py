"""Runtime enforcement for explore/research/submit/regulated profiles."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml

from .adaptive_checks import select_checks


VALID_PROFILES = {"explore", "research", "submit", "regulated"}
SUBMIT_REQUIRED_CHECKS = (
    "check_manuscript_citation_faithfulness.py",
    "check_manuscript_citation_interpretation.py",
    "check_citation_risk_radar.py",
    "check_number_registry.py",
    "check_claim_numbers_bound.py",
    "check_table_cell_sources.py",
    "check_result_registry.py",
    "check_output_reproducibility.py",
    "check_provenance.py",
    "check_paper_package.py",
)


@dataclass(frozen=True)
class RuntimeCheckPlan:
    profile: str
    strategy: str
    checks: tuple[str, ...]
    observed_paths: tuple[str, ...]


def _policy(root: Path) -> dict[str, Any]:
    path = root / "harness/research_profiles.yml"
    if not path.exists():
        return {"default_profile": "research", "profiles": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"default_profile": "research", "profiles": {}}


def resolve_research_profile(root: Path) -> str:
    override = os.environ.get("AEROS_RESEARCH_PROFILE", "").strip().lower()
    if override in VALID_PROFILES:
        return override
    manifest = root / "project_manifest.yml"
    if manifest.exists():
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        automation = data.get("automation") if isinstance(data, dict) else {}
        configured = str((automation or {}).get("research_profile") or "").strip().lower() if isinstance(automation, dict) else ""
        if configured in VALID_PROFILES:
            return configured
    configured = str(_policy(root).get("default_profile") or "research").strip().lower()
    return configured if configured in VALID_PROFILES else "research"


def runtime_check_plan(
    root: Path,
    *,
    contract_checks: list[str] | tuple[str, ...],
    observed_paths: list[str] | tuple[str, ...],
    profile: str | None = None,
) -> RuntimeCheckPlan:
    active = profile or resolve_research_profile(root)
    paths = tuple(dict.fromkeys(str(path).strip() for path in observed_paths if str(path).strip()))
    if active == "regulated":
        return RuntimeCheckPlan(active, "contract_full", tuple(dict.fromkeys(contract_checks)), paths)
    adaptive_policy = root / "harness/adaptive_checks.yml"
    if not adaptive_policy.exists():
        # Older vendored projects and deliberately minimal execution fixtures may
        # not yet carry the adaptive-check catalog.  Falling back to the explicit
        # task contract is fail-safe: declared checks still run, while no broad
        # profile behavior is invented from missing policy.
        return RuntimeCheckPlan(
            active,
            "contract_fallback_missing_adaptive_policy",
            tuple(dict.fromkeys(contract_checks)),
            paths,
        )
    adaptive = tuple(select_checks(root, list(paths)).get("checks") or [])
    if active == "submit":
        checks = tuple(dict.fromkeys([*adaptive, *SUBMIT_REQUIRED_CHECKS]))
        return RuntimeCheckPlan(active, "artifact_selected_plus_submit", checks, paths)
    return RuntimeCheckPlan(active, "artifact_selected", adaptive, paths)
