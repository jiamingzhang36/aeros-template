#!/usr/bin/env python3
"""Adversarial fixture: mutate an artifact after a hash-bound approval."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root)
    artifact = root / "paper" / "draft.md"
    approval = root / "decisions" / "approvals" / "G7_claim_audit.artifact.yml"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    approval.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("# Draft\n\nApproved claim wording.\n", encoding="utf-8")
    original_sha = _sha256(artifact)
    approval.write_text(
        f"""artifact_path: paper/draft.md
artifact_sha256: {original_sha}
approved_by: jiaming
approved_at: "2026-06-23T00:00:00+08:00"
decision_ref: decisions/approvals/G7.md
notes: "Adversarial fixture approval bound to the pre-mutation draft."
""",
        encoding="utf-8",
    )
    artifact.write_text("# Draft\n\nChanged after approval.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
