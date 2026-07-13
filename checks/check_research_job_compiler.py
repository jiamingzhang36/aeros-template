#!/usr/bin/env python3
from pathlib import Path
import json, os, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.research_job import ResearchJob, compile_research_job, validate_compilation
from aeros.runtime.execution_envelope import execute_action_spec_in_isolated_worktree
from aeros.runtime.adaptive_checks import select_checks
from aeros.runtime.drive import build_drive_report
ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    compiled = compile_research_job(ResearchJob("PROBE-C1-ACS","data_probe","C1","census_acs_2024","verify bounded feasibility"))
    failures = validate_compilation(compiled)
    if compiled.action_spec.kind != "data_probe" or compiled.execution_envelope.runtime_profile != "isolated-local-probe": failures.append("data_probe vertical slice compiled incorrectly")
    with tempfile.TemporaryDirectory(prefix="aeros_job_e2e_") as name:
        root = Path(name)
        for d in ("data", "harness", "checks"):
            (root / d).mkdir(parents=True, exist_ok=True)
        (root / "data/source.csv").write_text("county,year,value\nA,2024,1\nB,2024,2\n", encoding="utf-8")
        (root / "harness/adaptive_checks.yml").write_text((ROOT / "harness/adaptive_checks.yml").read_text(encoding="utf-8"), encoding="utf-8")
        fixture_check = root / "checks/check_data_probe.py"
        fixture_check.write_text(
            "from pathlib import Path\nimport json\np=next(Path('audits/data_probe').glob('*.json'))\n"
            "d=json.loads(p.read_text())\nraise SystemExit(0 if d.get('rows_observed')==2 and d.get('source_sha256') else 1)\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "fixture"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, capture_output=True)
        executable = compile_research_job(ResearchJob("PROBE-E2E","data_probe","C1","data/source.csv","bounded real probe"))
        old_pythonpath = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = str(ROOT) + os.pathsep + (old_pythonpath or "")
        try:
            result = execute_action_spec_in_isolated_worktree(root, executable.action_spec, timeout_seconds=20)
        finally:
            if old_pythonpath is None: os.environ.pop("PYTHONPATH", None)
            else: os.environ["PYTHONPATH"] = old_pythonpath
        if not result.ok or result.accepted_outputs != ("audits/data_probe/probe_e2e.json",):
            failures.append(f"isolated data-probe execution failed: {result}")
        plan = select_checks(root, list(result.observed_writes))
        if "data_sample_integrity" not in plan.get("risk_domains", []) or "check_data_probe.py" not in plan.get("checks", []):
            failures.append("observed probe output did not select data/sample post-checks")
        else:
            post = subprocess.run([sys.executable, "checks/check_data_probe.py"], cwd=root)
            if post.returncode != 0: failures.append("adaptive post-check failed over accepted probe artifact")
        (root / "evidence/econ").mkdir(parents=True, exist_ok=True)
        (root / "evidence/econ/specification_registry.csv").write_text(
            "spec_id,estimand_id,sample_id,outcome,treatment,controls,fixed_effects,cluster,weights,window,estimator,software,package_versions,protocol,status\n"
            "SP-OLS,E1,S1,y,d,none,none,none,none,all,ols,python,stdlib,none,registered\n",
            encoding="utf-8",
        )
        (root / "data/spec_sample.csv").write_text(
            "y,d\n1,0\n3,1\n5,2\n7,3\n9,4\n", encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "registered specification fixture"], cwd=root, check=True, capture_output=True)
        specification = compile_research_job(ResearchJob(
            "RUNSPEC-E2E", "run_specification", "SP-OLS", "data/spec_sample.csv", "bounded OLS fixture",
        ))
        failures.extend(validate_compilation(specification))
        spec_result = execute_action_spec_in_isolated_worktree(root, specification.action_spec, timeout_seconds=20)
        expected_spec_outputs = (
            "outputs/econ/specification_runs/runspec_e2e.json",
            "outputs/econ/specification_runs/runspec_e2e_exhibit.csv",
        )
        if not spec_result.ok or spec_result.accepted_outputs != expected_spec_outputs:
            failures.append(f"isolated run_specification execution failed: {spec_result}")
        else:
            payload = json.loads((root / expected_spec_outputs[0]).read_text(encoding="utf-8"))
            estimate = (((payload.get("result") or {}).get("coefficients") or {}).get("d") or {}).get("estimate")
            if payload.get("admission_status") != "nonproduction" or abs(float(estimate) - 2.0) > 1e-9:
                failures.append("run_specification did not produce the expected nonproduction OLS result")
            spec_plan = select_checks(root, list(spec_result.observed_writes))
            if "specification_integrity" not in spec_plan.get("risk_domains", []):
                failures.append("candidate specification outputs did not select specification-integrity checks")
        driven = build_drive_report(
            root,
            job="run_specification",
            execute=True,
            source_candidate="data/spec_sample.csv",
            target="SP-OLS",
        )
        drive_execution = driven.get("execution") or {}
        if driven.get("status") != "EXECUTED" or drive_execution.get("status") != "pass":
            failures.append(f"drive run_specification vertical slice failed: {driven}")
        if set(drive_execution.get("accepted_outputs") or []) != {
            "outputs/econ/specification_runs/drive_run_specification.json",
            "outputs/econ/specification_runs/drive_run_specification_exhibit.csv",
        }:
            failures.append("drive run_specification did not accept exactly the declared candidate outputs")
    if failures:
        print("FAIL: ResearchJob compiler"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: data_probe and run_specification ResearchJobs compile and execute in isolation"); return 0
if __name__ == "__main__": raise SystemExit(main())
