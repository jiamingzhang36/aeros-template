"""Local hash-chain support for AEROS update ledgers.

The chain is intentionally simple and local: each JSONL record hashes its
canonical payload plus the previous record hash. It detects accidental or
silent local drift in ledger-tracking artifacts. It is not a transparency log,
signature system, or protection against a malicious actor who can rewrite both
the ledger and the chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from typing import Any


GENESIS = "GENESIS"


@dataclass(frozen=True)
class ChainValidation:
    ok: bool
    failures: tuple[str, ...]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_record_hash(record: dict) -> str:
    payload = {key: value for key, value in record.items() if key != "entry_hash"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_text(encoded)


def load_chain_records(chain_path: Path) -> list[dict[str, Any]]:
    """Load hash-chain records from JSONL.

    This helper is intentionally small so all writers use the same schema.
    """
    if not chain_path.exists():
        return []
    records: list[dict[str, Any]] = []
    for raw in chain_path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            records.append(json.loads(raw))
    return records


def append_chain_record(
    *,
    root: Path,
    chain_path: Path,
    subject: str,
    entry_id: str,
    commit_refs: list[str],
    scope: list[str],
    does_not_prove: list[str],
    verification_strength: str = "local_hash_chain_over_observed_subject_file",
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one canonical v1 record.

    Committed ledger-chain mistakes should be corrected by appending a new
    correction record with this writer, not by rewriting a prior record.
    """
    records = load_chain_records(chain_path)
    prev_hash = records[-1].get("entry_hash") if records else GENESIS
    payload: dict[str, Any] = {
        "commit_refs": list(commit_refs),
        "scope": list(scope),
        "verification_strength": verification_strength,
        "does_not_prove": list(does_not_prove),
    }
    if extra_payload:
        payload.update(extra_payload)
    record: dict[str, Any] = {
        "version": 1,
        "seq": len(records) + 1,
        "entry_id": entry_id,
        "subject": subject,
        "subject_sha256": sha256_file(root / subject),
        "prev_hash": prev_hash,
        "payload": payload,
    }
    record["entry_hash"] = canonical_record_hash(record)
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    with chain_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return record


def validate_chain(root: Path, chain_path: Path) -> ChainValidation:
    failures: list[str] = []
    if not chain_path.exists():
        return ChainValidation(False, (f"missing chain file: {chain_path}",))
    records: list[dict] = []
    for lineno, raw in enumerate(chain_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            failures.append(f"line {lineno}: invalid JSON: {exc}")
            continue
        if not isinstance(record, dict):
            failures.append(f"line {lineno}: expected JSON object")
            continue
        records.append(record)
    if not records:
        failures.append("chain has no records")
        return ChainValidation(False, tuple(failures))

    previous = GENESIS
    seen_seq: set[int] = set()
    seen_entry_ids: set[str] = set()
    latest_subject_hash: dict[str, str] = {}
    for index, record in enumerate(records, start=1):
        seq = record.get("seq")
        if not isinstance(seq, int) or seq <= 0:
            failures.append(f"record {index}: seq must be a positive integer")
        elif seq in seen_seq:
            failures.append(f"record {index}: duplicate seq {seq}")
        else:
            seen_seq.add(seq)
        if record.get("prev_hash") != previous:
            failures.append(f"record {index}: prev_hash does not match prior entry")
        expected_hash = canonical_record_hash(record)
        if record.get("entry_hash") != expected_hash:
            failures.append(f"record {index}: entry_hash mismatch")
        entry_id = str(record.get("entry_id") or "")
        if not entry_id:
            failures.append(f"record {index}: missing entry_id")
        elif entry_id in seen_entry_ids:
            failures.append(f"record {index}: duplicate entry_id {entry_id}")
        else:
            seen_entry_ids.add(entry_id)
        subject = record.get("subject")
        subject_sha256 = record.get("subject_sha256")
        if isinstance(subject, str) and subject:
            subject_path = root / subject
            if not subject_path.is_file():
                failures.append(f"record {index}: subject missing: {subject}")
            latest_subject_hash[subject] = str(subject_sha256 or "")
        else:
            failures.append(f"record {index}: missing subject")
        previous = str(record.get("entry_hash") or expected_hash)
    for subject, expected_sha256 in latest_subject_hash.items():
        subject_path = root / subject
        if subject_path.is_file() and expected_sha256 != sha256_file(subject_path):
            failures.append(f"latest subject_sha256 mismatch for {subject}")
    return ChainValidation(not failures, tuple(failures))
