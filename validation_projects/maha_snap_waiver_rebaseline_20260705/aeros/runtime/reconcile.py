"""Post-pipeline reconciliation for derived AEROS control indexes.

`aeros reconcile` is intentionally low-authority. It refreshes derived indexes
after a real pipeline changes registered artifacts, but it never approves gates,
upgrades claims, or treats pipeline output as scientifically valid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Iterable


DOES_NOT_PROVE = [
    "that the pipeline results are scientifically valid",
    "that any claim is supported or upgraded",
    "that any human gate is approved",
    "that stale tasks are recovered",
    "that data access, literature extraction, or release compliance is complete",
]


@dataclass(frozen=True)
class ReconcileStep:
    name: str
    argv: list[str]
    reason: str
    writes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReconcileResult:
    step: ReconcileStep
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class ReconcileReport:
    project_root: Path
    generated_at: str
    dry_run: bool
    steps: list[ReconcileStep]
    results: list[ReconcileResult]

    @property
    def ok(self) -> bool:
        return self.dry_run or all(result.returncode == 0 for result in self.results)


def _base_argv() -> list[str]:
    return [sys.executable, "-m", "aeros.cli"]


def build_reconcile_plan(
    project_root: Path,
    *,
    skip_result_index: bool = False,
    skip_provenance: bool = False,
    skip_graph: bool = False,
    skip_state: bool = False,
    include_context: bool = False,
) -> list[ReconcileStep]:
    """Return the deterministic reconciliation plan for a project.

    Result-index sync is included only when the project has a result registry;
    provenance, research graph, and global state are the core post-pipeline
    derived layers.
    """
    base = _base_argv()
    steps: list[ReconcileStep] = []
    if not skip_result_index and (project_root / "evidence/result_registry.csv").exists():
        steps.append(ReconcileStep(
            name="result_index",
            argv=base + ["paper-ci", "sync-result-index"],
            reason="derive evidence/result_index.csv rows from evidence/result_registry.csv",
            writes=["evidence/result_index.csv", "outputs/.provenance/*.json"],
        ))
    if not skip_provenance:
        steps.append(ReconcileStep(
            name="provenance",
            argv=base + ["provenance", "sync"],
            reason="refresh outputs/.provenance hashes from current result artifacts",
            writes=["outputs/.provenance/*.json"],
        ))
    if not skip_graph:
        steps.append(ReconcileStep(
            name="research_graph",
            argv=base + ["graph", "build"],
            reason="rebuild evidence/research_graph.yml from registries and provenance",
            writes=["evidence/research_graph.yml"],
        ))
    if not skip_state:
        steps.append(ReconcileStep(
            name="global_state",
            argv=base + ["state", "global"],
            reason="rebuild aeros/state/global_state.yml as a derived project index",
            writes=["aeros/state/global_state.yml"],
        ))
    if include_context:
        steps.append(ReconcileStep(
            name="context_bundle",
            argv=base + ["context", "--write", "--brief"],
            reason="refresh lightweight human/agent context after derived indexes change",
            writes=["CONTEXT_BUNDLE.md", "outputs/context/context_bundle.json"],
        ))
    return steps


def run_reconcile(
    project_root: Path,
    *,
    dry_run: bool = False,
    timeout_seconds: int = 120,
    skip_result_index: bool = False,
    skip_provenance: bool = False,
    skip_graph: bool = False,
    skip_state: bool = False,
    include_context: bool = False,
) -> ReconcileReport:
    steps = build_reconcile_plan(
        project_root,
        skip_result_index=skip_result_index,
        skip_provenance=skip_provenance,
        skip_graph=skip_graph,
        skip_state=skip_state,
        include_context=include_context,
    )
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if dry_run:
        return ReconcileReport(project_root, generated_at, True, steps, [])

    results: list[ReconcileResult] = []
    for step in steps:
        try:
            proc = subprocess.run(
                step.argv,
                cwd=project_root,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
            results.append(ReconcileResult(
                step=step,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            ))
        except subprocess.TimeoutExpired as exc:
            results.append(ReconcileResult(
                step=step,
                returncode=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or f"timeout after {timeout_seconds}s",
                timed_out=True,
            ))
            break
        if results[-1].returncode != 0:
            break
    return ReconcileReport(project_root, generated_at, False, steps, results)


def _clip(text: str, limit: int = 1600) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n... [truncated]"


def _fmt_cmd(argv: Iterable[str]) -> str:
    return " ".join(argv)


def format_reconcile_report(report: ReconcileReport) -> str:
    lines = [
        "# AEROS Reconcile Report",
        "",
        f"generated_at: {report.generated_at}",
        f"project_root: {report.project_root}",
        f"dry_run: {str(report.dry_run).lower()}",
        f"status: {'PASS' if report.ok else 'FAIL'}",
        "",
        "## Plan",
    ]
    if not report.steps:
        lines.append("- no reconcile steps selected")
    for step in report.steps:
        writes = ", ".join(step.writes) if step.writes else "none"
        lines.append(f"- {step.name}: `{_fmt_cmd(step.argv)}`")
        lines.append(f"  reason: {step.reason}")
        lines.append(f"  writes: {writes}")

    if report.results:
        lines.extend(["", "## Results"])
        for result in report.results:
            lines.append(f"- {result.step.name}: exit_code={result.returncode}")
            if result.timed_out:
                lines.append("  timed_out: true")
            if result.stdout.strip():
                lines.append("  stdout:")
                lines.append("```")
                lines.append(_clip(result.stdout))
                lines.append("```")
            if result.stderr.strip():
                lines.append("  stderr:")
                lines.append("```")
                lines.append(_clip(result.stderr))
                lines.append("```")

    lines.extend(["", "## does_not_prove"])
    for item in DOES_NOT_PROVE:
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def write_reconcile_report(project_root: Path, report: ReconcileReport) -> Path:
    stamp = report.generated_at.replace(":", "").replace("+00:00", "Z")
    path = project_root / "outputs/logs" / f"aeros_reconcile_{stamp}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_reconcile_report(report), encoding="utf-8")
    return path
