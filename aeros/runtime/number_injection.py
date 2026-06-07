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

import csv
import re
from pathlib import Path

import yaml

NUMBERS = Path("paper/numbers.yml")
RESULT_INDEX = Path("evidence/result_index.csv")
TOKEN_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")

# Declared, auditable transforms between an artifact cell and its display form.
# A coefficient stored as a fraction is shown in the paper as percentage points
# (x100); keeping the transform explicit means verification re-applies the exact
# same operation instead of trusting a hand-typed derived value.
TRANSFORMS = {
    "identity": lambda x: x,
    "none": lambda x: x,
    "x100": lambda x: x * 100.0,
    "x1000": lambda x: x * 1000.0,
    "neg": lambda x: -x,
    "abs": lambda x: abs(x),
}


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
        # `display` is the typeset string (e.g. "21,748" or "12.5%"); `value` is
        # the canonical numeric that gets verified. display_consistent() keeps
        # them in lock-step so the comma form can never drift from the number.
        if spec.get("display") not in (None, ""):
            return str(spec["display"])
        return _format(spec["value"])

    rendered = TOKEN_RE.sub(_sub, text)
    return rendered, unresolved


def display_consistent(spec: dict) -> tuple[bool, str]:
    """If an entry has a `display` string, its digits must equal `value`.

    Returns (ok, detail). Entries with no display are trivially consistent.
    """
    display = spec.get("display")
    if display in (None, ""):
        return True, ""
    value = spec.get("value")
    cleaned = str(display).replace(",", "").replace(" ", "").rstrip("%")
    try:
        dval = float(cleaned)
        vval = float(value)
    except (TypeError, ValueError):
        return False, f"display '{display}' is not numerically comparable to value {value}"
    if abs(dval - vval) > 1e-9:
        return False, f"display '{display}' ({dval}) != value {value}"
    return True, ""


# --- Cell-level provenance (A2) -------------------------------------------
# Weak trace = "value rounds to *some* number in *any* registered file"; with
# thousands of registered numbers almost anything matches by coincidence. Strong
# trace = "this value = this file, this row, this column (after a declared
# transform)". verify_number enforces the strong form.

def _result_index_path_map(project_root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    idx = project_root / RESULT_INDEX
    if not idx.exists():
        return out
    with idx.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rid = (row.get("result_id") or "").strip()
            path = (row.get("path") or "").strip()
            if rid and path:
                out[rid] = project_root / path
    return out


def _select_row(rows: list[dict], select: dict) -> tuple[dict | None, str]:
    """Return the single row matching all select key==value pairs (string match)."""
    matched = [
        r for r in rows
        if all(str(r.get(k, "")).strip() == str(v).strip() for k, v in select.items())
    ]
    if not matched:
        return None, "no row matches selector"
    if len(matched) > 1:
        return None, f"{len(matched)} rows match selector (need exactly 1)"
    return matched[0], ""


def verify_number(project_root: Path, name: str, spec: dict) -> tuple[str, str]:
    """Cell-level verification of one registry entry.

    Returns (status, detail) with status in {ok, mismatch, no_source, error}.
    `ok`/`mismatch` mean a cell-source was declared and (dis)agreed; `no_source`
    means the entry has no `source:` block and the caller should fall back to the
    weak aggregate trace; `error` means the source block is malformed/unresolvable.
    """
    source = spec.get("source")
    if not isinstance(source, dict):
        return "no_source", "no cell-level source declared"
    value = spec.get("value")
    if value is None:
        return "error", "entry has no value"
    rid = str(source.get("result_id", "")).strip()
    field = str(source.get("field", "")).strip()
    select = source.get("select") or {}
    tname = str(source.get("transform", "identity")).strip() or "identity"
    rdp = source.get("round")
    if not rid or not field:
        return "error", "source needs both result_id and field"
    if not isinstance(select, dict):
        return "error", "source.select must be a mapping"
    if tname not in TRANSFORMS:
        return "error", f"unknown transform '{tname}' (allowed: {sorted(TRANSFORMS)})"
    paths = _result_index_path_map(project_root)
    if rid not in paths:
        return "error", f"result_id '{rid}' not registered in result_index.csv"
    path = paths[rid]
    if not path.exists():
        return "error", f"source file missing: {path}"
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except OSError as exc:
        return "error", f"cannot read {path}: {exc}"
    row, why = _select_row(rows, select)
    if row is None:
        return "error", f"{why} in {rid}"
    if field not in row:
        return "error", f"field '{field}' is not a column in {rid}"
    try:
        raw = float(str(row[field]).strip())
    except (ValueError, TypeError):
        return "error", f"cell {field} is not numeric: {row.get(field)!r}"
    transformed = TRANSFORMS[tname](raw)
    if rdp is None:
        sval = str(value)
        rdp = len(sval.split(".")[1]) if "." in sval else 0
    try:
        rdp = int(rdp)
    except (ValueError, TypeError):
        return "error", f"source.round must be an integer, got {rdp!r}"
    eps = 0.5 * (10 ** (-rdp)) + 1e-9
    if abs(round(transformed, rdp) - round(float(value), rdp)) <= eps:
        return "ok", f"{value} = {tname}({raw}) -> {round(transformed, rdp)} [{rid}]"
    return "mismatch", (
        f"value {value} != {tname}({raw})={round(transformed, rdp)} "
        f"(field {field}, {rid})"
    )


# --- Aggregate (weak) trace helpers, shared by the scan + registry fallback ---

def numeric_tokens(text: str) -> list[float]:
    vals: list[float] = []
    for m in re.finditer(r"[-+]?\d+(?:\.\d+)?", text):
        try:
            vals.append(float(m.group(0)))
        except ValueError:
            continue
    return vals


def verified_values(project_root: Path) -> list[float]:
    """All numeric tokens found across every registered result artifact file."""
    values: list[float] = []
    for path in _result_index_path_map(project_root).values():
        if not path.exists() or not path.is_file():
            continue
        try:
            values.extend(numeric_tokens(path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    return values


def load_whitelist(project_root: Path) -> set[str]:
    path = project_root / "paper" / "number_whitelist.txt"
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        token = line.split("#", 1)[0].strip().replace(" ", "")
        if token:
            out.add(token.rstrip("%"))
    return out


def matches(paper_num: str, verified: list[float], whitelist: set[str]) -> bool:
    """Weak trace: paper_num rounds to some value in the registered corpus."""
    raw = str(paper_num).replace(" ", "")
    bare = raw.rstrip("%")
    if bare in whitelist:
        return True
    try:
        value = float(bare)
    except ValueError:
        return True  # unparseable -> do not flag
    decimals = len(bare.split(".")[1]) if "." in bare else 0
    eps = 0.5 * (10 ** (-decimals)) + 1e-9
    for v in verified:
        if abs(round(v, decimals) - round(value, decimals)) <= eps:
            return True
        if raw.endswith("%") and abs(round(v * 100.0, decimals) - round(value, decimals)) <= eps:
            return True
    return False
