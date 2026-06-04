"""Number injection: paper numbers sourced by construction, not typed by hand.

Team Paper Lite "结果与正文绑定" / AutoResearchClaw VerifiedRegistry, in its
strongest form. Instead of *detecting* fabricated numbers after the fact (which
can only ever be a partial net), invert the problem: the paper references values
by name -- `{{ate}}`, `{{n_obs}}` -- and a build step substitutes the value from
a verified registry (paper/numbers.yml). Every injected number is then sourced by
construction, including integers (sample sizes, counts) that a free-text scan
cannot safely flag.

This module is pure load/substitute. The grounding rule -- every registry value
must trace to a registered result artifact -- is enforced by check_paper_numbers
so there is a single source of truth for "verified".
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

NUMBERS = Path("paper/numbers.yml")
TOKEN_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")


def load_numbers(project_root: Path) -> dict[str, dict]:
    """Return {name: {value, result_id, note}} from paper/numbers.yml (or {})."""
    path = project_root / NUMBERS
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{NUMBERS} is not valid YAML: {exc}") from exc
    numbers = data.get("numbers", data) if isinstance(data, dict) else {}
    out: dict[str, dict] = {}
    if isinstance(numbers, dict):
        for name, spec in numbers.items():
            if isinstance(spec, dict):
                out[str(name)] = spec
            else:  # bare scalar shorthand: name: 0.34
                out[str(name)] = {"value": spec}
    return out


def tokens_in(text: str) -> list[str]:
    return [m.group(1) for m in TOKEN_RE.finditer(text)]


def _format(value) -> str:
    if isinstance(value, float):
        # trim trailing zeros but keep meaningful precision
        return f"{value:.10g}"
    return str(value)


def render_paper(text: str, numbers: dict[str, dict]) -> tuple[str, list[str]]:
    """Substitute {{name}} tokens. Returns (rendered_text, unresolved_names)."""
    unresolved: list[str] = []

    def _sub(m: re.Match) -> str:
        name = m.group(1)
        spec = numbers.get(name)
        if spec is None or "value" not in spec:
            unresolved.append(name)
            return m.group(0)
        return _format(spec["value"])

    rendered = TOKEN_RE.sub(_sub, text)
    return rendered, unresolved
