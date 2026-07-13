#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.adaptive_checks import RISK_DOMAINS, assess_post_action, select_checks
ROOT = Path(__file__).resolve().parents[1]
def main() -> int:
    failures=[]
    paper=select_checks(ROOT,["tex/paper.tex"])
    data=select_checks(ROOT,["data/processed/panel.csv"])
    approval=select_checks(ROOT,["decisions/approvals/G3.md"])
    analysis=select_checks(ROOT,["outputs/analysis/model.csv","outputs/figures/figure.png"])
    econ_analysis=select_checks(ROOT,["outputs/econ/specification_runs/run.json"])
    manuscript=select_checks(ROOT,["docs/manuscript/paper.md"])
    if "paper_binding_integrity" not in paper["risk_domains"] or "check_manuscript_citation_faithfulness.py" not in paper["checks"]: failures.append("paper changes did not select paper-binding checks")
    if "data_sample_integrity" not in data["risk_domains"] or "check_provenance.py" not in data["checks"]: failures.append("data changes did not select data/provenance checks")
    if "release_reproduction_integrity" not in approval["risk_domains"]: failures.append("approval changes did not select authority checks")
    required_result_checks={"check_result_registry.py","check_output_reproducibility.py","check_provenance.py"}
    if "specification_integrity" not in analysis["risk_domains"] or not required_result_checks.issubset(set(analysis["checks"])):
        failures.append("analysis/figure outputs did not select result/provenance checks")
    if "specification_integrity" not in econ_analysis["risk_domains"]:
        failures.append("economics specification output did not select specification-integrity checks")
    if "paper_binding_integrity" not in manuscript["risk_domains"] or not required_result_checks.issubset(set(manuscript["checks"])):
        failures.append("docs/manuscript work did not select result/provenance checks")

    passed=assess_post_action(
        ROOT,
        ["outputs/analysis/model.csv"],
        action_exit_code=0,
        expected_outputs=["harness/adaptive_checks.yml"],
    )
    if passed.get("status")!="PASS": failures.append("successful action with a non-empty expected artifact did not pass")
    failed=assess_post_action(
        ROOT,
        ["outputs/analysis/model.csv"],
        action_exit_code=7,
        expected_outputs=["harness/adaptive_checks.yml"],
    )
    if failed.get("status")!="FAIL" or "action_exit_nonzero:7" not in failed.get("blockers",[]):
        failures.append("nonzero action exit did not fail closed")
    missing=assess_post_action(ROOT,["outputs/analysis/model.csv"],action_exit_code=0,expected_outputs=[])
    if missing.get("status")!="FAIL" or "expected_outputs_not_declared" not in missing.get("blockers",[]):
        failures.append("missing expected outputs did not fail closed")

    cli=subprocess.run(
        [
            sys.executable,"-m","aeros.cli","checks","select",
            "--changed","outputs/analysis/model.csv",
            "--action-exit","9",
            "--expected-output","harness/adaptive_checks.yml",
        ],
        cwd=ROOT,text=True,capture_output=True,timeout=20,
    )
    try:
        cli_payload=json.loads(cli.stdout)
    except json.JSONDecodeError:
        cli_payload={}
    if cli.returncode==0 or cli_payload.get("status")!="FAIL":
        failures.append("CLI post-action selector did not propagate action failure")
    if len(RISK_DOMAINS)!=6: failures.append("risk-domain model must contain exactly six domains")
    if failures: print("FAIL: adaptive checks"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: observed writes select checks across six risk domains"); return 0
if __name__ == "__main__": raise SystemExit(main())
