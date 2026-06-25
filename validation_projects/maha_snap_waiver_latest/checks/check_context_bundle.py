#!/usr/bin/env python3
"""Validate AEROS context bundle plumbing and honesty boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path.cwd()
REQUIRED_FILES = [
    ROOT / "aeros/runtime/context_bundle.py",
    ROOT / "harness/context_budget.yml",
    ROOT / "templates/CONTEXT_BUNDLE.md",
    ROOT / "CONTEXT_BUNDLE.md",
]


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing {path}")
    cli = ROOT / "aeros/cli.py"
    if cli.exists() and "context" not in cli.read_text(encoding="utf-8"):
        failures.append("aeros/cli.py: missing context command wiring")
    if (ROOT / "aeros/runtime/context_bundle.py").exists():
        sys.path.insert(0, str(ROOT))
        try:
            from aeros.runtime.context_bundle import build_context_bundle, format_context_bundle
            bundle = build_context_bundle(ROOT, lane="project", brief=True)
            rendered = format_context_bundle(bundle, brief=True)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"context bundle generation failed: {exc}")
        else:
            for key in ["current_goal", "next_action", "stop_rule", "does_not_prove", "source_hashes", "context_staleness"]:
                if key not in bundle:
                    failures.append(f"context bundle missing key: {key}")
            next_action = bundle.get("next_action") or {}
            if next_action.get("status_label") in {"SUBSTANTIVE_PRODUCED", "SUBSTANTIVE_DONE"} and not bundle.get("latest_substantive_artifact"):
                failures.append("context bundle cannot imply substantive production without latest_substantive_artifact")
            for marker in ["recommended_next_action", "status_label", "context_stale", "stop_rule", "does_not_prove"]:
                if marker not in rendered:
                    failures.append(f"rendered context missing marker: {marker}")
    template = ROOT / "templates/CONTEXT_BUNDLE.md"
    if template.exists():
        text = template.read_text(encoding="utf-8")
        for marker in ["does_not_prove", "stop_rule", "This bundle is context"]:
            if marker not in text:
                failures.append(f"{template}: missing marker {marker!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: context bundle plumbing is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
