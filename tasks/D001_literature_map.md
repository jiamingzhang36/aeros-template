# D001 Literature Map

## Task ID

D001

## Task Name

Literature Map

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: no

Recommended work mode: discovery_report_only

## Objective

Map the closest literature by research question, data, method, identification, findings, and remaining gaps.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/idea_memo.md`
- `discovery/search_log.md`

## Files to Inspect

- `discovery/idea_memo.md`
- `discovery/search_log.md`
- `discovery/paper_registry.csv`
- `discovery/closest_literature_matrix.csv`

## Files Allowed to Modify

- `discovery/literature_map.md`
- `discovery/paper_registry.csv`
- `discovery/closest_literature_matrix.csv`
- `discovery/search_log.md`
- `audits/discovery_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`

## Constraints

- Do not claim a literature gap until closest papers are inspected.
- Do not create final research claims.
- Do not write analysis code.

## Expected Output

A literature map that distinguishes research strands, closest papers, data used, methods, findings, and plausible gaps.

## Checks to Run

- `checks/check_discovery_completeness.py`
- `checks/check_agent_run_report.py`

## Done When

- Literature map exists.
- Paper registry has candidate entries or search failures are documented.
- Search log is updated.
- Run report is complete.

## Human Approval Required For

- Promoting the idea to execution harness
