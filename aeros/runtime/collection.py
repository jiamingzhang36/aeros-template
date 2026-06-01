"""Batch AI-output collection from approved prompt grids."""

from __future__ import annotations

import csv
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from .provider_connector import ProviderError, make_provider, utc_now


REQUIRED_GRID_COLUMNS = {
    "prompt_id",
    "persona",
    "prompt_variant",
    "model",
    "run_index",
}


@dataclass(frozen=True)
class CollectionConfig:
    provider: str = "mock"
    model: str = "mock-research-model"
    max_cost_usd: float = 0.0
    max_retries: int = 1
    timeout_seconds: int = 120
    rate_limit_seconds: float = 0.0


def _load_manifest_config(project_root: Path) -> CollectionConfig:
    manifest_path = project_root / "project_manifest.yml"
    if not manifest_path.exists():
        return CollectionConfig()
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    automation = data.get("automation", {}) if isinstance(data, dict) else {}
    block = automation.get("provider_connector", {}) if isinstance(automation, dict) else {}
    if not isinstance(block, dict):
        block = {}
    return CollectionConfig(
        provider=str(block.get("provider", "mock") or "mock"),
        model=str(block.get("model", "mock-research-model") or "mock-research-model"),
        max_cost_usd=float(block.get("max_cost_usd", 0.0) or 0.0),
        max_retries=int(block.get("max_retries", 1) or 1),
        timeout_seconds=int(block.get("timeout_seconds", 120) or 120),
        rate_limit_seconds=float(block.get("rate_limit_seconds", 0.0) or 0.0),
    )


def resolve_config(project_root: Path, **overrides: object) -> CollectionConfig:
    base = _load_manifest_config(project_root)
    values = {
        "provider": base.provider,
        "model": base.model,
        "max_cost_usd": base.max_cost_usd,
        "max_retries": base.max_retries,
        "timeout_seconds": base.timeout_seconds,
        "rate_limit_seconds": base.rate_limit_seconds,
    }
    for key, value in overrides.items():
        if value is not None:
            values[key] = value
    return CollectionConfig(**values)


def _read_grid(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"prompt grid not found: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_GRID_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        rows = [{k: (v or "").strip() for k, v in row.items()} for row in reader]
    prompt_ids = [row.get("prompt_id", "") for row in rows]
    if len(prompt_ids) != len(set(prompt_ids)):
        raise ValueError(f"{path}: prompt_id values must be unique")
    return rows


def _prompt_text(row: dict[str, str]) -> str:
    explicit = row.get("prompt_text", "").strip()
    if explicit:
        return explicit
    persona = row.get("persona", "household")
    variant = row.get("prompt_variant", "baseline")
    return (
        "Create a one-week grocery recommendation for the following synthetic "
        f"persona: {persona}. Prompt variant: {variant}. Return specific, "
        "purchasable grocery items, budget notes, nutrition notes, and feasibility notes. "
        "Do not use private or real household data."
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _write_run_report(path: Path, *, config: CollectionConfig, rows: int, out_path: Path,
                      total_cost: float, dry_run: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "dry-run" if dry_run else "completed"
    path.write_text(
        "# Provider Collection Run Report\n\n"
        f"Status: {mode}\n\n"
        f"- Provider: `{config.provider}`\n"
        f"- Model: `{config.model}`\n"
        f"- Rows planned: {rows}\n"
        f"- Output path: `{out_path}`\n"
        f"- Max cost USD: {config.max_cost_usd:.4f}\n"
        f"- Observed cost USD: {total_cost:.4f}\n"
        f"- Max retries: {config.max_retries}\n"
        f"- Timeout seconds: {config.timeout_seconds}\n"
        f"- Rate limit seconds: {config.rate_limit_seconds}\n\n"
        "Boundary: collection records are research observations only. They do not approve "
        "claim upgrades, paper language, or public release.\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_collection_provenance(project_root: Path, *, grid: Path, out: Path,
                                 config: CollectionConfig, rows: int,
                                 total_cost: float) -> Path:
    path = project_root / "outputs" / ".provenance" / "provider_collection.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact": out.relative_to(project_root).as_posix() if out.is_relative_to(project_root) else str(out),
        "output_path": out.relative_to(project_root).as_posix() if out.is_relative_to(project_root) else str(out),
        "created_at": utc_now(),
        "script_or_source": "aeros collect",
        "sha256": _sha256_file(out),
        "input_grid": grid.relative_to(project_root).as_posix() if grid.is_relative_to(project_root) else str(grid),
        "provider": config.provider,
        "model": config.model,
        "rows": rows,
        "cost_usd": total_cost,
        "claim_boundary": (
            "provider collection records are research observations only; "
            "they do not approve claim upgrades, paper language, or public release"
        ),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def collect_prompt_grid(
    project_root: Path,
    *,
    grid: Path,
    out: Path,
    report: Path,
    config: CollectionConfig,
    dry_run: bool = False,
    max_rows: int | None = None,
) -> int:
    rows = _read_grid(grid)
    if max_rows is not None:
        rows = rows[:max_rows]
    if dry_run:
        print(f"[collect] provider={config.provider} model={config.model}")
        print(f"[collect] grid={grid} rows={len(rows)}")
        print(f"[collect] out={out}")
        print("[collect] dry-run: no provider calls and no files written")
        return 0

    provider = make_provider(
        config.provider,
        model=config.model,
        timeout_seconds=config.timeout_seconds,
    )
    records: list[dict] = []
    total_cost = 0.0
    for index, row in enumerate(rows, start=1):
        prompt = _prompt_text(row)
        attempts = 0
        last_error = ""
        while attempts <= config.max_retries:
            attempts += 1
            try:
                response = provider.complete(prompt, row)
                break
            except ProviderError as exc:
                last_error = str(exc)
                if attempts > config.max_retries:
                    raise RuntimeError(
                        f"collection failed for {row.get('prompt_id')} after {attempts} attempt(s): "
                        f"{last_error}"
                    ) from exc
                time.sleep(min(2 ** attempts, 10))
        else:
            raise RuntimeError(f"collection failed for {row.get('prompt_id')}: {last_error}")

        total_cost += response.cost_usd
        if config.max_cost_usd > 0 and total_cost > config.max_cost_usd:
            raise RuntimeError(
                f"collection cost cap exceeded: {total_cost:.4f} > {config.max_cost_usd:.4f}"
            )

        output_text = response.output_text.strip()
        record = {
            "prompt_id": row.get("prompt_id", ""),
            "persona": row.get("persona", ""),
            "prompt_variant": row.get("prompt_variant", ""),
            "model": response.model,
            "provider": response.provider,
            "provider_request_id": response.provider_request_id,
            "run_index": int(row.get("run_index", "0") or 0),
            "collected_at": utc_now(),
            "prompt_text": prompt,
            "prompt_sha256": _sha256_text(prompt),
            "output_text": output_text,
            "output_sha256": _sha256_text(output_text),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": response.cost_usd,
            "duration_ms": response.duration_ms,
            "collection_index": index,
        }
        records.append(record)
        print(f"[collect] {index}/{len(rows)} {record['prompt_id']} ok provider={response.provider}")
        if config.rate_limit_seconds > 0 and index < len(rows):
            time.sleep(config.rate_limit_seconds)

    _write_jsonl(out, records)
    _write_run_report(
        report,
        config=config,
        rows=len(rows),
        out_path=out,
        total_cost=total_cost,
        dry_run=False,
    )
    provenance = _write_collection_provenance(
        project_root,
        grid=grid,
        out=out,
        config=config,
        rows=len(rows),
        total_cost=total_cost,
    )
    print(f"[collect] wrote {out}")
    print(f"[collect] wrote {report}")
    print(f"[collect] wrote {provenance}")
    return 0
