#!/usr/bin/env python3
"""Check that the AEROS skill layer scaffold is present and tiered."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


REQUIRED_FILES = {
    Path("harness/skill_registry.md"): [
        "## Skill Layer Principle",
        "## Borrowed Organization",
        "## Practical Skill Menu",
        "## Skill Tiers",
        "## Skill Use Status",
    ],
    Path("harness/skill_invocation_rules.md"): [
        "## Invocation Order",
        "## Skill Selection Rule",
        "## Literature Skills",
        "## Skill Conflict Rule",
    ],
    Path("harness/practical_skill_menu.md"): [
        "## Core Skills",
        "## Optional Skills",
        "## Reference Skills",
    ],
    Path("harness/skill_map_core.yml"): [
        "sources:",
        "skill_stage_taxonomy:",
        "skills:",
        "research_ideation:",
        "lit_review_assistant:",
        "academic_research_suite_deep_research:",
        "data_inventory:",
        "causal_id_review:",
        "did_checklist:",
        "code_review_econ:",
        "econ_writing_skill:",
    ],
    Path("harness/skill_map_reference.md"): [
        "# External Skill Reference Catalog",
        "## Optional Skills (task-specific)",
        "## Reference Skills (inspiration / review framing)",
    ],
}
SKILL_MAP = Path("harness/skill_map_core.yml")
ALLOWED_TIERS = {"core"}
MAX_CORE_SKILLS = 8


def main() -> int:
    failures: list[str] = []

    for path, required_text in REQUIRED_FILES.items():
        if not path.exists():
            failures.append(f"missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [item for item in required_text if item not in text]
        if missing:
            failures.append(f"{path}: missing required content {missing}")

    if yaml is None:
        failures.append("PyYAML is required to validate harness/skill_map_core.yml")
    elif SKILL_MAP.exists():
        data = yaml.safe_load(SKILL_MAP.read_text(encoding="utf-8"))
        skills = data.get("skills", {})
        core_count = 0
        for key, skill in skills.items():
            tier = skill.get("tier")
            if tier not in ALLOWED_TIERS:
                failures.append(f"{key}: invalid or missing tier {tier!r}")
            default_use = skill.get("default_use")
            if default_use is not True:
                failures.append(f"{key}: core skills in skill_map_core.yml must have default_use=true")
            if tier == "core":
                core_count += 1
        if core_count > MAX_CORE_SKILLS:
            failures.append(f"too many core skills: {core_count} > {MAX_CORE_SKILLS}")

    if failures:
        print("FAIL: skill layer problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: skill layer scaffold is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
