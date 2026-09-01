#!/usr/bin/env python3
"""Exercise the evaluation-first data-probe ExecutableRubric vertical slice."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aeros.runtime.executable_rubric import _scientific_content_hash, _verify_probe_criteria, active_rubric_issue, default_rubric_path, draft_executable_rubric, freeze_executable_rubric, validate_executable_rubric, verify_executable_rubric, write_executable_rubric, write_verification_report  # noqa: E402
from aeros.runtime.research_job import ResearchJob, compile_research_job, validate_compilation, write_compiled_job  # noqa: E402


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aeros_executable_rubric_") as name:
        root = Path(name)
        for directory in ("data", "docs", "harness", "decisions/approvals"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / "data/source.csv").write_text("county,year,value\nA,2024,1\nB,2024,2\n", encoding="utf-8")
        (root / "docs/data_contract.yml").write_text(yaml.safe_dump({"estimand_data_contract": {"unit_of_observation": "county-year", "population": "US counties", "required_fields": ["county", "year", "value"], "join_keys": ["county", "year"], "minimum_coverage": "2 rows", "maximum_missingness": "0", "probe_success_condition": "Observe at least two rows with all required fields."}}, sort_keys=False), encoding="utf-8")
        (root / "harness/permissions.yml").write_text("human_approval:\n  approver_identity: []\n  agent_identity: [aeros-agent]\n  trusted_signers: []\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "fixture"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, capture_output=True)
        job = ResearchJob("PROBE-RUBRIC", "data_probe", "C1", "data/source.csv", "verify bounded feasibility")
        compiled = compile_research_job(job)
        failures.extend("compiled: " + item for item in validate_compilation(compiled))
        generated = write_compiled_job(root, compiled)
        if len(generated) != 4 or not generated[-1].is_file(): failures.append("ResearchJob compilation did not materialize a rubric skeleton")
        rubric = draft_executable_rubric(root, job)
        failures.extend("draft: " + item for item in validate_executable_rubric(rubric))
        if rubric["scientific_freeze"].get("missing_required_fields"): failures.append("visible DataContract fields were not grounded into the candidate rubric")
        rubric_path = write_executable_rubric(root, rubric)
        blocked = verify_executable_rubric(root, rubric_path)
        if blocked.get("status") != "BLOCKED" or "human_frozen_probe_contract" not in blocked.get("unmet_criteria", []): failures.append("candidate rubric was not blocked pending a human freeze")
        if active_rubric_issue(root) is not None: failures.append("candidate-only rubric should not hijack Drive priority")
        approval = root / "decisions/approvals/rubric.yml"
        approval.write_text(yaml.safe_dump({"rubric_id": rubric["rubric_id"], "decision": "freeze_executable_rubric", "rubric_content_sha256": _scientific_content_hash(rubric), "authority_evidence": "local_authorship", "authority_scope": {"executable_rubric_freeze_only": True}}, sort_keys=False), encoding="utf-8")
        if freeze_executable_rubric(root, rubric_path, approval).get("status") != "REFUSED": failures.append("unsigned/uncommitted rubric approval unexpectedly froze a rubric")
        frozen = deepcopy(rubric); frozen["status"] = "human_frozen"; frozen["scientific_freeze"].update({"state": "human_frozen", "frozen_candidate_sha256": _scientific_content_hash(rubric)})
        artifact = root / "audits/data_probe/probe_rubric.json"; artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps({"target": "C1", "source": "data/source.csv", "source_sha256": sha256((root / "data/source.csv").read_bytes()).hexdigest(), "rows_observed": 2, "columns_observed": ["county", "year", "value"], "status": "probe_observed", "does_not_prove": ["data fitness", "canonical admission", "claim support"]}), encoding="utf-8")
        if any(item.get("status") != "verified" for item in _verify_probe_criteria(root, frozen)): failures.append("criterion-level probe verification rejected a matching bounded artifact")
        (root / "data/source.csv").write_text("county,year,value\nA,2024,9\n", encoding="utf-8")
        stale = next(item for item in _verify_probe_criteria(root, frozen) if item["criterion_id"] == "bounded_source_profile")
        if stale.get("status") != "unmet" or "source_sha256" not in stale.get("reason", ""): failures.append("criterion verification did not catch stale source provenance")
        if not write_verification_report(root, blocked).is_file(): failures.append("criterion verification report was not written")
        if default_rubric_path(root, job.job_id) != rubric_path: failures.append("rubric default path is not deterministic")
    if failures:
        print("FAIL: ExecutableRubric problems detected:"); [print("- " + item) for item in failures]; return 1
    print("PASS: executable rubric drafts, human-freeze boundaries, criterion verification, and ResearchJob compilation are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
