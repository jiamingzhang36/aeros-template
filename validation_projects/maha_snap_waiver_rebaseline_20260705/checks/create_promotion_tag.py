#!/usr/bin/env python3
"""Create a reproducible git snapshot tag for major stage promotions."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "project_manifest.yml"


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"missing manifest: {MANIFEST_PATH}")
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError("invalid project manifest format")
    return payload


def _current_gate(manifest: dict) -> str:
    return str(manifest.get("gate_lifecycle", {}).get("current_gate", "")).strip()


def _slug(text: str) -> str:
    return "-".join(part for part in text.lower().replace("_", "-").split() if part)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a promotion snapshot tag.")
    parser.add_argument("--from-stage", required=True)
    parser.add_argument("--to-stage", required=True)
    parser.add_argument("--tag", default="")
    parser.add_argument("--message", default="")
    args = parser.parse_args()

    repo_ok = _run(["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"])
    if repo_ok.returncode != 0 or repo_ok.stdout.strip() != "true":
        print("SKIP: repository not initialized; initialize git first for promotion tags.")
        return 0

    manifest = _load_manifest()
    current_gate = _current_gate(manifest)
    if args.from_stage and args.to_stage and current_gate:
        if args.from_stage.lower() not in current_gate.lower():
            print(
                f"WARN: manifest current_gate '{current_gate}' does not match --from-stage '{args.from_stage}'"
            )

    tag = args.tag.strip()
    if not tag:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        tag = f"promotion/{_slug(args.from_stage)}-to-{_slug(args.to_stage)}/{ts}"

    message = args.message.strip() or f"Promotion snapshot: {args.from_stage} -> {args.to_stage}"

    status = _run(["git", "-C", str(ROOT), "tag", "--list", tag])
    if status.returncode == 0 and tag in status.stdout:
        print(f"SKIP: tag already exists: {tag}")
        return 0

    head = _run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])  # noqa: S603
    if head.returncode != 0:
        print("FAIL: cannot resolve HEAD")
        print(head.stderr.strip())
        return 1

    tag_create = _run(
        [
            "git",
            "-C",
            str(ROOT),
            "tag",
            "-a",
            tag,
            "-m",
            message,
            head.stdout.strip(),
        ]
    )

    if tag_create.returncode != 0:
        print("FAIL: failed to create promotion tag")
        print(tag_create.stderr.strip())
        return 1

    print(f"PASS: created promotion tag {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
