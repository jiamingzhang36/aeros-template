#!/usr/bin/env python3
"""Check that root, discovery, literature, and execution AGENTS rules exist."""

from __future__ import annotations

import sys
from pathlib import Path


# Stage AGENTS files must exist and be substantive structured guidance. We do
# NOT require exact heading strings — a valid AGENTS.md may organize its rules
# under differently-named sections — only that real, sectioned content is there.
REQUIRED = [
    Path("AGENTS.md"),
    Path("discovery/AGENTS.md"),
    Path("discovery/literature/AGENTS.md"),
    Path("execution/AGENTS.md"),
]
MIN_HEADINGS = 3
MIN_CHARS = 300


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED:
        if not path.exists():
            failures.append(f"missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        headings = [ln for ln in text.splitlines() if ln.strip().startswith("##")]
        if len(headings) < MIN_HEADINGS or len(text.strip()) < MIN_CHARS:
            failures.append(f"{path}: not substantive "
                            f"(needs >= {MIN_HEADINGS} section headings and real content)")

    if failures:
        print("FAIL: stage AGENTS problems detected:")
        print("\n".join(failures))
        return 1

    print("PASS: root, discovery, literature, and execution AGENTS rules exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
