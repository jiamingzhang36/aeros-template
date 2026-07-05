#!/usr/bin/env python3
"""Check agent run report templates and executed run reports."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml


REQUIRED_AGENT_HEADINGS = [
    "## Run Metadata",
    "## Objective",
    "## Files Read",
    "## Files Modified",
    "## Commands Run",
    "## Outputs Changed",
    "## Skills Used",
    "## Checks Run",
    "## Protected Definitions",
    "## Claim Changes",
    "## Human Decisions Needed",
    "## Completion Status",
]

REQUIRED_CRITIC_HEADINGS = [
    "## Review Target",
    "## Review Questions",
    "## Findings",
    "## Verdict",
]

PLACEHOLDER_SKILLS = {"", "tbd", "todo", "to be determined", "to be filled", "na", "n/a", "none"}
PLACEHOLDER_COMMANDS = {"", "tbd", "todo", "to be determined", "to be filled", "na", "n/a", "none", "n/a (fill)"}


def missing_headings(path: Path, required: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [heading for heading in required if heading not in text]


def _load_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    # YAML task contracts (.yml/.yaml) are parsed whole; their top-level keys
    # (e.g. allowed_skills) play the role of front matter.
    if path.suffix.lower() in {".yml", ".yaml"}:
        try:
            parsed = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return {}
    try:
        parsed = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_task_id(text: str) -> str:
    # Accept both short ids (D001) and full contract ids (D001_literature_search).
    for line in text.splitlines():
        match = re.search(
            r"(?i)^\s*-?\s*task(?:\s*id)?\s*:\s*([A-Za-z]\d{3}(?:_[A-Za-z0-9_]+)?)",
            line,
        )
        if match:
            return match.group(1).strip()
    return ""


def _find_task_file(task_id: str) -> Path | None:
    # Resolve .md (legacy) and .yml/.yaml (runtime) task files, for both full
    # ids (exact stem match) and short ids (X###_* prefix match).
    patterns = [f"{task_id}.md", f"{task_id}.yml", f"{task_id}.yaml",
                f"{task_id}_*.md", f"{task_id}_*.yml", f"{task_id}_*.yaml"]
    for pattern in patterns:
        for path in sorted(Path("tasks").rglob(pattern)):
            return path
    return None


def _extract_section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == heading:
            section: list[str] = []
            for candidate in lines[i + 1 :]:
                if candidate.startswith("## "):
                    break
                section.append(candidate)
            return section
    return []


def _normalize_skill(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().strip("`'\"")).lower()


def _is_placeholder_skill(value: str) -> bool:
    return _normalize_skill(value) in PLACEHOLDER_SKILLS


def _extract_skills_from_text(content: str) -> set[str]:
    skills: set[str] = set()
    ticks = re.findall(r"`([^`]+)`", content)
    if ticks:
        for token in ticks:
            normalized = _normalize_skill(token)
            if not _is_placeholder_skill(normalized):
                skills.add(normalized)
        return skills

    line = content.strip()
    if not line or line.startswith("|"):
        return skills
    line = re.sub(r"^[-*+]\s*(\[[ xX]\]\s*)?", "", line).strip()
    if not line:
        return skills
    token = re.split(r"[,;:|\-]\s*", line, maxsplit=1)[0].strip()
    if token:
        normalized = _normalize_skill(token)
        if not _is_placeholder_skill(normalized):
            skills.add(normalized)
    return skills


def _extract_skills_used(text: str) -> list[str]:
    section_lines = _extract_section_lines(text, "## Skills Used")
    if not section_lines:
        return []

    extracted: set[str] = set()
    for line in section_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            if re.match(r"^\|?\s*:?-{3,}\s*:?\s*\|", stripped):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or cells[0].strip().lower() in {"", "skill", "skills"}:
                continue
            if cells and cells[0]:
                for token in _extract_skills_from_text(cells[0]):
                    extracted.add(token)
            continue
        if stripped.startswith("-") or stripped.startswith("*") or stripped.startswith("+"):
            for token in _extract_skills_from_text(stripped):
                extracted.add(token)
    return sorted(extracted)


def _extract_commands_used(text: str) -> list[str]:
    section_lines = _extract_section_lines(text, "## Commands Run")
    if not section_lines:
        return []

    extracted: set[str] = set()
    in_code = False
    for line in section_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            normalized = re.sub(r"\s+", " ", stripped.lower())
            if _normalize_skill(normalized) not in PLACEHOLDER_COMMANDS:
                extracted.add(stripped)
            continue
        if stripped.startswith("|"):
            if re.match(r"^\|?\s*:?-{3,}\s*:?\s*\|", stripped):
                continue
            cleaned = stripped.strip("|").strip()
            if cleaned:
                token = cleaned.split("|", 1)[0].strip()
                if token and not _is_placeholder_skill(token):
                    extracted.add(token)
            continue
        if stripped.startswith("-") or stripped.startswith("*") or stripped.startswith("+"):
            payload = stripped[1:].strip()
            if payload.startswith("[ ]") or payload.startswith("[x]") or payload.startswith("[X]"):
                payload = payload[3:].strip()
            if payload and not _is_placeholder_skill(payload):
                extracted.add(payload)
            continue
        if (not _is_placeholder_skill(stripped) and stripped.startswith("$")) or re.match(
            r"^[A-Za-z0-9_./-]+\s+.*", stripped
        ):
            extracted.add(stripped)

    return sorted(extracted)


def _validate_agent_run_reports() -> list[str]:
    failures: list[str] = []
    for path in sorted(Path("agent_runs").glob("*.md")):
        if path.name.startswith(("TEMPLATE_", "EXAMPLE_")):
            continue

        text = path.read_text(encoding="utf-8")
        # Scope: only validate actual AEROS task run reports. The runtime always
        # writes a Task ID into a report's metadata; a file without one is a
        # manual note or legacy artifact in agent_runs/, not a task report, and
        # is out of scope (validating it would be a false failure).
        task_id = _extract_task_id(text)
        if not task_id:
            continue

        # Only the runtime's own reports (task_id_YYYYMMDD_HHMMSS.md) are the
        # authoritative, report.py-formatted reports. An agent's free-form
        # self-report written into agent_runs/ is scratch, not the report —
        # validating it would false-fail; skip non-runtime-named files.
        import re as _re
        if not _re.search(r"_\d{8}_\d{6}\.md$", path.name):
            continue

        if "## Skills Used" not in text:
            failures.append(f"{path}: missing section ## Skills Used")
            continue

        task_file = _find_task_file(task_id)
        if not task_file:
            failures.append(f"{path}: cannot resolve task file for {task_id}")
            continue

        task_front = _load_front_matter(task_file)
        allowed_raw = task_front.get("allowed_skills", [])
        if not isinstance(allowed_raw, list):
            failures.append(f"{path}: task {task_id} allowed_skills must be a list in {task_file}")
            continue

        allowed = {_normalize_skill(str(item)) for item in allowed_raw if str(item).strip()}
        used = _extract_skills_used(text)
        unknown = [item for item in used if item and item not in allowed]
        if unknown:
            failures.append(
                f"{path}: uses skills {', '.join(unknown)} outside {task_id} allowed list"
            )

        commands = _extract_commands_used(text)
        if not commands:
            failures.append(f"{path}: Commands Run section has no recorded commands")

    return failures


def main() -> int:
    failures: list[str] = []
    checks = [
        (Path("agent_runs/TEMPLATE_agent_run_report.md"), REQUIRED_AGENT_HEADINGS),
        (Path("agent_runs/TEMPLATE_critic_report.md"), REQUIRED_CRITIC_HEADINGS),
    ]

    for path, required in checks:
        if not path.exists():
            failures.append(f"{path}: missing file")
            continue
        missing = missing_headings(path, required)
        if missing:
            failures.append(f"{path}: missing {', '.join(missing)}")

    failures.extend(_validate_agent_run_reports())

    if failures:
        print("FAIL: agent report checks detected problems:")
        print("\n".join(failures))
        return 1

    print("PASS: agent/critic templates and run reports include required sections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
