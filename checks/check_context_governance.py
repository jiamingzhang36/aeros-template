#!/usr/bin/env python3
"""Validate AEROS context governance and Context Compiler boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeros.runtime.context_compiler import audit_context_brief, build_context_brief, format_context_brief  # noqa: E402


REQUIRED_FILES = [
    ROOT / "aeros/runtime/context_compiler.py",
    ROOT / "harness/context_governance.yml",
    ROOT / "templates/CONTEXT_BRIEF.md",
    ROOT / "CONTEXT_BRIEF.md",
]


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")
    policy_path = ROOT / "harness/context_governance.yml"
    policy = {}
    if policy_path.exists():
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        if "active attention allocation" not in str(policy.get("principle", "")).lower():
            failures.append("context governance policy missing active-attention principle")
        for section in [
            "goal_context",
            "state_context",
            "evidence_context",
            "decision_context",
            "noise_context",
            "next_action",
            "attention_contract",
            "communication_budget",
        ]:
            if section not in (policy.get("required_sections") or []):
                failures.append(f"context governance policy missing required section {section}")
        communication = policy.get("communication_budget") or {}
        if communication.get("target") != "output_only":
            failures.append("context governance communication budget must target output_only")
        exact = {str(item).lower() for item in communication.get("preserve_exact") or []}
        for required in ["code", "commands", "errors", "hashes"]:
            if required not in exact:
                failures.append(f"context governance communication budget must preserve {required}")
        do_not = " ".join(str(item).lower() for item in communication.get("do_not_compress") or [])
        if "source evidence" not in do_not:
            failures.append("context governance communication budget must not compress source evidence")
    cli = ROOT / "aeros/cli.py"
    if cli.exists():
        text = cli.read_text(encoding="utf-8")
        for marker in ["context_command", "build_context_brief", "audit_context_brief"]:
            if marker not in text:
                failures.append(f"aeros/cli.py missing context compiler marker {marker}")
    try:
        brief = build_context_brief(ROOT, lane="project")
        rendered = format_context_brief(brief)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"context brief generation failed: {exc}")
        brief = {}
        rendered = ""
    if brief:
        failures.extend(audit_context_brief(brief))
        for section in [
            "Goal Context",
            "State Context",
            "Evidence Context",
            "Decision Context",
            "Noise Context",
            "Next Action",
            "Attention Contract",
            "Communication Budget",
            "Does Not Prove",
        ]:
            if section not in rendered:
                failures.append(f"rendered context brief missing {section}")
        if "Raw tool output" not in rendered or "compressed" not in rendered:
            failures.append("rendered context brief missing raw-output compression rule")
        if "Compress communication, not evidence" not in rendered or "output_only" not in rendered:
            failures.append("rendered context brief missing communication compression boundary")
        if "This brief is compiled context" not in rendered:
            failures.append("rendered context brief missing non-authority boundary")
        max_lines = int(policy.get("max_lines", 120) or 120)
        if len(rendered.splitlines()) > max_lines:
            failures.append(f"rendered context brief exceeds max_lines ({len(rendered.splitlines())}>{max_lines})")
    template = ROOT / "templates/CONTEXT_BRIEF.md"
    if template.exists():
        text = template.read_text(encoding="utf-8")
        for marker in [
            "Context is not storage",
            "Goal Context",
            "Noise Context",
            "raw_output_policy",
            "Communication Budget",
            "preserve_exact",
            "Does Not Prove",
        ]:
            if marker not in text:
                failures.append(f"templates/CONTEXT_BRIEF.md missing {marker!r}")
    if failures:
        print("FAIL: context governance problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: context governance and compiler boundaries are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
