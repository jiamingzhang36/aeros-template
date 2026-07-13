#!/usr/bin/env python3
"""Validate AEROS work-lane routing so tasks do not mix work surfaces."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.contract import load_contract  # noqa: E402
from aeros.runtime.work_lane import (  # noqa: E402
    LANE_EXACT_OUTPUTS,
    LANES,
    infer_work_lane,
    lane_policy_path,
    normalize_lane,
    output_lane_problems,
)


def _load_policy(root: Path) -> tuple[dict, list[str]]:
    path = lane_policy_path(root)
    if not path.exists():
        return {}, [f"missing {path.relative_to(root)}"]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {}, [f"{path.relative_to(root)} unreadable: {exc}"]
    if not isinstance(data, dict):
        return {}, [f"{path.relative_to(root)} must be a mapping"]
    return data, []


def main() -> int:
    root = Path.cwd()
    failures: list[str] = []
    policy, policy_failures = _load_policy(root)
    failures.extend(policy_failures)
    declared = set(policy.get("lanes", []) or [])
    if declared and declared != LANES:
        failures.append(
            "harness/work_lane_policy.yml lanes do not match runtime lanes: "
            f"policy={sorted(declared)} runtime={sorted(LANES)}"
        )
    for key in ["principle", "switch_gate", "completion_definitions", "forbidden_cross_lane_substitutions", "exact_output_exceptions"]:
        if key not in policy:
            failures.append(f"harness/work_lane_policy.yml missing {key}")

    declared_exceptions = {
        str(lane): set(str(path) for path in (paths or []))
        for lane, paths in (policy.get("exact_output_exceptions") or {}).items()
    }
    if declared_exceptions != LANE_EXACT_OUTPUTS:
        failures.append(
            "harness/work_lane_policy.yml exact_output_exceptions do not match runtime: "
            f"policy={declared_exceptions} runtime={LANE_EXACT_OUTPUTS}"
        )
    if output_lane_problems("literature", ["tex/references.bib"]):
        failures.append("literature lane must allow exact bibliography metadata path tex/references.bib")
    if not output_lane_problems("literature", ["tex/paper.tex"]):
        failures.append("literature lane must continue to forbid manuscript TeX edits")

    counts: Counter[str] = Counter()
    for path in sorted((root / "tasks").rglob("*.yml")):
        try:
            contract = load_contract(path)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{path.relative_to(root)} unreadable contract: {exc}")
            continue
        explicit = str(contract.raw.get("work_lane", "") or "")
        if explicit and not normalize_lane(explicit):
            failures.append(f"{path.relative_to(root)} invalid work_lane {explicit!r}")
            continue
        lane = infer_work_lane(contract)
        counts[lane] += 1
        if lane not in LANES:
            failures.append(f"{path.relative_to(root)} could not infer valid work_lane")
            continue
        for problem in output_lane_problems(lane, contract.allowed_outputs):
            failures.append(f"{path.relative_to(root)} lane={lane}: {problem}")

    if failures:
        print("FAIL: work-lane policy problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    summary = ", ".join(f"{lane}={counts[lane]}" for lane in sorted(counts))
    print(f"PASS: work lanes are valid ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
