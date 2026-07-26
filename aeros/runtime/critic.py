"""Independent verification pass (the mechanized critic).

Literature motivation:
- LLMs verify better than they generate, and a *separated* generation/review
  pass beats self-refinement (Stanford "Weaver"/generation-verification gap).
- But self-verification has hard limits (Kambhampati et al. 2402.08115): a model
  cannot reliably check its own reasoning, and a strong generator's errors evade
  a same-strength verifier. So the critic here is advisory: it raises concerns
  for the human gate, it does not certify correctness. The non-LLM backstop is
  `check_output_reproducibility` (a clean re-run the LLM cannot fake).

The critic runs through `provider_connector` (NOT the worker's run_agent), so it
is structurally separate from the generator and can use a different model. It
screens for the empirical-research failure modes catalogued for AI-scientist
systems (arXiv 2509.08713): data leakage, metric misuse, significance-driven
specification selection (p-hacking), and "declares success despite failures".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import provider_connector as pc

# The failure modes the critic must screen for. Each maps to a question the
# critic answers about THIS task's worker output.
FAILURE_MODES = {
    "data_leakage": "Train/test contamination, look-ahead, or using outcome-derived information as a feature.",
    "metric_misuse": "A reported metric that does not match the claim type or the question being asked.",
    "spec_selection": "A preferred specification appears chosen by significance/desired sign rather than pre-stated reasons (p-hacking).",
    "overclaim": "Success/claims asserted beyond what the checks, provenance, or earned claim ceiling support.",
}

_VERDICTS = {"pass", "concerns", "unverified"}


@dataclass
class CriticVerdict:
    verdict: str  # pass | concerns | unverified
    findings: list[dict] = field(default_factory=list)  # [{mode, severity, note}]
    raw: str = ""
    provider: str = ""
    model: str = ""
    review_key: str = ""
    cached: bool = False

    @property
    def has_blocking(self) -> bool:
        return any(str(f.get("severity", "")).lower() == "high" for f in self.findings)

    @property
    def concern_modes(self) -> list[str]:
        return [str(f.get("mode", "?")) for f in self.findings]


def build_critic_prompt(task_id: str, goal: str, evidence: str) -> str:
    modes = "\n".join(f"- {mode}: {desc}" for mode, desc in FAILURE_MODES.items())
    schema = (
        '{"verdict": "pass" | "concerns", '
        '"findings": [{"mode": "<one of: '
        + ", ".join(FAILURE_MODES)
        + '>", "severity": "low|medium|high", "note": "<specific evidence>"}]}'
    )
    return (
        "You are an independent research integrity critic. You did NOT produce the "
        "work below; review it adversarially. Do not be agreeable. Your job is to "
        "find the specific empirical-research failure modes listed, citing concrete "
        "evidence from the material. If you cannot find a failure mode, do not "
        "invent one.\n\n"
        f"## Task\n{task_id}: {goal}\n\n"
        "## Failure modes to screen for\n"
        f"{modes}\n\n"
        "## Worker output / changed evidence\n"
        f"{evidence[:12000]}\n\n"
        "## Required output\n"
        "Return ONLY a fenced ```json block matching exactly this schema:\n"
        f"{schema}\n"
        "Use verdict 'pass' only if you found no failure mode. Mark severity 'high' "
        "only for a concern that should block the gate until a human resolves it."
    )


def parse_verdict(text: str) -> tuple[str, list[dict]]:
    """Lenient parse of the critic's JSON verdict. Unparseable -> 'unverified'."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    blob = match.group(1) if match else None
    if blob is None:
        # Try a bare JSON object anywhere in the text.
        match = re.search(r"\{.*\"verdict\".*\}", text, flags=re.S)
        blob = match.group(0) if match else None
    if blob is None:
        return "unverified", []
    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, ValueError):
        return "unverified", []
    verdict = str(data.get("verdict", "unverified")).strip().lower()
    if verdict not in _VERDICTS:
        verdict = "unverified"
    findings = data.get("findings", []) or []
    clean: list[dict] = []
    for f in findings if isinstance(findings, list) else []:
        if not isinstance(f, dict):
            continue
        clean.append({
            "mode": str(f.get("mode", "?")),
            "severity": str(f.get("severity", "low")).lower(),
            "note": str(f.get("note", "")).strip(),
        })
    if verdict == "pass" and clean:
        verdict = "concerns"  # findings contradict a pass
    return verdict, clean


def run_critic(*, task_id: str, goal: str, evidence: str,
               provider: str = "mock", model: str = "mock-critic",
               timeout_seconds: int = 120) -> CriticVerdict:
    """Run one independent critic pass. Never raises into the caller; a provider
    failure yields an 'unverified' verdict (advisory, so it must not crash the loop)."""
    prompt = build_critic_prompt(task_id, goal, evidence)
    try:
        engine = pc.make_provider(provider, model=model, timeout_seconds=timeout_seconds)
        resp = engine.complete(prompt, {"prompt_id": f"critic-{task_id}", "persona": "critic",
                                        "prompt_variant": "integrity_review"})
        raw = resp.output_text
        verdict, findings = parse_verdict(raw)
        return CriticVerdict(verdict=verdict, findings=findings, raw=raw,
                             provider=resp.provider, model=resp.model)
    except pc.ProviderError as exc:
        return CriticVerdict(verdict="unverified", findings=[], raw=f"provider error: {exc}",
                             provider=provider, model=model)
    except Exception as exc:  # noqa: BLE001 - advisory pass must never break the run
        return CriticVerdict(verdict="unverified", findings=[], raw=f"critic error: {exc}",
                             provider=provider, model=model)


def _cache_path(project_root: Path, review_key: str) -> Path:
    # Runtime state is denied to candidate workers; agent_runs/ may be a declared
    # worker output and therefore must not hold authority-bearing review cache.
    return project_root / "aeros" / "state" / "critic_reviews" / f"{review_key}.json"


def load_cached_verdict(project_root: Path, review_key: str) -> CriticVerdict | None:
    path = _cache_path(project_root, review_key)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if data.get("review_key") != review_key:
        return None
    return CriticVerdict(
        verdict=str(data.get("verdict", "unverified")),
        findings=list(data.get("findings") or []),
        raw=str(data.get("raw", "")),
        provider=str(data.get("provider", "")),
        model=str(data.get("model", "")),
        review_key=review_key,
        cached=True,
    )


def save_cached_verdict(project_root: Path, verdict: CriticVerdict) -> Path:
    path = _cache_path(project_root, verdict.review_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "review_key": verdict.review_key,
        "verdict": verdict.verdict,
        "findings": verdict.findings,
        "raw": verdict.raw,
        "provider": verdict.provider,
        "model": verdict.model,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_critic_report(
    project_root: Path,
    task_id: str,
    verdict: CriticVerdict,
    *,
    risk: str = "unknown",
    required: bool = False,
    human_gate_required: bool = False,
) -> Path:
    out_dir = project_root / "agent_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task_id}_critic.md"
    lines = [
        f"# Independent Critic Report: {task_id}",
        "",
        f"- verdict: {verdict.verdict}",
        f"- provider: {verdict.provider} / {verdict.model}",
        f"- completion risk: {risk}",
        f"- critic required: {'yes' if required else 'no'}",
        f"- human gate required: {'yes' if human_gate_required else 'no'}",
        f"- review key: {verdict.review_key or 'n/a'}",
        f"- reused cached review: {'yes' if verdict.cached else 'no'}",
        f"- blocking findings: {'yes' if verdict.has_blocking else 'no'}",
        "",
        "## Findings",
        "",
    ]
    if not verdict.findings:
        lines.append("None recorded.")
    else:
        for f in verdict.findings:
            lines.append(f"- [{f['severity']}] {f['mode']}: {f['note']}")
    lines += [
        "",
        "## Note",
        "",
        "Advisory only. An LLM critic improves but does not certify correctness "
        "(self-verification has known limits); the non-LLM backstop is "
        "`check_output_reproducibility`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
