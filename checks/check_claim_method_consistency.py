#!/usr/bin/env python3
"""Ensure claim types align with method-card design signals.

This adds lightweight semantic checks beyond the type/name pairing:
- Method card declares a claim type and supported claim types.
- Sections such as identifying assumption are required to contain meaningful content
  for stronger claim classes (e.g., causal/mechanism).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


CLAIM_REGISTRY = Path("evidence/claim_registry.md")
METHOD_CARD = Path("docs/method_card.md")
REQUIRED_HEADERS = [
    "Claim ID",
    "Claim",
    "Type",
    "Status",
    "Evidence ID(s)",
    "Result ID(s)",
    "Boundary / Limitation",
    "Approved",
]

KNOWN_TYPES = {
    "descriptive",
    "associational",
    "causal",
    "mechanism",
    "policy-translation",
    "forecast",
}
CAUSAL_TYPES = {"causal", "mechanism"}
ACTIVE_STATUSES = {"supported", "ambiguous", "unsupported"}
PLACEHOLDER_VALUES = {"", "tbd", "todo", "to be determined", "to be filled", "na", "n/a", "none"}

SECTION_REQUIREMENTS = {
    "causal": [
        "Research Question",
        "Identifying Assumption",
        "Treatment / Exposure / Shock / Key Variable",
        "Empirical Strategy",
        "Control or Comparison Group",
        "Main Threats",
        "What This Design Cannot Show",
    ],
    "mechanism": [
        "Research Question",
        "Identifying Assumption",
        "Treatment / Exposure / Shock / Key Variable",
        "Empirical Strategy",
        "Control or Comparison Group",
        "Main Threats",
    ],
    "associational": [
        "Research Question",
        "Treatment / Exposure / Shock / Key Variable",
        "Control or Comparison Group",
        "Empirical Strategy",
    ],
    "descriptive": [
        "Research Question",
        "Outcomes",
        "Sample",
    ],
    "forecast": [
        "Research Question",
        "Empirical Strategy",
        "Robustness Checks",
        "Main Threats",
    ],
    "policy-translation": [
        "Research Question",
        "Main Threats",
        "What This Design Cannot Show",
        "Robustness Checks",
    ],
}


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _is_placeholder(value: Any) -> bool:
    return _norm(value).strip().lower() in PLACEHOLDER_VALUES


def _extract_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return {}
    try:
        payload = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_claim_rows() -> list[dict[str, str]]:
    if not CLAIM_REGISTRY.exists():
        return []

    lines = CLAIM_REGISTRY.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, str]] = []
    normalized_headers = [h.lower() for h in REQUIRED_HEADERS]

    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        headers = [cell.strip() for cell in line.strip("|").split("|")]
        if [cell.lower() for cell in headers] != normalized_headers:
            continue

        separator_index = i + 1
        if separator_index >= len(lines):
            continue
        if not re.match(r"^\s*\|?\s*:?-{3,}\s*:?(?:\|\s*:?-{3,}\s*:?\|?)*\s*$", lines[separator_index].strip()):
            continue

        for raw in lines[i + 2 :]:
            cleaned = raw.strip()
            if not cleaned.startswith("|"):
                break
            cells = [cell.strip() for cell in cleaned.strip("|").split("|")]
            if len(cells) < len(headers):
                continue
            if cells[0].strip().lower() == "claim id":
                continue
            rows.append(dict(zip(headers, cells)))
        if rows:
            break

    return rows


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    norm = _norm(value).lower()
    return norm in {"true", "1", "yes", "y", "on"}


def _normalize_claim_type(value: str) -> str:
    value = _norm(value).lower()
    for sep in ("/", ",", ";"):
        if sep in value:
            value = value.split(sep)[0]
    return value.strip()


def _collect_active_claim_types(rows: list[dict[str, str]]) -> list[str]:
    types: set[str] = set()
    for row in rows:
        status = _norm(row.get("Status")).lower()
        if status and status not in ACTIVE_STATUSES:
            continue
        ctype = _normalize_claim_type(row.get("Type", ""))
        if ctype and ctype in KNOWN_TYPES:
            types.add(ctype)
    return sorted(types)


def _coerce_supported_types(raw: Any) -> set[str]:
    supported: set[str] = set()
    if isinstance(raw, str):
        for item in re.split(r"[,;\n]", raw):
            normalized = _normalize_claim_type(item)
            if normalized:
                supported.add(normalized)
    elif isinstance(raw, (list, tuple, set)):
        for item in raw:
            if isinstance(item, str):
                normalized = _normalize_claim_type(item)
                if normalized:
                    supported.add(normalized)
    return supported


def _extract_section_text(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    target = heading.strip()
    for i, line in enumerate(lines):
        if line.strip() == target:
            start = i
            break
    if start is None:
        return ""

    section_lines: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        section_lines.append(line)

    return "\n".join(section_lines).strip()


def _section_has_meaningful_content(content: str) -> bool:
    for line in content.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("###"):
            continue
        if cleaned.startswith("|") and cleaned.count("|") >= 2:
            cells = [cell.strip().lower() for cell in cleaned.strip("|").split("|")]
            if cells and all(_is_placeholder(cell) for cell in cells):
                continue
        if cleaned.startswith("-"):
            cleaned = cleaned.lstrip("- ").strip()
        if cleaned.startswith("[") and "](" in cleaned:
            continue
        if not _is_placeholder(cleaned):
            return True
    return False



def main() -> int:
    claims = _parse_claim_rows()
    if not claims:
        print(f"PASS: claim-method consistency skipped; no parsed claims in {CLAIM_REGISTRY}")
        return 0

    if not METHOD_CARD.exists():
        print(f"FAIL: missing {METHOD_CARD}")
        return 1

    method_meta = _extract_front_matter(METHOD_CARD)
    method_text = METHOD_CARD.read_text(encoding="utf-8")

    method_claim_type = _normalize_claim_type(method_meta.get("claim_type", ""))
    method_supported = _coerce_supported_types(method_meta.get("supported_claim_types"))
    if not method_supported and method_claim_type:
        method_supported = {method_claim_type}

    identification_strategy = _norm(method_meta.get("identification_strategy"))
    design_supports_causal = method_meta.get("design_supports_causal")

    active_claim_types = _collect_active_claim_types(claims)
    if not active_claim_types:
        print("PASS: no active claims to validate against method card")
        return 0

    failures: list[str] = []

    if not method_claim_type:
        failures.append("method_card missing non-placeholder claim_type in front matter")
    elif method_claim_type not in KNOWN_TYPES:
        failures.append(f"method_card claim_type '{method_claim_type}' is not recognized")

    if not method_supported:
        failures.append("method_card missing supported_claim_types in front matter")

    for ctype in active_claim_types:
        if method_supported and ctype not in method_supported:
            failures.append(
                f"method_card supported_claim_types does not include active claim type '{ctype}'"
            )
        requirements = SECTION_REQUIREMENTS.get(ctype, [])
        for section in requirements:
            body = _extract_section_text(method_text, f"## {section}")
            if not body:
                failures.append(f"method_card missing required section '## {section}' for claim type '{ctype}'")
                continue
            if not _section_has_meaningful_content(body):
                failures.append(
                    f"method_card section '## {section}' is placeholder-like for claim type '{ctype}'"
                )

    if set(active_claim_types) & CAUSAL_TYPES:
        if _is_placeholder(identification_strategy):
            failures.append("method_card missing non-placeholder identification_strategy in front matter")
        if _norm(design_supports_causal) == "":
            failures.append("method_card front matter design_supports_causal is missing")
        elif not _coerce_bool(design_supports_causal):
            failures.append(
                "method_card front matter design_supports_causal must be true for causal/mechanism claims"
            )

    if failures:
        print("FAIL: claim-method consistency failed:")
        print("\n".join(failures))
        return 1

    print(
        "PASS: claim-method consistency holds for active claim types "
        + ", ".join(active_claim_types)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
