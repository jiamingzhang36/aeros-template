#!/usr/bin/env python3
"""Exercise source-bound candidate-paragraph compilation without a provider."""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from aeros.runtime.literature_adapter import PAPER_REGISTRY_COLUMNS  # noqa: E402
from aeros.runtime.literature_paragraph import ParagraphCandidateArgs, compile_candidate_paragraphs  # noqa: E402


def _fixture(root: Path, *, complete: bool) -> None:
    registry = root / "discovery/literature/paper_registry.csv"
    registry.parent.mkdir(parents=True, exist_ok=True)
    with registry.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAPER_REGISTRY_COLUMNS)
        writer.writeheader()
        writer.writerow({"paper_id": "P001", "citation_key": "example2026", "title": "Benefit access and program take-up", "authors": "Example, Ada", "year": "2026", "full_text_available": "yes", "extraction_card": "yes", "evidence_basis": "full_text"})
    card = root / "discovery/literature/extraction_cards/P001.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    direct = "| p. 4 | The study documents take-up barriers. | supports a bounded descriptive statement |" if complete else "| TBD | TBD | TBD |"
    card.write_text("\n".join([
        "# P001", "## Full Text Status", "full_text_obtained", "## Extraction Depth", "full_text_extraction",
        "## Content Summary", "The paper studies administrative barriers to benefit take-up.",
        "## What This Paper Can Support", "- A bounded descriptive statement about documented take-up barriers.",
        "## What This Paper Cannot Support", "- A causal claim about every benefit program.",
        "## Direct Evidence Notes", "| Page / section | Supporting passage | Interpretation |", "|---|---|---|", direct,
        "## Opened Source", "https://doi.org/10.1234/example.2026",
    ]) + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    for path in [ROOT / "aeros/runtime/literature_paragraph.py", ROOT / "harness/literature_paragraph_compilation_policy.yml", ROOT / "aeros/cli.py"]:
        if not path.exists():
            failures.append(f"missing {path}")
    with tempfile.TemporaryDirectory(prefix="aeros-literature-paragraph-") as temporary:
        root = Path(temporary)
        _fixture(root, complete=True)
        before = (root / "discovery/literature/paper_registry.csv").read_bytes()
        result = compile_candidate_paragraphs(root, ParagraphCandidateArgs(paper_ids=("P001",), purpose="positioning the take-up literature", target_claim="Prior work documents administrative barriers to take-up."))
        if result.get("status") != "CANDIDATE_COMPILED":
            failures.append(f"eligible extraction card did not compile: {result}")
        writes = result.get("writes") or []
        if len(writes) != 2 or not all(str(path).startswith("work/literature_candidate_paragraphs/") for path in writes):
            failures.append(f"candidate outputs escaped the work-only surface: {writes}")
        if (root / "discovery/literature/paper_registry.csv").read_bytes() != before:
            failures.append("candidate compiler must not mutate paper_registry")
        packet = root / writes[0] if writes else None
        if packet is None or not packet.exists() or "\\cite{example2026}" not in packet.read_text(encoding="utf-8"):
            failures.append("candidate packet lacks a source-bound citation key")

        incomplete = Path(tempfile.mkdtemp(prefix="aeros-literature-paragraph-incomplete-"))
        try:
            _fixture(incomplete, complete=False)
            refused = compile_candidate_paragraphs(incomplete, ParagraphCandidateArgs(paper_ids=("P001",), purpose="positioning", target_claim="A bounded claim."))
            if refused.get("status") != "REFUSED" or "P001" not in (refused.get("failures") or {}):
                failures.append("incomplete direct-evidence card was not refused")
        finally:
            import shutil
            shutil.rmtree(incomplete, ignore_errors=True)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: source-bound candidate paragraph compilation preserves extraction and manuscript-promotion boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
