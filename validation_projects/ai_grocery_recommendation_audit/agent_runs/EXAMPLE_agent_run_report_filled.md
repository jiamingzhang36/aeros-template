# Agent Run Report (Example)

## Run Metadata

- Run ID: EXAMPLE-001
- Date: 2026-05-28
- Task ID: D001
- Task: D001_literature_search.md
- Executor: template_author
- Mode: discovery
- Human decision points: none

## Files Read

- `AGENTS.md`
- `README.md`
- `discovery/AGENTS.md`
- `tasks/discovery/D001_literature_search.md`
- `discovery/01_literature_scope.md`
- `discovery/literature/search_log.md`
- `discovery/literature/paper_registry.csv`

## Files Modified

- `discovery/literature/search_log.csv`
- `discovery/literature/paper_registry.csv`
- `agent_runs/EXAMPLE_agent_run_report_filled.md`

## Skills Used

- none

## Commands Run

- `python3 checks/check_discovery_completeness.py`
- `python3 checks/check_literature_registry.py`
- `python3 checks/check_agent_run_report.py`

## Outputs Produced

- Added three literature entries with source links in `search_log.csv`.
- Annotated relevance and status for each candidate.

## Checks

- `checks/check_discovery_completeness.py`: PASS
- `checks/check_literature_registry.py`: PASS
- `checks/check_agent_run_report.py`: PASS

## Decision

Discovery task complete. Search leads are exploratory and do not claim a literature gap yet.

## Open Questions

- Which candidate paper has the highest evidence density for closest-literature status?
