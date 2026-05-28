# D002 Data Scouting

## Task ID

D002

## Task Name

Data Scouting

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: no

Recommended work mode: discovery_report_only

## Objective

Identify candidate data sources and evaluate accessibility, unit, coverage, variables, cost, difficulty, limitations, and potential use.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/idea_memo.md`
- `discovery/literature/synthesis/literature_map.md`

## Files to Inspect

- `discovery/idea_memo.md`
- `discovery/literature/synthesis/literature_map.md`
- `discovery/data_inventory.csv`
- `discovery/literature/search_log.md`

## Files Allowed to Modify

- `discovery/data_inventory.csv`
- `discovery/literature/search_log.md`
- `audits/data_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/data_contract.yml`
- `code/`

## Constraints

- Do not download restricted or confidential data.
- Do not treat availability as confirmed unless evidence is recorded.
- Do not write data pipeline code.

## Expected Output

A data inventory with candidate sources, units, coverage, variables, access barriers, measurement limits, and likely research use.

## Checks to Run

- `checks/check_discovery_completeness.py`
- `checks/check_no_raw_data_changes.py`
- `checks/check_agent_run_report.py`

## Done When

- Data inventory is updated.
- Search log records data-source searches.
- Main access barriers are listed.
- Run report is complete.

## Human Approval Required For

- Paid data acquisition
- Restricted data access
- Promoting a source as sufficient for execution
