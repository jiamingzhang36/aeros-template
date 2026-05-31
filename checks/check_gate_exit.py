#!/usr/bin/env python3
"""Validate project gate progression against machine-readable exit criteria."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Any

import yaml


MANIFEST = Path("project_manifest.yml")
AEROS_STATE = Path("aeros_state.yml")

PLACEHOLDER_VALUES = {"", "tbd", "todo", "to be determined", "to be filled", "na", "n/a"}
REQUIRED_CLAIM_HEADERS = [
    "Claim ID",
    "Claim",
    "Type",
    "Status",
    "Evidence ID(s)",
    "Result ID(s)",
    "Boundary / Limitation",
    "Approved",
]

GATE_ID_PATTERN = re.compile(r"^G(\d+)")


def _parse_gate_id(value: str) -> int:
    m = GATE_ID_PATTERN.match(value or "")
    if not m:
        raise ValueError(f"invalid gate id '{value}'")
    return int(m.group(1))


def _load_manifest() -> dict:
    if not MANIFEST.exists():
        raise RuntimeError(f"missing manifest: {MANIFEST}")
    with MANIFEST.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"invalid manifest format: {MANIFEST}")
    return data


def _load_runtime_gate() -> str:
    if not AEROS_STATE.exists():
        return ""
    data = yaml.safe_load(AEROS_STATE.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return ""
    return str(data.get("current_gate", "")).strip()


def _extract_gate_id_series(manifest: dict) -> list[str]:
    gates = manifest.get("gate_lifecycle", {}).get("gates", [])
    if not gates:
        raise RuntimeError("manifest missing gate_lifecycle.gates")
    return [str(item).strip() for item in gates]


def _load_current_gate(manifest: dict) -> str:
    return str(manifest.get("gate_lifecycle", {}).get("current_gate", "")).strip()


def _load_criteria(manifest: dict) -> dict[str, list[dict]]:
    criteria = manifest.get("gate_exit_criteria", {})
    if not isinstance(criteria, dict):
        raise RuntimeError("manifest gate_exit_criteria must be a mapping")
    normalized: dict[str, list[dict]] = {}
    for gate_id, block in criteria.items():
        if isinstance(block, dict):
            normalized[gate_id] = block.get("requires", [])
        elif isinstance(block, list):
            normalized[gate_id] = block
        else:
            raise RuntimeError(f"invalid gate_exit_criteria for {gate_id}: expected list or dict")
    return normalized


def _validate_mainline_alignment(manifest: dict) -> list[str]:
    failures: list[str] = []
    project = manifest.get("project", {})
    project_status = str(project.get("status", "")).strip().lower()
    if project_status not in {"", "draft"}:
        mainline = manifest.get("mainline_alignment", {})
        if not isinstance(mainline, dict):
            failures.append("mainline_alignment is missing or invalid")
            return failures
        for key in ("north_star", "active_mechanism"):
            value = str(mainline.get(key, "")).strip()
            if not value:
                failures.append(
                    f"mainline_alignment.{key} is required when project.status is '{project_status}'"
                )
    return failures


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).strip().lower()


def _is_placeholder(value: Any) -> bool:
    return _norm_lower(value) in PLACEHOLDER_VALUES


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def _load_file_status(path: Path) -> str:
    if path.suffix.lower() in {".yml", ".yaml"}:
        if not path.exists():
            return ""
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            status = payload.get("status")
            if status is not None:
                return _norm(status)
            if len(payload) == 1:
                return ""
        return ""

    if not path.exists() or path.suffix.lower() != ".md":
        return ""

    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if match:
        try:
            front = yaml.safe_load(match.group(1)) or {}
            if isinstance(front, dict):
                front_status = front.get("status")
                if front_status is not None:
                    return _norm(front_status)
        except yaml.YAMLError:
            pass
    match = re.search(r"^status:\s*(.+)$", text, flags=re.M | re.I)
    if match:
        return _norm(match.group(1).split("#", 1)[0])
    return ""


def _required_file_statuses(manifest: dict) -> list[str]:
    project_status = str(manifest.get("project", {}).get("status", "")).strip().lower()
    if project_status == "draft" or project_status == "":
        return []

    failures: list[str] = []
    files = manifest.get("layers", {}).get("research_judgment", {}).get("required_files", [])
    for rel_path in files:
        path = Path(rel_path)
        if not path.exists():
            continue
        if path.suffix.lower() not in {".md", ".yml", ".yaml"}:
            continue

        status = _load_file_status(path)
        if not status:
            failures.append(f"research_judgment.required_files status missing: {rel_path}")
            continue
        if _is_placeholder(status):
            failures.append(f"research_judgment.required_files status placeholder: {rel_path}")

    return failures


def _parse_markdown_table(path: Path, required_headers: list[str]) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    normalized_required = [header.lower() for header in required_headers]
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        headers = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if [cell.lower() for cell in headers] != normalized_required:
            continue
        sep = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not re.match(r"^\s*\|?\s*:?-{3,}\s*:?(?:\|\s*:?-{3,}\s*:?\|?)*\s*$", sep):
            continue
        rows: list[dict[str, str]] = []
        for raw in lines[i + 2 :]:
            stripped = raw.strip()
            if not stripped.startswith("|"):
                break
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) < len(headers):
                continue
            rows.append(dict(zip(headers, cells)))
        if rows:
            return rows
    return []


def _main_claim_row(claim_rows: list[dict[str, str]]) -> dict[str, str]:
    if not claim_rows:
        return {}
    return claim_rows[0]


def _extract_result_ids(value: str) -> list[str]:
    return re.findall(r"R\d{3}", value or "")


def _load_claim_rows() -> list[dict[str, str]]:
    path = Path("evidence/claim_registry.md")
    if not path.exists():
        return []
    return _parse_markdown_table(path, REQUIRED_CLAIM_HEADERS)


def _main_claim_result_ids(claim_rows: list[dict[str, str]]) -> list[str]:
    claim = _main_claim_row(claim_rows)
    if not claim:
        return []
    return _extract_result_ids(claim.get("Result ID(s)", ""))


def _load_result_index_ids(path: Path | str = "evidence/result_index.csv") -> set[str]:
    index_path = Path(path)
    if not index_path.exists():
        return set()
    return {
        _norm(row.get("result_id", ""))
        for row in _read_csv_rows(index_path)
        if _norm(row.get("result_id", ""))
    }


def _load_provenance_ids() -> set[str]:
    provenance_dir = Path("outputs/.provenance")
    if not provenance_dir.exists():
        return set()
    return {
        file.stem
        for file in provenance_dir.glob("*.json")
        if re.fullmatch(r"R\d{3}", file.stem)
    }


def _check_markdown_table_rows(path: Path, requirement: dict) -> tuple[bool, str]:
    section = str(requirement.get("section", "")).strip() or str(requirement.get("header", "Variables")).strip()
    min_rows = int(requirement.get("min_rows", 1))

    if not path.exists():
        return False, f"required file not found: {path}"

    lines = path.read_text(encoding="utf-8").splitlines()
    section_line = f"## {section}"
    header_index = None
    for i, line in enumerate(lines):
        if line.strip() == section_line and i + 2 < len(lines):
            header_index = i
            break
    if header_index is None:
        return False, f"{path}: missing section {section_line}"

    section_lines = lines[header_index + 1 :]
    table_start = None
    for offset, line in enumerate(section_lines):
        if line.strip().startswith("|"):
            table_start = offset
            break
    if table_start is None:
        return False, f"{path}: section {section_line} has no markdown table"

    rows = 0
    for raw in section_lines[table_start + 2 :]:
        stripped = raw.strip()
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 1:
            continue
        if all(_is_placeholder(cell) for cell in cells):
            continue
        rows += 1

    if rows >= min_rows:
        return True, f"ok:{path}"

    return False, f"{path} has {rows} non-placeholder row(s); requires >= {min_rows} rows in section {section}"


def _row_passes_filters(row: dict[str, str], filters: dict[str, str]) -> bool:
    for key, expected in filters.items():
        if row.get(key, "").strip() != str(expected).strip():
            return False
    return True


def _count_matching_rows(requirement: dict) -> int:
    path = Path(requirement["path"])
    if not path.exists():
        raise RuntimeError(f"required csv missing: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        filters = requirement.get("filters", {})
        if not isinstance(filters, dict):
            raise RuntimeError(f"invalid filters for {path}: expected dict")
        count = 0
        for row in reader:
            if _row_passes_filters(row, filters):
                count += 1
    return count


def _check_requirement(req: dict) -> tuple[bool, str]:
    req_type = str(req.get("type", "csv_filter_count"))
    path = req.get("path")
    if not path:
        raise RuntimeError("exit criterion missing path")
    file_path = Path(path)

    if req_type in {"file_exists", "exists"}:
        if file_path.exists():
            return True, f"ok:{path}"
        return False, f"required file not found: {path}"

    if req_type == "csv_filter_count":
        min_count = int(req.get("min_count", 1))
        count = _count_matching_rows(req)
        required_filters = req.get("filters", {})
        if count >= min_count:
            return True, f"ok:{path}"
        return (
            False,
            f"{path} has {count} matching row(s); requires >= {min_count} for filters {required_filters}",
        )

    if req_type == "status_not_empty":
        status = _load_file_status(file_path)
        if status and not _is_placeholder(status):
            return True, f"ok:{path}"
        if not status:
            return False, f"{path} does not declare a non-empty status"
        return False, f"{path} status appears placeholder-like: {status}"

    if req_type == "yaml_field_nonempty":
        if not file_path.exists():
            return False, f"required file not found: {path}"
        field = str(req.get("field", "")).strip()
        if not field:
            raise RuntimeError(f"yaml_field_nonempty missing field for {path}")
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return False, f"{path} is not valid yaml dict"
        cursor: Any = payload
        for key in field.split("."):
            if not isinstance(cursor, dict) or key not in cursor:
                return False, f"{path}: missing required yaml field '{field}'"
            cursor = cursor.get(key)
        if isinstance(cursor, (list, tuple, dict)):
            if cursor:
                return True, f"ok:{path}:{field}"
            return False, f"{path}: yaml field '{field}' is empty"
        if _is_placeholder(cursor):
            return False, f"{path}: yaml field '{field}' is placeholder-like"
        return True, f"ok:{path}:{field}"

    if req_type == "markdown_status_equals":
        status = _load_file_status(file_path)
        if not status:
            return False, f"{path}: status missing or cannot be parsed"
        required_status = _norm(req.get("value", ""))
        if status.lower() == required_status.lower():
            return True, f"ok:{path}:{required_status}"
        return False, f"{path}: requires status '{required_status}', found '{status}'"

    if req_type == "claim_main_has_type":
        if not file_path.exists():
            return False, f"required claim registry not found: {path}"
        claims = _load_claim_rows()
        claim = _main_claim_row(claims)
        if not claim:
            return False, "claim_registry has no claim rows"
        claim_type = claim.get("Type", "")
        if claim_type and not _is_placeholder(claim_type):
            return True, f"ok:{path}"
        return False, "main claim Type is missing or placeholder-like"

    if req_type == "claim_main_results_registered":
        if not file_path.exists():
            return False, f"required claim registry not found: {path}"
        claims = _load_claim_rows()
        result_ids = _main_claim_result_ids(claims)
        if not result_ids:
            return False, "main claim has no result_id references"
        result_index = _load_result_index_ids()
        if not result_index:
            return False, "result_index.csv missing or has no result_id entries"
        missing = sorted(set(result_ids) - result_index)
        if missing:
            return False, f"main claim result_id(s) missing from result_index.csv: {', '.join(missing)}"
        return True, "ok: main claim result_ids are registered in result_index.csv"

    if req_type == "claim_no_draft":
        if not file_path.exists():
            return False, f"required claim registry not found: {path}"
        claims = _load_claim_rows()
        draft_claims = [c.get("Claim ID", "") for c in claims if _norm_lower(c.get("Status")) == "draft"]
        if draft_claims:
            return False, f"claim_registry has draft claims: {', '.join(draft_claims)}"
        return True, "ok:claim_registry"

    if req_type == "claim_main_results_have_provenance":
        claims = _load_claim_rows()
        claim = _main_claim_row(claims)
        if not claim:
            return False, "claim_registry has no claim rows"
        result_ids = _extract_result_ids(claim.get("Result ID(s)", ""))
        if not result_ids:
            return False, "main claim has no result_id references; please provide at least one result_id before proceeding"

        provenance = _load_provenance_ids()
        missing = sorted(set(result_ids) - provenance)
        if missing:
            return False, f"main claim result_id(s) missing provenance: {', '.join(missing)}"
        return True, "ok:main claim result_ids all have provenance"

    if req_type == "result_index_all_have_provenance":
        if not Path("evidence/result_index.csv").exists():
            return True, "ok: no result index yet"
        rows = _read_csv_rows(Path("evidence/result_index.csv"))
        result_ids = [str(r.get("result_id", "")).strip() for r in rows if str(r.get("result_id", "")).strip()]
        if not result_ids:
            return True, "ok: result index empty"
        provenance = _load_provenance_ids()
        missing = sorted(set(result_ids) - provenance)
        if missing:
            return False, f"result_index result_ids missing provenance: {', '.join(missing)}"
        return True, "ok: result_index all result_ids have provenance"

    if req_type == "file_not_placeholder":
        if not file_path.exists():
            return False, f"required file not found: {path}"
        marker = str(req.get("marker", "placeholder"))
        if marker in file_path.read_text(encoding="utf-8"):
            return False, f"{path}: still contains marker '{marker}'"
        return True, f"ok:{path}"

    if req_type == "csv_nonempty_rows":
        if not file_path.exists():
            return False, f"required file not found: {path}"
        if file_path.suffix.lower() != ".csv":
            return False, f"{path}: csv_nonempty_rows requires a csv file"
        min_rows = int(req.get("min_rows", 1))
        rows = _read_csv_rows(file_path)
        if len(rows) >= min_rows:
            return True, f"ok:{path}"
        return False, f"{path} has {len(rows)} data row(s); requires >= {min_rows}"

    if req_type == "markdown_nonplaceholder_lines":
        if not file_path.exists():
            return False, f"required file not found: {path}"
        min_lines = int(req.get("min_lines", 1))
        lines = [
            line.strip()
            for line in file_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        meaningful = [
            line
            for line in lines
            if not _is_placeholder(line)
        ]
        if len(meaningful) >= min_lines:
            return True, f"ok:{path}"
        return False, f"{path} has insufficient non-placeholder content; requires >= {min_lines} non-heading lines"

    if req_type == "markdown_table_min_rows":
        return _check_markdown_table_rows(file_path, req)

    raise RuntimeError(f"unknown criterion type: {req_type}")


def evaluate_through_gate(gate_label: str, project_root: str | Path = ".") -> tuple[bool, list[str]]:
    """Evaluate manifest gate-exit criteria for every gate up to and including
    gate_label. Returns (ok, failures). Reusable by both the check and the
    human-gate approval flow so they share one criteria source of truth.
    """
    import os
    prev = os.getcwd()
    os.chdir(str(project_root))
    try:
        manifest = _load_manifest()
        gate_ids = [item.split()[0] for item in _extract_gate_id_series(manifest)]
        target_id = _parse_gate_id(gate_label.split()[0])
        failures: list[str] = []
        failures.extend(_validate_mainline_alignment(manifest))
        failures.extend(_required_file_statuses(manifest))
        criteria = _load_criteria(manifest)
        for gate in gate_ids[: target_id + 1]:
            for req in criteria.get(gate, []):
                try:
                    ok, message = _check_requirement(req)
                except RuntimeError as exc:
                    failures.append(f"{gate}: {exc}")
                    continue
                if not ok:
                    failures.append(f"{gate}: {message}")
        return (not failures, failures)
    finally:
        os.chdir(prev)


def main() -> int:
    try:
        manifest = _load_manifest()
        # Source of truth for the current gate is the runtime state (aeros_state.yml);
        # the manifest value is only a fallback for a fresh project.
        runtime_gate = _load_runtime_gate()
        manifest_gate = _load_current_gate(manifest)
        authoritative = runtime_gate or manifest_gate
        _parse_gate_id(authoritative.split()[0])
    except (RuntimeError, ValueError, IndexError) as exc:
        print(f"FAIL: gate configuration invalid ({exc})")
        return 1

    ok, failures = evaluate_through_gate(authoritative)
    if not ok:
        print("FAIL: gate exit criteria not satisfied:")
        print("\n".join(failures))
        return 1

    src = "runtime state" if runtime_gate else "manifest"
    print(f"PASS: gate_exit check passed at {authoritative} (source: {src})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
