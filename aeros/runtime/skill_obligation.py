"""Skill obligation helpers.

Skill obligations make skill consideration auditable without turning skills into
research authority.  A task that is skill-eligible must either declare allowed
or recommended skills for the relevant class, mark the class required, or carry
an explicit waiver/blocker.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - normal AEROS env has PyYAML
    yaml = None

from .contract import Contract
from .skill_receipt import load_core_skill_map


POLICY_PATH = Path("harness/skill_obligation_policy.yml")

DEFAULT_CLASSES: dict[str, dict[str, Any]] = {
    "data_source": {
        "skills": ["data-inventory", "data-quality-checker", "data-merge-audit"],
        "triggers": ["data", "source", "probe", "capture", "inventory", "denominator", "gdp", "schema"],
    },
    "literature": {
        "skills": ["academic-research-suite", "lit-review-assistant"],
        "triggers": ["literature", "citation", "paper_registry", "full-text", "fulltext", "synthesis"],
    },
    "writing": {
        "skills": ["econ-write", "pre-submission-audit"],
        "triggers": ["paper", "draft", "writing", "submission", "referee", "response"],
    },
    "causal_identification": {
        "skills": ["causal-id-review", "did-checklist"],
        "triggers": ["identification", "causal", "did", "event study", "method_card", "design"],
    },
    "replication": {
        "skills": ["code-review-econ", "replication-check"],
        "triggers": ["replication", "reproduc", "provenance", "pipeline", "result_validation", "code_review"],
    },
}

MECHANICAL_WAIVER_CLASSES = {
    "ledger_hash_only",
    "typo_only",
    "mechanical_revalidation",
    "single_line_parser_patch",
}


def _norm_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


@lru_cache(maxsize=16)
def _load_policy(root: Path) -> dict[str, Any]:
    path = root / POLICY_PATH
    if not path.exists() or yaml is None:
        return {"classes": DEFAULT_CLASSES}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"classes": DEFAULT_CLASSES}


def obligation_classes(root: Path) -> dict[str, dict[str, Any]]:
    policy = _load_policy(root)
    classes = policy.get("classes") or DEFAULT_CLASSES
    out: dict[str, dict[str, Any]] = {}
    for name, spec in classes.items():
        if isinstance(spec, dict):
            out[str(name)] = {
                "skills": _norm_list(spec.get("skills")),
                "triggers": _norm_list(spec.get("triggers")),
            }
    return out or DEFAULT_CLASSES


def explicit_skill_obligations(contract: Contract) -> list[str]:
    return _norm_list(contract.raw.get("skill_obligations"))


def skill_waivers(contract: Contract) -> list[dict[str, Any]]:
    return [item for item in (contract.raw.get("skill_waivers") or []) if isinstance(item, dict)]


def infer_skill_obligations(project_root: Path, contract: Contract) -> list[str]:
    explicit = explicit_skill_obligations(contract)
    if explicit:
        return explicit
    if (
        _norm_list(contract.raw.get("allowed_skills"))
        or _norm_list(contract.raw.get("recommended_skills"))
        or _norm_list(contract.raw.get("required_skill_classes"))
        or skill_waivers(contract)
    ):
        return []
    if contract.work_lane == "harness":
        return []
    blob = " ".join(
        [
            contract.task_id,
            contract.stage,
            contract.gate,
            contract.work_lane,
            contract.goal,
            " ".join(contract.checks),
            " ".join(contract.allowed_outputs),
            " ".join(contract.inputs),
        ]
    ).lower()
    inferred: list[str] = []
    for cls, spec in obligation_classes(project_root).items():
        triggers = [str(t).lower() for t in spec.get("triggers", [])]
        if any(token and token in blob for token in triggers):
            inferred.append(cls)
    return inferred


def _waived_classes(contract: Contract) -> set[str]:
    waived: set[str] = set()
    for waiver in skill_waivers(contract):
        cls = str(waiver.get("skill_class", "")).strip()
        if cls:
            waived.add(cls)
    return waived


def skill_obligation_report(project_root: Path, contract: Contract) -> dict[str, Any]:
    classes = obligation_classes(project_root)
    obligations = infer_skill_obligations(project_root, contract)
    allowed = set(_norm_list(contract.raw.get("allowed_skills")))
    recommended = set(_norm_list(contract.raw.get("recommended_skills")))
    required = set(_norm_list(contract.raw.get("required_skill_classes")))
    waived = _waived_classes(contract)
    known_skills = set(load_core_skill_map(project_root))
    failures: list[str] = []
    rows: list[dict[str, Any]] = []

    for cls in obligations:
        spec = classes.get(cls, {})
        candidate_skills = set(_norm_list(spec.get("skills")))
        declared = sorted((allowed | recommended) & candidate_skills)
        satisfied = bool(declared) or cls in required or cls in waived or "all" in waived
        if not satisfied:
            failures.append(
                f"{contract.task_id}: skill obligation {cls!r} has no allowed/recommended skill, required class, or waiver"
            )
        for skill in sorted(candidate_skills):
            if skill not in known_skills:
                failures.append(f"{contract.task_id}: obligation {cls!r} references unknown skill {skill!r}")
        rows.append(
            {
                "skill_class": cls,
                "candidate_skills": sorted(candidate_skills),
                "declared_skills": declared,
                "required_class": cls in required,
                "waived": cls in waived or "all" in waived,
                "satisfied": satisfied,
            }
        )
    return {
        "task_id": contract.task_id,
        "skill_obligations": obligations,
        "rows": rows,
        "failures": failures,
        "does_not_prove": [
            "that a skill was invoked",
            "that skill output is correct",
            "that research claims are supported",
            "that a human gate is approved",
        ],
    }


def validate_skill_coverage(project_root: Path, contracts: dict[str, tuple[Contract, Path]]) -> list[str]:
    failures: list[str] = []
    for _task_id, (contract, _path) in sorted(contracts.items()):
        failures.extend(skill_obligation_report(project_root, contract)["failures"])
    return failures
