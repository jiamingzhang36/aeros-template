# D003 Feasibility Triage

## Task ID

D003

## Task Name

Feasibility Triage

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: yes, for pursue / pause / drop decision

Recommended work mode: discovery_report_only

## Objective

Assess whether the idea should be pursued, revised, paused, or dropped based on literature gap, data availability, measurement quality, identification, and execution cost.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/idea_memo.md`
- `discovery/source_memo_trace.csv`
- `discovery/literature/synthesis/literature_map.md`
- `discovery/data_inventory.csv`
- `discovery/feasibility_matrix.md`

## Files to Inspect

- `discovery/idea_memo.md`
- `discovery/source_memo_trace.csv`
- `discovery/literature/synthesis/literature_map.md`
- `discovery/data_inventory.csv`
- `discovery/feasibility_matrix.md`
- `discovery/feasibility_memo.md`

## Files Allowed to Modify

- `discovery/feasibility_matrix.md`
- `discovery/feasibility_memo.md`
- `audits/discovery_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `evidence/claim_registry.md`

## Constraints

- Be strict and candid.
- Do not promote the project unless data and design feasibility are plausible after documented data-engineering probes.
- Do not treat source existence, a website, or a database name as sufficient evidence of feasibility.
- Do not issue a feasibility boundary if high-priority source-memo leads are still only registered but unprobed, unless the memo marks the decision as `TBD` or `revise`.
- State the evidence grade for data feasibility and identify what additional data engineering could change the decision.
- Do not issue a final feasibility conclusion until relevant data skills and manual probes have either been used, ruled out as inapplicable, or listed as blocked next steps.
- Separate causal feasibility from descriptive or measurement feasibility.
- If data engineering is unresolved, use `TBD` or `revise` rather than a final pursue/pause/drop conclusion.

## Expected Output

A feasibility matrix and memo with a provisional pursue, revise, pause, drop, or TBD recommendation, explicit data-engineering next probes, and skill-assisted probe status.

## Checks to Run

- `checks/check_discovery_completeness.py`
- `checks/check_source_memo_trace.py`
- `checks/check_feasibility_matrix.py`
- `checks/check_agent_run_report.py`

## Done When

- Feasibility dimensions are scored or marked TBD.
- Minimum viable version is stated.
- Decision is pursue, revise, pause, drop, or TBD.
- Decision confidence and remaining data-engineering work are stated.
- Relevant data-skill probes are used, ruled out, or listed as blocked.
- Run report is complete.

## Human Approval Required For

- Treating the feasibility decision as final
- Promoting a causal design before linkage, coverage, and identifying variation have been probed
