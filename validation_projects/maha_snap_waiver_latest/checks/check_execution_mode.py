#!/usr/bin/env python3
"""Validate execution mode/profile recommendations."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.runtime.execution_mode import recommend_execution_mode  # noqa: E402
from aeros.runtime.mode_compiler import compiled_mode_map  # noqa: E402


POLICY = Path("harness/execution_mode_policy.yml")
REQUIRED_MODES = {
    "smoke_test",
    "bounded_probe",
    "broad_capture",
    "source_capture",
    "paper_release",
    "expensive_api_run",
    "waiting_on_external_input",
}


def main() -> int:
    failures: list[str] = []
    policy_text = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""
    modes = {mode: {} for mode in REQUIRED_MODES if f"  {mode}:" in policy_text}
    for mode in REQUIRED_MODES:
        if mode not in modes:
            failures.append(f"missing execution mode {mode}")
            continue
        for key in ["governance_shell", "check_profile", "max_provider_calls", "max_cost_usd", "requires_human_decision", "allowed_progress_label", "stop_condition"]:
            if key not in policy_text:
                failures.append(f"{mode}: missing {key}")
    if "expensive_api_run:" not in policy_text or "requires_human_decision: true" not in policy_text:
        failures.append("expensive_api_run must require a human decision")
    if "paper_release:" not in policy_text or "allowed_progress_label: DECISION_RECORDED" not in policy_text:
        failures.append("paper_release must use DECISION_RECORDED")

    smoke = recommend_execution_mode(Path.cwd(), lane="data", intent="quick smoke test")
    if smoke.get("mode") != "smoke_test" or smoke.get("check_profile") != "smoke":
        failures.append("smoke-test recommendation did not select smoke_test/smoke")
    broad = recommend_execution_mode(Path.cwd(), lane="data", intent="broad search lead sweep")
    if broad.get("mode") != "broad_capture" or broad.get("claim_surface") != "none_by_construction":
        failures.append("broad search did not select broad_capture with no claim surface")
    api = recommend_execution_mode(Path.cwd(), lane="data", intent="paid API refresh")
    if api.get("mode") != "expensive_api_run" or not api.get("requires_human_decision"):
        failures.append("API intent did not select expensive_api_run with human decision")
    with tempfile.TemporaryDirectory(prefix="aeros_execution_mode_") as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "work/recapture_demo").mkdir(parents=True)
        (tmp / "work/recapture_demo/source.html").write_text("<html></html>", encoding="utf-8")
        report = recommend_execution_mode(tmp, lane="data", intent="denominator probe")
        if report.get("mode") != "bounded_probe":
            failures.append("data probe without git status should remain bounded_probe")
    compiled = compiled_mode_map(Path.cwd())
    required_fields = {"artifact_level", "effect_class", "authority_surface", "execution_budget", "verification_strength"}
    if len(compiled.get("policy_surfaces") or []) < 4:
        failures.append("compiled mode map must name multiple policy surfaces")
    cross_checks = set(compiled.get("cross_checks_run") or [])
    for marker in ["output_intent_policy", "source_capture_permission_policy", "check_profiles"]:
        if not any(marker in item for item in cross_checks):
            failures.append(f"compiled mode map did not cross-check {marker}")
    if not isinstance(compiled.get("contradictions"), list):
        failures.append("compiled mode map must emit a contradictions list")
    elif compiled.get("contradictions"):
        failures.append("compiled mode map reported contradictions: " + "; ".join(compiled.get("contradictions") or []))
    rows = {row.get("preset"): row for row in compiled.get("presets") or []}
    broad_row = rows.get("broad_capture") or {}
    if not broad_row:
        failures.append("compiled mode map missing broad_capture")
    elif {key for key in required_fields if broad_row.get(key)} != required_fields:
        failures.append("compiled broad_capture row missing five-field projection")
    elif broad_row.get("artifact_level") != "lead" or broad_row.get("authority_surface") != "none":
        failures.append("compiled broad_capture row should be lead/none")
    if failures:
        print("FAIL: execution mode problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: execution modes are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
