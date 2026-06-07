#!/usr/bin/env python3
"""Check that replication-package scaffolding exists."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_PATHS = [
    Path("README_replication.md"),
    Path("project_manifest.yml"),
    Path("Makefile"),
    Path("requirements.txt"),
    Path("environment.yml"),
    Path("data/README_data.md"),
    Path("code/99_make_all.py"),
    Path("evidence/result_index.csv"),
]

# The manuscript may be a Markdown draft (paper/draft.md or any paper/*.md) OR a
# LaTeX source under tex/ — projects that write directly in LaTeX should not be
# forced to also keep a paper/draft.md. Accept any of these.
MANUSCRIPT_GLOBS = [("paper", "draft.md"), ("paper", "*.md"), ("tex", "*.tex")]


def _manuscript_present() -> bool:
    for base, pattern in MANUSCRIPT_GLOBS:
        b = Path(base)
        if b.exists() and any(b.glob(pattern)):
            return True
    return False


def main() -> int:
    missing = [str(path) for path in REQUIRED_PATHS if not path.exists()]
    if not _manuscript_present():
        missing.append("a manuscript (paper/draft.md, paper/*.md, or tex/*.tex)")
    if missing:
        print("FAIL: replication package scaffolding is missing:")
        print("\n".join(missing))
        return 1

    print("PASS: replication package scaffolding exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
