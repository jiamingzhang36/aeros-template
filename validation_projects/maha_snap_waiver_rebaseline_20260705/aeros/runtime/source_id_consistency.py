"""Source-id consistency checks across AEROS data surfaces.

This module is intentionally mechanical.  It checks whether source/data IDs
used by contracts, inventories, provenance, and result registries resolve to
the same known source universe.  It does not decide whether a source is
scientifically sufficient or whether a result should support a claim.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - yaml is present in normal AEROS envs
    yaml = None


SOURCE_ID_KEYS = {
    "source_id",
    "source_ids",
    "data_id",
    "data_ids",
    "input_source_id",
    "input_source_ids",
    "input_sources",
    "source_path_or_url_id",
}

DOES_NOT_PROVE = [
    "source content quality",
    "source coverage sufficiency",
    "data licensing or terms compliance",
    "claim support",
]


@dataclass(frozen=True)
class SourceIdUse:
    source_id: str
    surface: str
    path: str
    detail: str


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _split_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_split_ids(item))
        return out
    if isinstance(value, dict):
        out = []
        for key in SOURCE_ID_KEYS:
            if key in value:
                out.extend(_split_ids(value.get(key)))
        return out
    text = str(value).strip()
    if not text or text in {"[]", "{}", "NA", "N/A", "none", "None"}:
        return []
    for sep in [";", "|", ","]:
        if sep in text:
            return [part.strip() for part in text.split(sep) if part.strip()]
    return [text]


def _walk_ids(obj: Any) -> Iterable[str]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in SOURCE_ID_KEYS:
                yield from _split_ids(value)
            yield from _walk_ids(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_ids(item)


def _load_yaml(path: Path) -> Any:
    if not path.exists() or yaml is None:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None


def _scan_yaml_source_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    ids: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        for key in SOURCE_ID_KEYS:
            prefix = f"{key}:"
            if stripped.startswith(prefix):
                ids.extend(_split_ids(stripped.split(":", 1)[1].strip().strip("\"'")))
    return sorted(set(ids))


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


def inventory_source_ids(root: Path) -> list[SourceIdUse]:
    path = root / "discovery" / "data_inventory.csv"
    uses: list[SourceIdUse] = []
    for idx, row in enumerate(_load_csv_rows(path), start=2):
        for key in ("source_id", "data_id", "id"):
            value = _norm(row.get(key))
            if value:
                uses.append(SourceIdUse(value, "data_inventory", str(path), f"row {idx} {key}"))
                break
    return uses


def contract_source_ids(root: Path) -> list[SourceIdUse]:
    path = root / "docs" / "data_contract.yml"
    data = _load_yaml(path)
    ids = sorted(set(_walk_ids(data))) if data else _scan_yaml_source_ids(path)
    return [SourceIdUse(source_id, "data_contract", str(path), "source reference") for source_id in ids]


def provenance_source_ids(root: Path) -> list[SourceIdUse]:
    uses: list[SourceIdUse] = []
    prov_dir = root / "outputs" / ".provenance"
    if not prov_dir.exists():
        return uses
    for path in sorted(prov_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for source_id in sorted(set(_walk_ids(data))):
            uses.append(SourceIdUse(source_id, "provenance", str(path), "source reference"))
    return uses


def result_registry_source_ids(root: Path) -> list[SourceIdUse]:
    path = root / "evidence" / "result_registry.csv"
    uses: list[SourceIdUse] = []
    for idx, row in enumerate(_load_csv_rows(path), start=2):
        for key, value in row.items():
            text = _norm(value)
            if not text:
                continue
            parsed: Any
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = None
            ids = set(_walk_ids(parsed)) if parsed is not None else set()
            if key in SOURCE_ID_KEYS:
                ids.update(_split_ids(text))
            for source_id in sorted(ids):
                uses.append(SourceIdUse(source_id, "result_registry", str(path), f"row {idx} {key}"))
    return uses


def collect_source_id_uses(root: Path) -> dict[str, list[SourceIdUse]]:
    root = Path(root)
    uses = {
        "inventory": inventory_source_ids(root),
        "contract": contract_source_ids(root),
        "provenance": provenance_source_ids(root),
        "result_registry": result_registry_source_ids(root),
    }
    return uses


def validate_source_id_consistency(root: Path) -> dict[str, Any]:
    """Return a mechanical consistency report.

    Contract ids must resolve to inventory ids when an inventory exists.
    Provenance/result-registry ids must resolve to either inventory or contract
    ids. Empty template surfaces pass cleanly.
    """

    uses = collect_source_id_uses(Path(root))
    inventory_ids = {u.source_id for u in uses["inventory"]}
    contract_ids = {u.source_id for u in uses["contract"]}
    known_ids = inventory_ids | contract_ids
    issues: list[str] = []

    if inventory_ids:
        for source_id in sorted(contract_ids - inventory_ids):
            issues.append(f"data_contract references unknown source_id {source_id!r} not found in discovery/data_inventory.csv")

    if known_ids:
        for surface in ("provenance", "result_registry"):
            for use in uses[surface]:
                if use.source_id not in known_ids:
                    issues.append(f"{surface} references unknown source_id {use.source_id!r} at {use.path} ({use.detail})")

    return {
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "counts": {key: len(value) for key, value in uses.items()},
        "known_source_ids": sorted(known_ids),
        "does_not_prove": DOES_NOT_PROVE,
    }


def format_source_id_report(report: dict[str, Any]) -> str:
    lines = [f"source-id consistency: {report.get('status', 'UNKNOWN')}"]
    for issue in report.get("issues", []):
        lines.append(f"- {issue}")
    lines.append("does_not_prove:")
    for item in report.get("does_not_prove", []):
        lines.append(f"- {item}")
    return "\n".join(lines)
