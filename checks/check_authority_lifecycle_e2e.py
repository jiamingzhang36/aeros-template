#!/usr/bin/env python3
"""Real SSH E2E for bootstrap, rotation, revocation, and gate authority."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aeros.runtime.authority import bootstrap_ssh_signer, evaluate_for_action  # noqa: E402
from aeros.runtime.identity import write_approval_request  # noqa: E402
from aeros.runtime.plan_deck import Card, Deck, write_deck  # noqa: E402


def run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=root, text=True, capture_output=True, check=check)


def sign_config(root: Path, key: Path, principal: str) -> None:
    allowed = root / "allowed_signers_runtime"
    allowed.write_text(f"{principal} {key.with_suffix('.pub').read_text(encoding='utf-8').strip()}\n", encoding="utf-8")
    run(root, "git", "config", "gpg.format", "ssh")
    run(root, "git", "config", "user.signingkey", str(key))
    run(root, "git", "config", "gpg.ssh.allowedSignersFile", str(allowed))


def fingerprint(key: Path) -> str:
    result = subprocess.run(["ssh-keygen", "-lf", str(key.with_suffix(".pub")), "-E", "sha256"], text=True, capture_output=True, check=True)
    return result.stdout.split()[1]


def commit(root: Path, message: str, *paths: str, signed: bool = True) -> None:
    run(root, "git", "add", *paths)
    command = ["git", "commit"] + (["-S"] if signed else []) + ["-m", message]
    run(root, *command)


def cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "aeros.cli", *args], cwd=root, env=env, text=True, capture_output=True)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_authority_lifecycle_") as name:
        root = Path(name)
        for directory in ("harness", "checks", "decisions/approvals", "decisions/plans"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        run(root, "git", "init")
        run(root, "git", "config", "user.name", "fixture-human")
        run(root, "git", "config", "user.email", "fixture@example.invalid")
        key1, key2 = root / "human_key_1", root / "human_key_2"
        for key in (key1, key2):
            run(root, "ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
        policy = root / "harness/permissions.yml"
        policy.write_text(
            "human_approval:\n  enforcement: git_committer\n  approver_identity: [fixture-human]\n"
            "  agent_identity: [fixture-agent]\n  approval_artifact_dir: decisions/approvals\n"
            "  minimum_authority: {campaign_release: signed_commit, gate_approval: signed_commit, gate_apply: signed_commit}\n"
            "  trusted_signers: []\n",
            encoding="utf-8",
        )
        (root / "project_manifest.yml").write_text("project:\n  name: authority_lifecycle_e2e\n", encoding="utf-8")
        (root / "checks/check_gate_exit.py").write_text(
            "def evaluate_through_gate(gate, project_root=None):\n    return True, []\n", encoding="utf-8"
        )
        commit(root, "unsigned pre-trust baseline", "harness/permissions.yml", "project_manifest.yml", "checks/check_gate_exit.py", signed=False)

        # First enrollment is an explicit TOFU ceremony and its policy commit is signed by that key.
        bootstrap_ssh_signer(
            root, identity="fixture-human", principal="fixture@example.invalid",
            public_key=key1.with_suffix(".pub").read_text(encoding="utf-8"),
            confirmed_fingerprint=fingerprint(key1),
        )
        sign_config(root, key1, "fixture@example.invalid")
        commit(root, "bootstrap trusted signer", "harness/permissions.yml")

        # A malicious repository allowed-signers config cannot replace the
        # signer anchored in the committed permissions policy.
        sign_config(root, key2, "fixture@example.invalid")
        attacker_approval = write_approval_request(root, gate="G2", stage="discovery", requested_by="attacker", note="self grant")
        commit(root, "attacker self-signed approval", str(attacker_approval.relative_to(root)))
        if evaluate_for_action(root, attacker_approval, "gate_approval").granted:
            failures.append("repository-local attacker key replaced the protected signer binding")
        sign_config(root, key1, "fixture@example.invalid")

        # Positive gate approve with the trusted key.
        approval = write_approval_request(root, gate="G3", stage="discovery", requested_by="fixture", note="fixture")
        commit(root, "signed G3 approval", str(approval.relative_to(root)))
        approved = cli(root, "gate", "approve", "G3", "--stage", "discovery", "--force")
        if approved.returncode != 0:
            failures.append(f"trusted signed gate approve failed: {approved.stderr or approved.stdout}")

        # Positive gate apply uses the same floor and signed deck.
        deck = write_deck(root, Deck(gate="G4", stage="execution", cards=[Card(id="A", title="bounded action")]))
        commit(root, "signed G4 plan", str(deck.relative_to(root)))
        applied = cli(root, "gate", "apply", "G4", "--stage", "execution", "--force")
        if applied.returncode != 0:
            failures.append(f"trusted signed gate apply failed: {applied.stderr or applied.stdout}")

        # Rotate to key2. The policy change itself must be signed by key1.
        data = yaml.safe_load(policy.read_text(encoding="utf-8")) or {}
        data["human_approval"]["trusted_signers"] = [{
            "identity": "fixture-human", "principal": "fixture@example.invalid",
            "ssh_public_key": key2.with_suffix(".pub").read_text(encoding="utf-8").strip(),
        }]
        policy.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        commit(root, "rotate authority signer", "harness/permissions.yml")
        if evaluate_for_action(root, approval, "gate_approval").granted:
            failures.append("approval signed by revoked key remained valid after signer rotation")

        # The new key works after old-key-authorized rotation.
        sign_config(root, key2, "fixture@example.invalid")
        new_approval = write_approval_request(root, gate="G5", stage="execution", requested_by="fixture", note="fixture")
        commit(root, "signed G5 approval", str(new_approval.relative_to(root)))
        if not evaluate_for_action(root, new_approval, "gate_approval").granted:
            failures.append("approval signed by rotated-in key was rejected")

        # Spoofed local authorship cannot use --force to cross the gate floor.
        spoof = write_approval_request(root, gate="G6", stage="execution", requested_by="agent", note="spoof")
        spoof.write_text(spoof.read_text(encoding="utf-8").replace("signed_commit", "local_authorship", 1), encoding="utf-8")
        commit(root, "spoofed local gate approval", str(spoof.relative_to(root)), signed=False)
        forced = cli(root, "gate", "approve", "G6", "--stage", "execution", "--force")
        if forced.returncode == 0:
            failures.append("gate approve --force bypassed the signed authority floor")

    if failures:
        print("FAIL: authority lifecycle E2E")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: bootstrap, signed gate approve/apply, rotation, revocation, and force resistance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
