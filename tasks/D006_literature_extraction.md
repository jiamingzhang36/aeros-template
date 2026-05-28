# D006 Literature Extraction

## Task ID

D006

## Task Name

Literature Extraction

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: no

Recommended work mode: discovery_report_only

## Objective

Create structured extraction cards from full-text papers.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/literature/AGENTS.md`
- `discovery/literature/paper_registry.csv`
- `discovery/literature/extraction_cards/TEMPLATE_extraction_card.md`

## Files to Inspect

- `discovery/literature/paper_registry.csv`
- full-text paper files or official full-text URLs

## Files Allowed to Modify

- `discovery/literature/extraction_cards/`
- `discovery/literature/paper_registry.csv`
- `discovery/literature/citation_audit.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`
- `discovery/literature/synthesis/`

## Constraints

- Extract only from papers with full text obtained.
- Do not use model memory or search snippets.
- If a detail is not stated, write `not stated`.
- Include page, section, table, or figure references when possible.
- Do not infer identification strategy unless explicitly described.

## Expected Output

One extraction card per full-text paper selected for extraction.

## Checks to Run

- `checks/check_literature_registry.py`
- `checks/check_literature_functions.py`
- `checks/check_extraction_cards.py`
- `checks/check_citation_audit.py`
- `checks/check_agent_run_report.py`

## Done When

- Extraction cards exist for extracted papers.
- Registry extraction status is updated.
- Citation audit is updated.
- Run report is complete.

## Human Approval Required For

- Treating abstract-only papers as sufficient evidence
