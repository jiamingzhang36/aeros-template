# T002 Data Feasibility

## Objective

Evaluate whether candidate data sources can support the proposed unit, sample, treatment / exposure / key variables, outcomes, and design.

## Harness Mode

Worker required: yes

Critic required: yes, if data feasibility affects project status

Human gate required: yes, if recommending pursue, pause, or drop

## Files to Inspect

- `discovery/data_inventory.csv`
- `discovery/feasibility_memo.md`
- `docs/data_contract.yml`
- `docs/protected_definitions.yml`

## Files Allowed to Modify

- `discovery/data_inventory.csv`
- `discovery/feasibility_memo.md`
- `audits/data_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`

## Constraints

- Do not download restricted or confidential data into the repository.
- Do not modify `data/raw/`.
- Do not mark data as feasible without source evidence.
- Do not mark data as execution-ready until access, schema, key variables, coverage, linkage keys, and minimum viable construction have been probed or explicitly scoped out.
- Separate linked descriptive pilot feasibility from national causal design feasibility.
- Use or explicitly consider relevant data skills before recommending pursue, pause, or drop. If a skill is blocked, record the blocking condition and the next probe needed.

## Expected Output

A data audit report with:

- available sources
- unavailable or restricted sources
- key variables
- evidence maturity and data-engineering status
- skills considered, skills used, and blocked skill probes
- measurement gaps
- unresolved linkage, coverage, access, and construction probes
- minimum viable empirical test
- decision: pursue, revise, pause, drop, or TBD

## Checks to Run

- `checks/check_no_raw_data_changes.py`
- `checks/check_agent_run_report.py`

## Done When

- Data audit report is written.
- Feasibility decision is explicit.
- Run report is complete.
