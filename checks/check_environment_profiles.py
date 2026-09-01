#!/usr/bin/env python3
"""Exercise ActionSpec -> EnvironmentProfile -> Envelope compilation."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.action_spec import declared_action_spec, validate_action_spec  # noqa: E402
from aeros.runtime.environment_profile import environment_profile_errors  # noqa: E402
from aeros.runtime.execution_envelope import default_envelope_for_action_spec  # noqa: E402


def main() -> int:
    failures: list[str] = []
    capture = declared_action_spec(
        kind="official_source_capture", effect_class="local_write_preview", lane="data",
        capabilities=("network_official_source",), expected_outputs=("data/probes/fixture/source.json",),
        command="python3 checks/check_environment_profiles.py", stop_condition="bounded fixture", runtime_profile="isolated-capture",
    )
    capture_envelope = default_envelope_for_action_spec(capture)
    if capture.environment_profile.get("profile") != "capture":
        failures.append("official source capture did not compile to capture environment")
    if capture_envelope.network_policy != "public_web_only" or capture_envelope.credential_policy != "scrub_all":
        failures.append("capture environment did not carry public-web and credential-scrub policy")
    if not any(root.startswith("data/probes/") for root in capture_envelope.write_roots):
        failures.append("capture environment incorrectly widened or removed declared probe output root")
    if not capture.environment_approval_fingerprint or ":" not in capture.idempotency_key:
        failures.append("ActionSpec did not bind profile digest into execution/approval identity")
    failures.extend(validate_action_spec(capture))

    analysis = declared_action_spec(
        kind="run_specification", effect_class="local_write_preview", lane="analysis",
        expected_outputs=("outputs/econ/specification_runs/fixture.json",),
        command="python3 checks/check_environment_profiles.py", stop_condition="candidate result", runtime_profile="isolated-analysis",
    )
    analysis_envelope = default_envelope_for_action_spec(analysis)
    if analysis.environment_profile.get("profile") != "analysis" or analysis_envelope.network_policy != "deny":
        failures.append("specification run did not compile to network-denied analysis environment")
    if "outputs/econ/specification_runs/" not in analysis_envelope.write_roots:
        failures.append("analysis environment did not retain narrowed candidate output root")

    manuscript = declared_action_spec(
        kind="manuscript_candidate", effect_class="local_write_preview", lane="writing",
        expected_outputs=("paper/main.tex",), command="python3 checks/check_environment_profiles.py", stop_condition="candidate draft",
    )
    manuscript_envelope = default_envelope_for_action_spec(manuscript)
    manuscript_errors = environment_profile_errors(manuscript.to_dict(), manuscript_envelope.to_dict())
    if manuscript.environment_profile.get("profile") != "manuscript":
        failures.append("writing task did not compile to manuscript environment")
    if not any("paper/main.tex" in item for item in manuscript_errors):
        failures.append("manuscript environment allowed direct canonical paper output")

    promotion = declared_action_spec(
        kind="promotion", effect_class="human_decision", lane="release",
        expected_outputs=(), command="aeros approve", stop_condition="human decision recorded", requires_decision=True,
        authority_boundary={"claim": "none", "canonical": "promote", "release": "none", "human_decision_required": "true"},
    )
    if promotion.environment_profile.get("profile") != "promotion":
        failures.append("promotion boundary did not compile to promotion environment")
    if promotion.environment_profile.get("credential_policy") != "human_injected_only":
        failures.append("promotion environment did not require human-injected credentials")

    if failures:
        print("FAIL: environment profile compilation problems detected")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: ActionSpec environment profiles narrow envelopes and bind policy identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
