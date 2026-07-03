#!/usr/bin/env python3
"""Validate task mode workflow presets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aeros.runtime.task_mode import DEFAULT_MODES, infer_task_mode

POLICY = Path("harness/task_mode_policy.yml")
REQUIRED = set(DEFAULT_MODES)


def main() -> int:
    failures: list[str] = []
    data = yaml.safe_load(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    modes = (data or {}).get("modes") or {}
    missing = REQUIRED - set(modes)
    if missing:
        failures.append(f"missing task modes: {sorted(missing)}")
    for name in REQUIRED & set(modes):
        spec = modes.get(name) or {}
        for key in ("workflow_preset", "execution_mode", "allowed_output_intents"):
            if key not in spec:
                failures.append(f"{name}: missing {key}")

    cases = [
        ("", "tidy up the folder structure", "general_guardrail"),
        ("data", "broad search lead sweep into lead queue", "broad_capture"),
        ("data", "recapture sources in browser", "source_capture"),
        ("data", "repair denominator data inventory", "data_repair"),
        ("data", "audit claim ceiling", "claim_audit"),
        ("data", "sync Word paper draft", "writing_sync"),
        ("data", "submission preflight", "submission_readiness"),
        ("data", "wrong route need negative seed first", "route_recovery"),
    ]
    for lane, intent, expected in cases:
        report = infer_task_mode(ROOT, lane=lane, intent=intent)
        if report["task_mode"] != expected:
            failures.append(f"intent {intent!r}: expected {expected}, got {report['task_mode']}")
    if "--json" in sys.argv:
        print(json.dumps({"status": "fail" if failures else "pass", "failures": failures}, ensure_ascii=False))
    elif failures:
        print("FAIL: task mode problems detected")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("PASS: task modes are valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
