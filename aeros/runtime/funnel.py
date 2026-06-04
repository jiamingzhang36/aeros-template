"""Two-layer funnel: parallel-generate then select a champion (Team Paper Lite).

TPL slide 17: "并行生成多个，构建一个" — generate N candidates in parallel
(findings, designs, framings), then converge to one champion, recording why each
was pruned. This is exploration breadth WITHOUT the post-hoc selection bias that
the AI-scientist literature flags (arXiv 2509.08713): the selection_criterion is
stated UP FRONT (pre-registration flavor), and selection may not be by
statistical significance alone.

A funnel round lives at discovery/funnels/<round>.yml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

FUNNEL_DIR = Path("discovery/funnels")

# Selection by significance alone is the canonical post-hoc bias; disallow it.
# Substring phrases (matched against the lowercased selection criterion).
SIGNIFICANCE_PHRASES = (
    "significance", "significant", "p-value", "pvalue", "p value",
    "p<0.05", "p < 0.05", "p<.05", "most significant", "lowest p",
    "smallest p", "by p", "stars", "t-stat", "t stat",
)


def _is_significance_only(criterion: str) -> bool:
    c = criterion.strip().lower()
    if not c:
        return False
    return any(phrase in c for phrase in SIGNIFICANCE_PHRASES)


@dataclass
class Candidate:
    id: str
    title: str
    status: str = "candidate"   # candidate | champion | pruned
    viability: str = ""         # measured viability note (data-grounded)
    rationale: str = ""         # why kept / why pruned

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "status": self.status,
                "viability": self.viability, "rationale": self.rationale}


@dataclass
class Funnel:
    round: str
    status: str = "open"        # open | selected
    selection_criterion: str = ""   # MUST be stated before selecting
    champion: str = ""
    selection_rationale: str = ""
    candidates: list[Candidate] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "status": self.status,
            "selection_criterion": self.selection_criterion,
            "champion": self.champion,
            "selection_rationale": self.selection_rationale,
            "created_at": self.created_at,
            "candidates": [c.to_dict() for c in self.candidates],
        }


def funnel_path(project_root: Path, round_name: str) -> Path:
    slug = "".join(c for c in round_name if c.isalnum() or c in "-_") or "round"
    return project_root / FUNNEL_DIR / f"{slug}.yml"


def load_funnel(path: Path) -> Funnel:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cands = [Candidate(id=str(c.get("id", "?")), title=str(c.get("title", "")),
                       status=str(c.get("status", "candidate")),
                       viability=str(c.get("viability", "")),
                       rationale=str(c.get("rationale", "")))
             for c in (data.get("candidates", []) or []) if isinstance(c, dict)]
    return Funnel(
        round=str(data.get("round", path.stem)),
        status=str(data.get("status", "open")),
        selection_criterion=str(data.get("selection_criterion", "")),
        champion=str(data.get("champion", "")),
        selection_rationale=str(data.get("selection_rationale", "")),
        created_at=str(data.get("created_at", "")),
        candidates=cands,
    )


def save_funnel(path: Path, funnel: Funnel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(funnel.to_dict(), sort_keys=False, allow_unicode=True),
                    encoding="utf-8")


def new_funnel(project_root: Path, round_name: str, n: int, criterion: str = "") -> Path:
    funnel = Funnel(
        round=round_name,
        selection_criterion=criterion,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        candidates=[Candidate(id=f"{round_name[:1].upper()}{i}", title=f"(edit) candidate {i}")
                    for i in range(1, max(n, 2) + 1)],
    )
    path = funnel_path(project_root, round_name)
    save_funnel(path, funnel)
    return path


def select_champion(project_root: Path, round_name: str, champion_id: str,
                    rationale: str) -> tuple[Path, list[str]]:
    """Record the champion + prune the rest. Returns (path, problems)."""
    path = funnel_path(project_root, round_name)
    funnel = load_funnel(path)
    problems = _selection_problems(funnel, champion_id, rationale)
    if problems:
        return path, problems
    for c in funnel.candidates:
        if c.id == champion_id:
            c.status = "champion"
        elif c.status != "pruned":
            c.status = "pruned"
            c.rationale = c.rationale or f"not selected under criterion: {funnel.selection_criterion}"
    funnel.champion = champion_id
    funnel.selection_rationale = rationale
    funnel.status = "selected"
    save_funnel(path, funnel)
    return path, []


def _selection_problems(funnel: Funnel, champion_id: str, rationale: str) -> list[str]:
    problems: list[str] = []
    if len(funnel.candidates) < 2:
        problems.append("a funnel needs at least 2 parallel candidates")
    if champion_id not in {c.id for c in funnel.candidates}:
        problems.append(f"champion {champion_id!r} is not among the candidates")
    if not funnel.selection_criterion.strip():
        problems.append("selection_criterion must be stated up front (before selecting)")
    elif _is_significance_only(funnel.selection_criterion):
        problems.append("selection criterion appears to rest on statistical significance — "
                        "state a substantive criterion (significance alone is post-hoc bias)")
    if not rationale.strip():
        problems.append("a selection rationale is required")
    return problems


def validate_selected(funnel: Funnel) -> list[str]:
    """Validate an already-selected funnel (used by the check)."""
    if funnel.status != "selected":
        return []
    problems = _selection_problems(funnel, funnel.champion, funnel.selection_rationale)
    champions = [c for c in funnel.candidates if c.status == "champion"]
    if len(champions) != 1:
        problems.append(f"exactly one champion required; found {len(champions)}")
    return problems
