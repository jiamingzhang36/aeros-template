# T002 Data Feasibility

## Objective

Evaluate whether candidate data sources can support the proposed unit, sample, treatment / exposure / key variables, outcomes, and design.

## Harness Mode

Worker required: yes

Critic required: yes, if data feasibility affects project status

Human gate required: yes, if recommending pursue, pause, or drop

## Files to Inspect

- `docs/discovery/04_data_inventory.csv`
- `docs/discovery/09_feasibility_memo.md`
- `docs/data_contract.yml`
- `docs/protected_definitions.yml`

## Files Allowed to Modify

- `docs/discovery/04_data_inventory.csv`
- `docs/discovery/09_feasibility_memo.md`
- `audits/data_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`

## Constraints

- Do not download restricted or confidential data into the repository.
- Do not modify `data/raw/`.
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

- `checks/check_no_raw_data_changes.py`
- `checks/check_agent_run_report.py`

## Done When

- Data audit report is written.
- Feasibility decision is explicit.
- Run report is complete.
