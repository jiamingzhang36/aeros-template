#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.authority import evaluate_authority
def main()->int:
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); subprocess.run(["git","init"],cwd=root,check=True,capture_output=True)
        subprocess.run(["git","config","user.name","fixture-human"],cwd=root,check=True); subprocess.run(["git","config","user.email","x@y.invalid"],cwd=root,check=True)
        (root/"harness").mkdir(); (root/"decisions/approvals").mkdir(parents=True)
        (root/"harness/permissions.yml").write_text("human_approval:\n  approver_identity: [fixture-human]\n  agent_identity: [fixture-agent]\n",encoding="utf-8")
        art=root/"decisions/approvals/x.yml"; art.write_text("authority_evidence: local_authorship\n",encoding="utf-8")
        subprocess.run(["git","add","."],cwd=root,check=True); subprocess.run(["git","commit","-m","approval"],cwd=root,check=True,capture_output=True)
        local=evaluate_authority(root,art,"local_authorship"); signed=evaluate_authority(root,art,"signed_commit"); external=evaluate_authority(root,art,"external_human_approval")
        failures=[]
        if not local.granted or "real-world human identity is not proven" not in local.reason: failures.append("local_authorship boundary incorrect")
        if signed.granted: failures.append("unsigned commit passed signed_commit authority")
        if external.granted: failures.append("unconfigured external verifier granted authority")
        if failures: print("FAIL: authority evidence"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: tiered authority evidence is fail-closed and locally honest"); return 0
if __name__=="__main__": raise SystemExit(main())
