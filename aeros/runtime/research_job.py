"""Compile one high-level ResearchJob into existing AEROS execution objects."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import yaml

from .action_spec import ActionSpec
from .execution_envelope import ExecutionEnvelope


@dataclass(frozen=True)
class ResearchJob:
    job_id: str
    job_type: str
    target: str
    source_candidate: str
    objective: str


@dataclass(frozen=True)
class CompiledResearchJob:
    job: ResearchJob
    task_contract: dict[str, Any]
    action_spec: ActionSpec
    execution_envelope: ExecutionEnvelope

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_job": self.job.__dict__,
            "task_contract": self.task_contract,
            "action_spec": self.action_spec.to_dict(),
            "execution_envelope": self.execution_envelope.to_dict(),
        }


def load_research_job(path: Path) -> ResearchJob:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    required = ["job_id", "job_type", "target", "source_candidate", "objective"]
    missing = [key for key in required if not str(data.get(key) or "").strip()]
    if missing:
        raise ValueError(f"ResearchJob missing: {', '.join(missing)}")
    return ResearchJob(*(str(data[key]).strip() for key in required))


def compile_research_job(job: ResearchJob) -> CompiledResearchJob:
    if job.job_type != "data_probe":
        raise ValueError("ResearchJob v1 supports only job_type=data_probe")
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in job.job_id).strip("_")
    output = f"audits/data_probe/{slug}.json"
    task = {
        "task_id": job.job_id,
        "stage": "discovery",
        "work_lane": "data",
        "goal": job.objective,
        "inputs": [job.source_candidate],
        "checks": ["checks/check_data_probe.py"],
        "allowed_outputs": [output],
        "output_intents": {output: "probe_only"},
        "required_skill_classes": ["data_source"],
        "budget": {"max_agent_calls": 0, "max_dollars": 0},
    }
    command = f"python3 -m aeros.cli data probe plan"
    digest = sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()[:12]
    envelope = ExecutionEnvelope(
        read_roots=(".",), write_roots=("audits/data_probe/",),
        deny_roots=("data/raw/", "data/processed/", "evidence/claim_registry.md", "paper/"),
        expected_outputs=(output,), runtime_profile="isolated-local-probe",
    )
    action = ActionSpec(
        id=f"AS-{digest}", kind="data_probe", lane="data", effect_class="local_write_preview",
        capabilities=("read_project_state", "read_data_inventory", "plan_data_work"),
        expected_outputs=(output,), acceptance_checks=("checks/check_data_probe.py",),
        command=command, stop_condition="probe report produced without canonical or claim admission",
        runtime_profile=envelope.runtime_profile, execution_envelope=envelope.to_dict(),
        authority_boundary={"claim":"none","release":"none","canonical":"none","human_decision_required":"false"},
    )
    return CompiledResearchJob(job, task, action, envelope)


def validate_compilation(compiled: CompiledResearchJob) -> list[str]:
    task_outputs = set(compiled.task_contract.get("allowed_outputs") or [])
    action_outputs = set(compiled.action_spec.expected_outputs)
    envelope_outputs = set(compiled.execution_envelope.expected_outputs)
    failures = []
    if not envelope_outputs <= action_outputs <= task_outputs:
        failures.append("authority expansion: envelope outputs must be subset of ActionSpec outputs, which must be subset of TaskContract outputs")
    for root in compiled.execution_envelope.write_roots:
        if not any(out.startswith(root.rstrip('/') + '/') or out == root.rstrip('/') for out in action_outputs):
            failures.append(f"ExecutionEnvelope write root {root} is not bounded by expected outputs")
    return failures


def write_compiled_job(root: Path, compiled: CompiledResearchJob) -> list[Path]:
    base = root / "contracts/generated" / compiled.job.job_id
    paths = [base.with_suffix(".task.yml"), base.with_suffix(".action.json"), base.with_suffix(".envelope.json")]
    for path in paths: path.parent.mkdir(parents=True, exist_ok=True)
    paths[0].write_text(yaml.safe_dump(compiled.task_contract, sort_keys=False), encoding="utf-8")
    paths[1].write_text(json.dumps(compiled.action_spec.to_dict(), indent=2) + "\n", encoding="utf-8")
    paths[2].write_text(json.dumps(compiled.execution_envelope.to_dict(), indent=2) + "\n", encoding="utf-8")
    return paths

