#!/usr/bin/env python3
from pathlib import Path
import json, os, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.research_job import ResearchJob, compile_research_job, validate_compilation
from aeros.runtime.execution_envelope import execute_action_spec_in_isolated_worktree
from aeros.runtime.adaptive_checks import select_checks
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
    if failures:
        print("FAIL: ResearchJob compiler"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: data_probe ResearchJob compiles, executes in isolation, and passes adaptive post-checks"); return 0
if __name__ == "__main__": raise SystemExit(main())
