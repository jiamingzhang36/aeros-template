# D005 Literature Librarian

## Task ID

D005

## Task Name

Literature Librarian

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: no

Recommended work mode: discovery_report_only

## Objective

Verify candidate citations, find DOI / official pages / working paper pages / PDF links, and update full-text status.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/literature/AGENTS.md`
- `discovery/literature/paper_registry.csv`

## Files to Inspect

- `discovery/literature/paper_registry.csv`
- `discovery/literature/search_log.csv`
- `discovery/literature/citation_audit.md`

## Files Allowed to Modify

- `discovery/literature/paper_registry.csv`
- `discovery/literature/citation_audit.md`
- `discovery/literature/search_log.csv`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`
- `discovery/literature/synthesis/`

## Constraints

- Do not summarize papers.
- Do not fabricate DOI, URL, or citation metadata.
- Do not commit copyrighted PDFs; record official URLs or local private paths instead.
- If full text is unavailable, mark `full_text_unavailable` or `abstract_only`.

## Expected Output

Updated registry and citation audit with verified citation metadata and full-text status.

## Checks to Run

- `checks/check_literature_registry.py`
- `checks/check_literature_functions.py`
- `checks/check_citation_audit.py`
- `checks/check_agent_run_report.py`

## Done When

- Citation audit is updated.
- Full-text availability is explicit.
- Registry statuses are updated.
- Run report is complete.

## Human Approval Required For

- Paid access
- Restricted access
- Uploading or sharing PDFs
