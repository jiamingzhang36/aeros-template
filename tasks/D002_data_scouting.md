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
- `discovery/source_memo_trace.csv`
- `discovery/literature/synthesis/literature_map.md`

## Files to Inspect

- `discovery/idea_memo.md`
- `discovery/source_memo_trace.csv`
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
- Do not conclude that a project is feasible or infeasible from source existence alone.
- Do not demote a high-priority source-memo data lead to "next step" without at least one concrete access/search probe or a recorded blocker.
- Label each source by evidence maturity: located, access_path_verified, sample_obtained, schema_inspected, variables_verified, linkage_tested, coverage_diagnosed, or blocked.
- Consider relevant data skills before making a feasibility judgment, such as `data-inventory`, `data-quality-checker`, `data-codebook`, `describe-data`, and `data-merge-audit`; record which were used or why they were not applicable.
- If a useful skill cannot be run because data are unavailable, restricted, or not yet sampled, record that as a blocked probe rather than as a final conclusion.
- Record the next concrete probe needed to upgrade the feasibility judgment.
- Map every high-priority source-memo data lead to `discovery/data_inventory.csv` with `access_evidence`, `engineering_status`, and `next_probe`.
- Do not write data pipeline code.

## Expected Output

A data inventory with candidate sources, units, coverage, variables, access barriers, measurement limits, evidence maturity, skills considered/used, next probes, and likely research use.

## Checks to Run

- `checks/check_discovery_completeness.py`
- `checks/check_source_memo_trace.py`
- `checks/check_no_raw_data_changes.py`
- `checks/check_agent_run_report.py`

## Done When

- Data inventory is updated.
- High-priority source-memo data leads are probed, blocked, or explicitly deferred.
- Search log records data-source searches.
- Main access barriers are listed.
- Engineering status and next probe are recorded for each candidate source.
- Skill use or skill non-use rationale is recorded for each candidate source.
- Run report is complete.

## Human Approval Required For

- Paid data acquisition
- Restricted data access
- Promoting a source as sufficient for execution
