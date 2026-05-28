# T007 Replication Package

## Task ID

T007

## Task Name

Replication Package

## Harness Mode

Worker required: yes

Critic required: yes

Human gate required: yes, if data access, sharing, or publication files change

Recommended work mode: branch_or_isolated_worktree

## Objective

Check whether the project has enough structure to prepare a replication package.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `README_replication.md`
- `docs/data_contract.yml`
- `docs/data_sources.md`
- `evidence/result_index.csv`
- `harness/permissions.yml`

## Files to Inspect

- `README_replication.md`
- `Makefile`
- `environment.yml`
- `requirements.txt`
- `code/`
- `data/README_data.md`
- `evidence/result_index.csv`
- `paper/`

## Files Allowed to Modify

- `audits/replication_package_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `paper/`

## Constraints

- Do not expose restricted data.
- Do not edit publication-facing files unless explicitly allowed.
- Report missing replication materials instead of fabricating them.

## Expected Output

A replication package report covering data access, environment, scripts, outputs, paper links, and unresolved blockers.

## Checks to Run

- `checks/check_replication_package.py`
- `checks/check_pipeline_runs.py`
- `checks/check_output_reproducibility.py`
- `checks/check_protected_definitions.py`
- `checks/check_agent_run_report.py`

## Done When

- Replication package report exists.
- Missing replication materials are listed.
- Required checks pass or failures are documented.
- Critic review is complete.

## Human Approval Required For

- Any data-sharing decision
- Any public release
- Any change to protected definitions or publication-facing files
