#!/usr/bin/env python3
"""Validate optional artifact admissibility edges for claim support."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeros.kernel.artifact_graph import ArtifactType, EdgeUse, EvidenceEdge, compile_claim_admissibility  # noqa: E402

EDGES = Path('evidence/admissibility_edges.csv')
REQUIRED = ['claim_id','source_id','target_id','evidence_type','use','strength']


def main() -> int:
    if not EDGES.exists():
        print('PASS: artifact admissibility graph inactive (no evidence/admissibility_edges.csv yet)')
        return 0
    failures: list[str] = []
    by_claim: dict[str, list[EvidenceEdge]] = {}
    with EDGES.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        for col in REQUIRED:
            if col not in header:
                failures.append(f'admissibility_edges missing required column: {col}')
        for row in reader:
            claim_id = row.get('claim_id','').strip()
            try:
                edge = EvidenceEdge(
                    source_id=row.get('source_id','').strip(),
                    target_id=row.get('target_id','').strip(),
                    evidence_type=ArtifactType(row.get('evidence_type','').strip()),
                    use=EdgeUse(row.get('use','').strip()),
                    strength=float(row.get('strength') or 0.0),
                )
            except Exception as exc:
                failures.append(f"{claim_id or '(missing)'}: invalid edge row ({exc})")
                continue
            by_claim.setdefault(claim_id, []).append(edge)
    for claim_id, edges in by_claim.items():
        result = compile_claim_admissibility(claim_id, edges)
        if not result.admissible:
            for obligation in result.obligations:
                if obligation.severity == 'hard':
                    failures.append(f'{claim_id}: {obligation.reason}')
    if failures:
        print('FAIL: artifact admissibility problems detected:')
        for failure in failures:
            print(f'- {failure}')
        return 1
    print(f'PASS: artifact admissibility graph valid ({len(by_claim)} claim(s))')
    return 0

if __name__ == '__main__':
    sys.exit(main())
