#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.adaptive_checks import RISK_DOMAINS, select_checks
ROOT = Path(__file__).resolve().parents[1]
def main() -> int:
    failures=[]
    paper=select_checks(ROOT,["tex/paper.tex"])
    data=select_checks(ROOT,["data/processed/panel.csv"])
    approval=select_checks(ROOT,["decisions/approvals/G3.md"])
    if "paper_binding_integrity" not in paper["risk_domains"] or "check_manuscript_citation_faithfulness.py" not in paper["checks"]: failures.append("paper changes did not select paper-binding checks")
    if "data_sample_integrity" not in data["risk_domains"] or "check_provenance.py" not in data["checks"]: failures.append("data changes did not select data/provenance checks")
    if "release_reproduction_integrity" not in approval["risk_domains"]: failures.append("approval changes did not select authority checks")
    if len(RISK_DOMAINS)!=6: failures.append("risk-domain model must contain exactly six domains")
    if failures: print("FAIL: adaptive checks"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: observed writes select checks across six risk domains"); return 0
if __name__ == "__main__": raise SystemExit(main())

