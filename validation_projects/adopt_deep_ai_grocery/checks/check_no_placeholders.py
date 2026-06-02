#!/usr/bin/env python3
"""Fail when filled/active/locked artifacts keep placeholder content."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


STATEFUL_STATUSES = {"active", "filled", "locked"}
PLACEHOLDER_VALUES = {"", "tbd", "todo", "to be filled", "to be determined", "na", "n/a", "none"}
PROJECT_MANIFEST = Path("project_manifest.yml")

PLACEHOLDER_PATTERNS = [re.compile(rf"\b{token}\b", re.IGNORECASE) for token in ("tbd", "todo", "na", "n/a")]


def _load_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    marker = "\n---\n"
    end = text.find(marker, 4)
    if end < 0:
        return {}, text

    fm_raw = text[4:end]
    body = text[end + len(marker) :]
    try:
        data = yaml.safe_load(fm_raw) if fm_raw.strip() else {}
    except yaml.YAMLError:
        data = {}
    return (data if isinstance(data, dict) else {}), body


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _is_placeholder(value: Any) -> bool:
    text = _normalize(value).lower()
    if not text:
        return True
    normalized = re.sub(r"[\"'`]+", "", text).strip().strip("[]{}()")
    if normalized in PLACEHOLDER_VALUES:
        return True
    return any(pattern.search(text) for pattern in PLACEHOLDER_PATTERNS)


def _scan_front_matter(path: Path, fm: dict[str, Any], failures: list[str]) -> None:
    status = str(fm.get("status", "")).strip().lower()
    if status not in STATEFUL_STATUSES:
        return
    for key, value in fm.items():
        if key in {"status", "required_sections", "schema_version", "default", "type", "notes"}:
            continue
        if isinstance(value, dict):
            for sub_k, sub_v in value.items():
                if _is_placeholder(sub_v):
                    failures.append(f"{path}: front matter {key}.{sub_k} is placeholder")
        elif isinstance(value, (list, tuple, set)):
            if not value:
                failures.append(f"{path}: front matter {key} is empty list")
            else:
                for idx, item in enumerate(value):
                    if _is_placeholder(item):
                        failures.append(f"{path}: front matter {key}[{idx}] is placeholder")
        else:
            if _is_placeholder(value):
                failures.append(f"{path}: front matter {key} is placeholder")


def _is_section_content_meaningful(lines: list[str]) -> bool:
    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("#"):
            continue
        if cleaned.startswith("|") and len(cleaned) > 2 and cleaned.count("|") >= 2:
            # Likely a placeholder table row.
            if _is_placeholder_row(cleaned):
                continue
        if not _is_placeholder(cleaned):
            return True
    return False


def _is_placeholder_row(line: str) -> bool:
    if not line.startswith("|"):
        return False
    cells = [cell.strip().lower() for cell in line.strip().strip("|").split("|")]
    if not cells:
        return True
    return all(_is_placeholder(cell) for cell in cells)


def _scan_markdown_body(path: Path, fm: dict[str, Any], body: str, failures: list[str]) -> None:
    status = str(fm.get("status", "")).strip().lower()
    if status not in STATEFUL_STATUSES:
        return

    required_sections = fm.get("required_sections", [])
    if not required_sections:
        return

    lines = body.splitlines()
    for section in required_sections:
        section_heading = str(section).strip()
        if section_heading not in body:
            failures.append(f"{path}: missing required section {section_heading}")
            continue
        start = next(i for i, line in enumerate(lines) if line.strip() == section_heading)
        section_lines: list[str] = []
        for line in lines[start + 1 :]:
            if line.startswith("## "):
                break
            section_lines.append(line)
        if not _is_section_content_meaningful(section_lines):
            failures.append(f"{path}: required section {section_heading} has no meaningful content")


def _scan_manifest_artifacts(path: Path, failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    fm, body = _load_front_matter(text)
    _scan_front_matter(path, fm, failures)
    _scan_markdown_body(path, fm, body, failures)


def _load_files_to_check() -> list[Path]:
    if not PROJECT_MANIFEST.exists():
        return []
    manifest = yaml.safe_load(PROJECT_MANIFEST.read_text(encoding="utf-8")) or {}
    checks = manifest.get("checks", {})
    if not isinstance(checks, dict):
        return []
    # placeholder-check specific files can be declared explicitly by users.
    files = checks.get("no_placeholders", checks.get("content_gate", checks.get("placeholders")))
    if files:
        if isinstance(files, list):
            return [Path(item) for item in files if item]
        if isinstance(files, str):
            return [Path(files)]
        return []

    # Fallback to key tracked artifact files for discovery/execution checks.
    fallback: list[str] = []
    for section in [
        manifest.get("research_judgment", {}),
        manifest.get("stage_agents", {}),
        manifest.get("mechanical_verification", {}),
        manifest.get("harness", {}),
    ]:
        if isinstance(section, dict):
            required_files = section.get("required_files", [])
            if isinstance(required_files, list):
                fallback.extend(required_files)
            required_dirs = section.get("required_dirs", [])
            if isinstance(required_dirs, list):
                for directory in required_dirs:
                    dpath = Path(directory)
                    if not dpath.exists():
                        continue
                    fallback.extend(str(item) for item in dpath.rglob("*.md"))

    fallback.extend(manifest.get("protected_files", []))
    fallback.extend([checks.get("run_command"), checks.get("stage_agents", "")])
    fallback.extend(["project_manifest.yml", "discovery/idea_memo.md", "docs/method_card.md", "evidence/claim_registry.md"])
    return [Path(item) for item in sorted(set(filter(None, fallback))) if Path(item).exists()]


def main() -> int:
    failures: list[str] = []
    paths = _load_files_to_check()
    for path in paths:
        if not path.exists():
            continue
        if path.suffix.lower() not in {".md", ".markdown", ".yml", ".yaml"}:
            continue
        _scan_manifest_artifacts(path, failures)

    if failures:
        print("FAIL: placeholder check failed:")
        print("\n".join(sorted(set(failures))))
        return 1

    print("PASS: no placeholder violations for stateful artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
