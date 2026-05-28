# D004 Design Sketch

## Task ID

D004

## Task Name

Research Design Sketch

## Harness Mode

Worker required: yes

Critic required: yes, if recommending promotion

Human gate required: yes

Recommended work mode: discovery_report_only

## Objective

Draft a provisional research design sketch and decide whether the project is ready to promote into the full execution harness.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/idea_memo.md`
- `discovery/literature/synthesis/literature_map.md`
- `discovery/data_inventory.csv`
- `discovery/feasibility_matrix.md`
- `discovery/feasibility_memo.md`

## Files to Inspect

- `discovery/`
- `docs/gate_lifecycle.md`

## Files Allowed to Modify

- `discovery/design_sketch.md`
- `discovery/PROMOTE_TO_HARNESS.md`
- `audits/discovery_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`
- `code/`

## Constraints

- Keep definitions provisional.
- Do not create final protected definitions.
- Do not create final claims.
- If promotion is recommended, list exactly what must be created in the execution harness.

## Expected Output

A design sketch and promotion gate decision: promote, revise discovery, pause, drop, or TBD.

## Checks to Run

- `checks/check_discovery_completeness.py`
- `checks/check_feasibility_matrix.py`
- `checks/check_agent_run_report.py`

## Done When

- Design sketch exists.
- Promotion gate decision is explicit.
- Human decisions needed are listed.
- Run report is complete.

## Human Approval Required For

- Promoting to the full execution harness
