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
        subject = record.get("subject")
        subject_sha256 = record.get("subject_sha256")
        if isinstance(subject, str) and subject:
            subject_path = root / subject
            if not subject_path.is_file():
                failures.append(f"record {index}: subject missing: {subject}")
            elif subject_sha256 != sha256_file(subject_path):
                failures.append(f"record {index}: subject_sha256 mismatch for {subject}")
        else:
            failures.append(f"record {index}: missing subject")
        previous = str(record.get("entry_hash") or expected_hash)
    return ChainValidation(not failures, tuple(failures))

