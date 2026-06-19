#!/usr/bin/env python3
"""Validate registered external economics tools and literature adapters."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("FAIL: PyYAML is required for check_external_tool_registry.py") from exc


ROOT = Path.cwd()
REGISTRY = ROOT / "harness/external_tool_registry.yml"
ECON_LIT_POLICY = ROOT / "harness/econ_literature_discovery_policy.yml"
LITERATURE_RULES = ROOT / "discovery/literature/literature_rules.md"

ALLOWED_LANES = {"data", "literature", "analysis", "claim", "writing", "compliance", "harness"}
ALLOWED_ROLES = {
    "reference_index",
    "adapter_candidate",
    "external_standard",
    "advisory_reviewer",
    "reference_pattern",
}
REQUIRED_TOOLS = {
    "awesome_ai_for_economists",
    "openalex",
    "citec_repec",
    "pybiblionet",
    "preprintresolver",
    "aea_data_editor",
    "opensourceeconomics",
    "econstellar",
    "econometrics_agent",
    "causal_copilot",
    "causalagent",
}
REQUIRED_LIT_ADAPTERS = {"openalex", "citec_repec", "pybiblionet", "preprintresolver"}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def _validate_tool_registry() -> list[str]:
    failures: list[str] = []
    data = _load_yaml(REGISTRY)
    for key in ("version", "policy", "principle", "tools"):
        if key not in data:
            failures.append(f"{REGISTRY}: missing top-level field {key}")
    tools = data.get("tools") or {}
    if not isinstance(tools, dict):
        return failures + [f"{REGISTRY}: tools must be a mapping"]

    missing = sorted(REQUIRED_TOOLS - set(tools))
    if missing:
        failures.append(f"{REGISTRY}: missing required tools: {', '.join(missing)}")

    for tool_id, spec in sorted(tools.items()):
        if not isinstance(spec, dict):
            failures.append(f"{REGISTRY}: {tool_id} must be a mapping")
            continue
        lane = str(spec.get("lane", "")).strip()
        if lane not in ALLOWED_LANES:
            failures.append(f"{REGISTRY}: {tool_id} has invalid lane {lane!r}")
        role = str(spec.get("role", "")).strip()
        if role not in ALLOWED_ROLES:
            failures.append(f"{REGISTRY}: {tool_id} has invalid role {role!r}")
        for field in ("maturity", "url", "use_for", "evidence_output", "must_not_do"):
            if not spec.get(field):
                failures.append(f"{REGISTRY}: {tool_id} missing {field}")
        if role in {"advisory_reviewer", "adapter_candidate", "reference_pattern"}:
            boundary = " ".join(_as_list(spec.get("must_not_do"))).lower()
            if "approve" not in boundary and "gate" not in boundary:
                failures.append(f"{REGISTRY}: {tool_id} must explicitly forbid gate approval")
            if role == "advisory_reviewer" and "claim" not in boundary and "identification" not in boundary:
                failures.append(f"{REGISTRY}: {tool_id} advisory reviewer must not certify claims/identification")
    return failures


def _validate_literature_policy() -> list[str]:
    failures: list[str] = []
    data = _load_yaml(ECON_LIT_POLICY)
    adapters = data.get("adapters") or {}
    if not isinstance(adapters, dict):
        return failures + [f"{ECON_LIT_POLICY}: adapters must be a mapping"]
    missing = sorted(REQUIRED_LIT_ADAPTERS - set(adapters))
    if missing:
        failures.append(f"{ECON_LIT_POLICY}: missing required adapters: {', '.join(missing)}")
    for adapter_id, spec in sorted(adapters.items()):
        if not isinstance(spec, dict):
            failures.append(f"{ECON_LIT_POLICY}: {adapter_id} must be a mapping")
            continue
        if not spec.get("role"):
            failures.append(f"{ECON_LIT_POLICY}: {adapter_id} missing role")
        if not spec.get("default_output"):
            failures.append(f"{ECON_LIT_POLICY}: {adapter_id} missing default_output")
        cannot_support = " ".join(_as_list(spec.get("cannot_support"))).lower()
        if "gap" not in cannot_support and "synthesis" not in cannot_support and "findings" not in cannot_support:
            failures.append(f"{ECON_LIT_POLICY}: {adapter_id} must forbid substantive evidence use")
    if LITERATURE_RULES.exists():
        text = LITERATURE_RULES.read_text(encoding="utf-8")
        for marker in ("OpenAlex", "CitEc", "PreprintResolver"):
            if marker not in text:
                failures.append(f"{LITERATURE_RULES}: missing external adapter boundary for {marker}")
    return failures


def main() -> int:
    failures: list[str] = []
    try:
        failures.extend(_validate_tool_registry())
        failures.extend(_validate_literature_policy())
    except ValueError as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: external economics tool registry and discovery policy are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
