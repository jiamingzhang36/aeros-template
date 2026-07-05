---
task_class: standard
allowed_skills: []
---
# D001 Literature Search

## Task ID

D001

## Task Name

Literature Search

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: no

Recommended work mode: discovery_report_only

## Objective

Find real candidate academic literature and register search results without writing synthesis.

## Stop Rule

TBD

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/idea_memo.md`
- `discovery/01_literature_scope.md`
- `discovery/literature/AGENTS.md`
- `discovery/literature/function_taxonomy.md`
- `discovery/literature/search_protocol.md`
- `discovery/literature/search_log.md`

## Files to Inspect

- `discovery/idea_memo.md`
- `discovery/01_literature_scope.md`
- `discovery/literature/search_protocol.md`
- `discovery/literature/search_log.md`
- `discovery/literature/paper_registry.csv`

## Files Allowed to Modify

- `discovery/literature/paper_registry.csv`
- `discovery/literature/search_log.md`
- `discovery/literature/search_log.csv`
- `audits/discovery_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`

## Constraints

- Do not summarize papers.
- Do not claim a literature gap.
- Do not infer methods, data, or findings from titles or snippets.
- Do not create final research claims.
- Do not write analysis code.

## Expected Output

Updated search log and paper registry with discovered candidate papers, source links, DOI or URL when available, and initial relevance notes.

## Checks to Run

- `checks/check_discovery_completeness.py`
- `checks/check_literature_registry.py`
- `checks/check_literature_functions.py`
- `checks/check_agent_run_report.py`

## Done When

- Paper registry has candidate entries or search failures are documented.
- Search log is updated.
- Run report is complete.

## Human Approval Required For

- Promoting the idea to execution harness
