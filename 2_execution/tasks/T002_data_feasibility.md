# T002 Data Feasibility

## Objective

Evaluate whether candidate data sources can support the proposed unit, sample, treatment / exposure / key variables, outcomes, and design.

## Harness Mode

Worker required: yes

Critic required: yes, if data feasibility affects project status

Human gate required: yes, if recommending pursue, pause, or drop

## Files to Inspect

- `0_discovery/04_data_inventory.csv`
- `0_discovery/09_feasibility_memo.md`
- `1_design/data_contract.yml`
- `1_design/protected_definitions.yml`

## Files Allowed to Modify

- `0_discovery/04_data_inventory.csv`
- `0_discovery/09_feasibility_memo.md`
- `5_audits/data_audit_report.md`
- `4_agent_runs/`

## Files Forbidden to Modify

- `2_execution/data/raw/`

## Constraints

- Do not download restricted or confidential data into the repository.
- Do not modify `2_execution/data/raw/`.
- Do not mark data as feasible without source evidence.

## Expected Output

A data audit report with:

- available sources
- unavailable or restricted sources
- key variables
- measurement gaps
- minimum viable empirical test
- decision: pursue, revise, pause, or drop

## Checks to Run

- `2_execution/checks/check_no_raw_data_changes.py`
- `2_execution/checks/check_agent_run_report.py`

## Done When

- Data audit report is written.
- Feasibility decision is explicit.
- Run report is complete.
