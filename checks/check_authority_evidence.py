#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.authority import evaluate_authority, evaluate_for_action
def main()->int:
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); subprocess.run(["git","init"],cwd=root,check=True,capture_output=True)
        subprocess.run(["git","config","user.name","fixture-human"],cwd=root,check=True); subprocess.run(["git","config","user.email","x@y.invalid"],cwd=root,check=True)
        (root/"harness").mkdir(); (root/"decisions/approvals").mkdir(parents=True)
        (root/"harness/permissions.yml").write_text("human_approval:\n  approver_identity: [fixture-human]\n  agent_identity: [fixture-agent]\n",encoding="utf-8")
        art=root/"decisions/approvals/x.yml"; art.write_text("authority_evidence: local_authorship\n",encoding="utf-8")
        subprocess.run(["git","add","."],cwd=root,check=True); subprocess.run(["git","commit","-m","approval"],cwd=root,check=True,capture_output=True)
        local=evaluate_authority(root,art,"local_authorship"); signed=evaluate_authority(root,art,"signed_commit"); external=evaluate_authority(root,art,"external_human_approval"); release=evaluate_for_action(root,art,"campaign_release")
        failures=[]
        if not local.granted or "real-world human identity is not proven" not in local.reason: failures.append("local_authorship boundary incorrect")
        if signed.granted: failures.append("unsigned commit passed signed_commit authority")
        if release.granted or "requires at least signed_commit" not in release.reason: failures.append("spoofable local_authorship released a campaign breaker")
        if external.granted: failures.append("unconfigured external verifier granted authority")
        # A repository-local allowedSignersFile must not become a trust anchor.
        legit=root/"legit"; attacker=root/"attacker"
        for key in (legit, attacker):
            subprocess.run(["ssh-keygen","-q","-t","ed25519","-N","","-f",str(key)],cwd=root,check=True,capture_output=True)
        trusted=legit.with_suffix(".pub").read_text(encoding="utf-8").strip()
        policy=(root/"harness/permissions.yml")
        policy.write_text(
            "human_approval:\n  approver_identity: [fixture-human]\n  agent_identity: [fixture-agent]\n"
            "  minimum_authority: {campaign_release: signed_commit}\n  trusted_signers:\n"
            "    - identity: fixture-human\n      principal: fixture@example.invalid\n"
            f"      ssh_public_key: {trusted}\n",encoding="utf-8")
        subprocess.run(["git","add","harness/permissions.yml"],cwd=root,check=True)
        subprocess.run(["git","commit","-m","protected trust anchor"],cwd=root,check=True,capture_output=True)
        malicious=root/"malicious_allowed_signers"
        malicious.write_text("fixture@example.invalid "+attacker.with_suffix(".pub").read_text(encoding="utf-8"),encoding="utf-8")
        subprocess.run(["git","config","gpg.format","ssh"],cwd=root,check=True)
        subprocess.run(["git","config","user.signingkey",str(attacker)],cwd=root,check=True)
        subprocess.run(["git","config","gpg.ssh.allowedSignersFile",str(malicious)],cwd=root,check=True)
        art.write_text("authority_evidence: signed_commit\n",encoding="utf-8")
        subprocess.run(["git","add",str(art.relative_to(root))],cwd=root,check=True)
        subprocess.run(["git","commit","-S","-m","attacker self approval"],cwd=root,check=True,capture_output=True)
        attack=evaluate_for_action(root,art,"campaign_release")
        if attack.granted: failures.append("attacker-controlled repository allowedSignersFile bypassed protected signer binding")
        # An uncommitted trust-policy edit must fail closed even if it enrolls the attacker.
        policy.write_text(policy.read_text(encoding="utf-8")+f"\n# attempted key enrollment\n",encoding="utf-8")
        tampered=evaluate_for_action(root,art,"campaign_release")
        if tampered.granted or "uncommitted changes" not in tampered.reason: failures.append("uncommitted permissions tampering did not fail closed")
        if failures: print("FAIL: authority evidence"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: tiered authority evidence is fail-closed and locally honest"); return 0
if __name__=="__main__": raise SystemExit(main())
