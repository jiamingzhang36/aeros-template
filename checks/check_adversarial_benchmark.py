#!/usr/bin/env python3
"""Validate and exercise the adversarial benchmark scaffold.

Executable fixtures deliberately create failure modes that AEROS must detect:
false completion, stale result provenance, fake full text, claim-ceiling escape,
and stale artifact-bound human approval.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

import yaml


PATH = Path("harness/adversarial_benchmark.yml")
EXIT_ZERO_FIXTURE = Path("tests/adversarial/exit_zero_no_output.py")
STALE_REGISTRY_FIXTURE = Path("tests/adversarial/stale_registry.py")
FALSE_FULLTEXT_FIXTURE = Path("tests/adversarial/false_fulltext.py")
CLAIM_CEILING_FIXTURE = Path("tests/adversarial/claim_ceiling_escape.py")
STALE_HUMAN_APPROVAL_FIXTURE = Path("tests/adversarial/stale_human_approval.py")
NOOP_CHECK = Path("checks/check_noop_runs.py")
PROVENANCE_CHECK = Path("checks/check_provenance.py")
CLAIM_CEILING_CHECK = Path("checks/check_claim_ceiling.py")
APPROVAL_FRESHNESS_CHECK = Path("checks/check_approval_freshness.py")
REQUIRED = {
    "false_fulltext",
    "exit_zero_no_output",
    "stale_registry",
    "claim_ceiling_escape",
    "stale_human_approval",
    "session_scope_drift",
    "wrong_python_runtime",
    "undeclared_credential",
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _resolve_project_or_template(root: Path, rel: Path) -> Path:
    project_path = root / rel
    if project_path.exists():
        return project_path
    if rel.parts and rel.parts[0] == "checks":
        sibling = Path(__file__).resolve().parent / rel.name
        if sibling.exists():
            return sibling
    if rel.parts and rel.parts[0] == "tests":
        template_root = Path(__file__).resolve().parent.parent
        candidate = template_root / rel
        if candidate.exists():
            return candidate
    return project_path


def _exercise_exit_zero_no_output(root: Path) -> list[str]:
    failures: list[str] = []
    fixture_path = _resolve_project_or_template(root, EXIT_ZERO_FIXTURE)
    noop_check_path = _resolve_project_or_template(root, NOOP_CHECK)
    if not fixture_path.exists():
        return [f"missing executable fixture {EXIT_ZERO_FIXTURE}"]
    if not noop_check_path.exists():
        return [f"missing detection check {NOOP_CHECK}"]

    with tempfile.TemporaryDirectory(prefix="aeros_adv_noop_") as tmp_name:
        tmp = Path(tmp_name)
        task_id = "ADV_exit_zero_no_output"
        declared_output = tmp / "outputs" / "missing.csv"
        _write_text(
            tmp / "tasks" / "discovery" / f"{task_id}.yml",
            f"""task_id: {task_id}
stage: discovery
gate: G0
work_lane: data
goal: "Adversarial fixture: command exits 0 but declared output is absent."
allowed_outputs:
  - outputs/missing.csv
checks: []
""",
        )
        _write_text(
            tmp / "aeros_state.yml",
            f"""current_stage: discovery
current_gate: G0
gate_status: open
candidate_stage: discovery
candidate_gate: G0
tasks:
  {task_id}:
    status: passed
gate_history: []
candidate_gate_history: []
gate_decisions: []
""",
        )
        fixture_run = subprocess.run(
            [
                sys.executable,
                str(fixture_path.resolve()),
                "--declared-output",
                str(declared_output),
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if fixture_run.returncode != 0:
            failures.append(f"exit_zero_no_output fixture did not exit 0: {fixture_run.stderr.strip()}")
        if declared_output.exists():
            failures.append("exit_zero_no_output fixture unexpectedly created the declared output")

        detection = subprocess.run(
            [sys.executable, str(noop_check_path.resolve())],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        output = f"{detection.stdout}\n{detection.stderr}"
        if detection.returncode == 0:
            failures.append("exit_zero_no_output was not detected by check_noop_runs.py")
        if task_id not in output:
            failures.append("check_noop_runs.py did not identify the adversarial task id")
    return failures


def _exercise_stale_registry(root: Path) -> list[str]:
    failures: list[str] = []
    fixture_path = _resolve_project_or_template(root, STALE_REGISTRY_FIXTURE)
    provenance_check_path = _resolve_project_or_template(root, PROVENANCE_CHECK)
    if not fixture_path.exists():
        return [f"missing executable fixture {STALE_REGISTRY_FIXTURE}"]
    if not provenance_check_path.exists():
        return [f"missing detection check {PROVENANCE_CHECK}"]

    with tempfile.TemporaryDirectory(prefix="aeros_adv_stale_registry_") as tmp_name:
        tmp = Path(tmp_name)
        result_id = "R_ADV_STALE_001"
        artifact = tmp / "outputs" / "tables" / "stale.csv"
        _write_text(artifact, "before\n")
        _write_text(
            tmp / "evidence" / "result_index.csv",
            "result_id,path,script_or_source,created_date,linked_claims\n"
            f"{result_id},outputs/tables/stale.csv,tests/adversarial/stale_registry.py,2026-06-23,\n",
        )
        _write_text(
            tmp / "outputs" / ".provenance" / f"{result_id}.json",
            json.dumps(
                {
                    "result_id": result_id,
                    "output_path": "outputs/tables/stale.csv",
                    "created_at": "2026-06-23T00:00:00+00:00",
                    "script_or_source": "tests/adversarial/stale_registry.py",
                    "sha256": _sha256(artifact),
                },
                indent=2,
            )
            + "\n",
        )
        fixture_run = subprocess.run(
            [
                sys.executable,
                str(fixture_path.resolve()),
                "--artifact",
                str(artifact),
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if fixture_run.returncode != 0:
            failures.append(f"stale_registry fixture did not exit 0: {fixture_run.stderr.strip()}")
        detection = subprocess.run(
            [sys.executable, str(provenance_check_path.resolve())],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        output = f"{detection.stdout}\n{detection.stderr}"
        if detection.returncode == 0:
            failures.append("stale_registry was not detected by check_provenance.py")
        if result_id not in output or "sha256 mismatch" not in output:
            failures.append("check_provenance.py did not identify the stale registry sha256 mismatch")
    return failures


def _exercise_false_fulltext(root: Path) -> list[str]:
    failures: list[str] = []
    fixture_path = _resolve_project_or_template(root, FALSE_FULLTEXT_FIXTURE)
    if not fixture_path.exists():
        return [f"missing executable fixture {FALSE_FULLTEXT_FIXTURE}"]

    with tempfile.TemporaryDirectory(prefix="aeros_adv_false_fulltext_") as tmp_name:
        tmp = Path(tmp_name)
        candidate = tmp / "downloads" / "candidate.html"
        fixture_run = subprocess.run(
            [
                sys.executable,
                str(fixture_path.resolve()),
                "--output",
                str(candidate),
                "--kind",
                "cloudflare",
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if fixture_run.returncode != 0:
            failures.append(f"false_fulltext fixture did not exit 0: {fixture_run.stderr.strip()}")
        if not candidate.exists():
            failures.append("false_fulltext fixture did not create candidate HTML")
            return failures
        sys.path.insert(0, str(root.resolve()))
        try:
            from aeros.runtime import literature_adapter as adapter  # noqa: WPS433
        except Exception as exc:  # pragma: no cover - import should be stable in checked repos
            failures.append(f"could not import literature_adapter verifier: {exc}")
            return failures
        verdict = adapter.verify_fulltext_candidate_content(
            candidate.read_text(encoding="utf-8"),
            content_type="text/html",
            expected_title="Target economics article",
            expected_doi="10.0000/target",
        )
        if verdict.get("verdict") != "blocked" or verdict.get("blocker_reason") != "security_challenge":
            failures.append(f"false_fulltext was not blocked as a security challenge: {verdict!r}")
    return failures


def _exercise_claim_ceiling_escape(root: Path) -> list[str]:
    failures: list[str] = []
    fixture_path = _resolve_project_or_template(root, CLAIM_CEILING_FIXTURE)
    ceiling_check_path = _resolve_project_or_template(root, CLAIM_CEILING_CHECK)
    if not fixture_path.exists():
        return [f"missing executable fixture {CLAIM_CEILING_FIXTURE}"]
    if not ceiling_check_path.exists():
        return [f"missing detection check {CLAIM_CEILING_CHECK}"]

    with tempfile.TemporaryDirectory(prefix="aeros_adv_claim_ceiling_") as tmp_name:
        tmp = Path(tmp_name)
        fixture_run = subprocess.run(
            [sys.executable, str(fixture_path.resolve()), "--root", str(tmp)],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if fixture_run.returncode != 0:
            failures.append(f"claim_ceiling_escape fixture did not exit 0: {fixture_run.stderr.strip()}")
        detection = subprocess.run(
            [sys.executable, str(ceiling_check_path.resolve())],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        output = f"{detection.stdout}\n{detection.stderr}"
        if detection.returncode == 0:
            failures.append("claim_ceiling_escape was not detected by check_claim_ceiling.py")
        if "C_ADV" not in output or "exceeds earned ceiling" not in output:
            failures.append("check_claim_ceiling.py did not identify the adversarial over-claim")
    return failures


def _exercise_stale_human_approval(root: Path) -> list[str]:
    failures: list[str] = []
    fixture_path = _resolve_project_or_template(root, STALE_HUMAN_APPROVAL_FIXTURE)
    approval_check_path = _resolve_project_or_template(root, APPROVAL_FRESHNESS_CHECK)
    if not fixture_path.exists():
        return [f"missing executable fixture {STALE_HUMAN_APPROVAL_FIXTURE}"]
    if not approval_check_path.exists():
        return [f"missing detection check {APPROVAL_FRESHNESS_CHECK}"]

    with tempfile.TemporaryDirectory(prefix="aeros_adv_stale_approval_") as tmp_name:
        tmp = Path(tmp_name)
        fixture_run = subprocess.run(
            [sys.executable, str(fixture_path.resolve()), "--root", str(tmp)],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if fixture_run.returncode != 0:
            failures.append(f"stale_human_approval fixture did not exit 0: {fixture_run.stderr.strip()}")
        detection = subprocess.run(
            [sys.executable, str(approval_check_path.resolve())],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        output = f"{detection.stdout}\n{detection.stderr}"
        if detection.returncode == 0:
            failures.append("stale_human_approval was not detected by check_approval_freshness.py")
        if "approval is stale" not in output or "paper/draft.md" not in output:
            failures.append("check_approval_freshness.py did not identify the stale artifact approval")
    return failures


def main() -> int:
    root = Path.cwd()
    if not PATH.exists():
        print(f"FAIL: missing {PATH}")
        return 1
    data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
    scenario_rows = [
        item for item in data.get("scenarios", [])
        if isinstance(item, dict) and item.get("id")
    ]
    scenarios = {str(item.get("id")) for item in scenario_rows}
    failures: list[str] = []
    missing = REQUIRED - scenarios
    if missing:
        for item in sorted(missing):
            failures.append(f"missing scenario {item}")
    exit_zero = next((item for item in scenario_rows if item.get("id") == "exit_zero_no_output"), {})
    if exit_zero.get("executable_fixture") != str(EXIT_ZERO_FIXTURE):
        failures.append("exit_zero_no_output missing executable_fixture wiring")
    if exit_zero.get("detection_check") != str(NOOP_CHECK):
        failures.append("exit_zero_no_output missing detection_check wiring")
    stale_registry = next((item for item in scenario_rows if item.get("id") == "stale_registry"), {})
    if stale_registry.get("executable_fixture") != str(STALE_REGISTRY_FIXTURE):
        failures.append("stale_registry missing executable_fixture wiring")
    if stale_registry.get("detection_check") != str(PROVENANCE_CHECK):
        failures.append("stale_registry missing detection_check wiring")
    false_fulltext = next((item for item in scenario_rows if item.get("id") == "false_fulltext"), {})
    if false_fulltext.get("executable_fixture") != str(FALSE_FULLTEXT_FIXTURE):
        failures.append("false_fulltext missing executable_fixture wiring")
    claim_ceiling = next((item for item in scenario_rows if item.get("id") == "claim_ceiling_escape"), {})
    if claim_ceiling.get("executable_fixture") != str(CLAIM_CEILING_FIXTURE):
        failures.append("claim_ceiling_escape missing executable_fixture wiring")
    if claim_ceiling.get("detection_check") != str(CLAIM_CEILING_CHECK):
        failures.append("claim_ceiling_escape missing detection_check wiring")
    stale_approval = next((item for item in scenario_rows if item.get("id") == "stale_human_approval"), {})
    if stale_approval.get("executable_fixture") != str(STALE_HUMAN_APPROVAL_FIXTURE):
        failures.append("stale_human_approval missing executable_fixture wiring")
    if stale_approval.get("detection_check") != str(APPROVAL_FRESHNESS_CHECK):
        failures.append("stale_human_approval missing detection_check wiring")
    failures.extend(_exercise_false_fulltext(root))
    failures.extend(_exercise_exit_zero_no_output(root))
    failures.extend(_exercise_stale_registry(root))
    failures.extend(_exercise_claim_ceiling_escape(root))
    failures.extend(_exercise_stale_human_approval(root))

    if failures:
        print("FAIL: adversarial benchmark problems detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "PASS: adversarial benchmark fixtures detected false_fulltext, "
        "exit_zero_no_output, stale_registry, claim_ceiling_escape, and "
        "stale_human_approval"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
