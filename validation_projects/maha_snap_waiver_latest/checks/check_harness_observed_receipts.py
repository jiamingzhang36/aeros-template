#!/usr/bin/env python3
"""Validate harness-generated observed receipt support.

This check exercises the receipt writer with a real temporary subject file. It
does not claim that any research task completed or that the harness result is
scientifically sufficient.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeros.runtime.harness_receipt import sha256_file, write_observed_harness_receipt  # noqa: E402


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros-harness-receipt-") as tmp:
        root = Path(tmp)
        subject = root / "project_manifest.yml"
        subject.write_text("project:\n  name: fixture\n", encoding="utf-8")
        summary = {
            "status": "pass",
            "profile": "fixture",
            "failures": 0,
            "checks": [
                {
                    "name": "checks/check_fixture.py",
                    "status": "pass",
                    "exit_code": 0,
                    "elapsed_seconds": 0.01,
                    "output_tail": ["PASS: fixture"],
                }
            ],
        }
        path, payload = write_observed_harness_receipt(
            root,
            summary,
            ["python", "checks/run_harness_checks.py", "--profile", "fixture"],
            subjects=["project_manifest.yml", "missing.yml"],
        )
        if not path.exists():
            failures.append("receipt file was not written")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        for key in [
            "version",
            "receipt_type",
            "receipt_id",
            "generated_by",
            "generated_at",
            "command",
            "checks",
            "subjects",
            "verification_strength",
            "does_not_prove",
        ]:
            if key not in loaded:
                failures.append(f"receipt missing key: {key}")
        if loaded.get("receipt_type") != "harness_observed_check_run":
            failures.append("receipt_type is not harness_observed_check_run")
        if loaded.get("verification_strength") != "harness_observed_exit_codes_and_file_hashes":
            failures.append("verification_strength does not describe observed exit-code/hash evidence")
        subjects = {item.get("path"): item for item in loaded.get("subjects", [])}
        if subjects.get("project_manifest.yml", {}).get("sha256") != sha256_file(subject):
            failures.append("subject sha256 did not match the observed file")
        if subjects.get("missing.yml", {}).get("exists") is not False:
            failures.append("missing subject was not recorded as missing")
        if "claim support" not in loaded.get("does_not_prove", []):
            failures.append("receipt does_not_prove does not include claim-support boundary")
        if payload != loaded:
            failures.append("returned payload differs from written JSON")

    runner = Path("checks/run_harness_checks.py").read_text(encoding="utf-8")
    if "write_observed_harness_receipt" not in runner:
        failures.append("run_harness_checks.py does not call write_observed_harness_receipt")
    if "--no-observed-receipt" not in runner:
        failures.append("run_harness_checks.py lacks explicit no-observed-receipt escape hatch")

    if failures:
        print("FAIL: harness observed receipt check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: harness observed receipts are generated from observed check outputs and hashes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

