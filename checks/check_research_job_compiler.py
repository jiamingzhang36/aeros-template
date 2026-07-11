#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeros.runtime.research_job import ResearchJob, compile_research_job, validate_compilation

def main() -> int:
    compiled = compile_research_job(ResearchJob("PROBE-C1-ACS","data_probe","C1","census_acs_2024","verify bounded feasibility"))
    failures = validate_compilation(compiled)
    if compiled.action_spec.kind != "data_probe" or compiled.execution_envelope.runtime_profile != "isolated-local-probe": failures.append("data_probe vertical slice compiled incorrectly")
    if failures:
        print("FAIL: ResearchJob compiler"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: data_probe ResearchJob compiles with monotonically narrowing authority"); return 0
if __name__ == "__main__": raise SystemExit(main())

