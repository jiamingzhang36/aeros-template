#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.artifact_semantics import compile_legacy_output_intent, parse_artifact_semantics

def main() -> int:
    failures = []
    expected = {
        "lead_queue": ("lead", "raw", "nonproduction"),
        "staging_artifact": ("accepted", "staging", "nonproduction"),
        "canonical_update": ("accepted", "processed", "canonical"),
    }
    for legacy, wanted in expected.items():
        got = compile_legacy_output_intent(legacy)
        if (got.selection_status, got.processing_stage, got.admission_status) != wanted:
            failures.append(f"legacy projection mismatch for {legacy}")
    try:
        parse_artifact_semantics({"selection_status":"rejected","processing_stage":"processed","admission_status":"canonical"})
        failures.append("rejected canonical artifact was accepted")
    except ValueError:
        pass
    if failures:
        print("FAIL: artifact semantics"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: orthogonal artifact semantics and legacy output-intent projection are valid"); return 0
if __name__ == "__main__": raise SystemExit(main())

