---
task_class: standard
allowed_skills: []
---
# D004 Literature Verification and Extraction

## Task ID

D004

## Task Name

Literature Verification and Extraction

## Renumbering Note

Formerly D005, with the former D006 Literature Extraction responsibilities merged in.

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: no

Recommended work mode: discovery_report_only

## Objective

Verify candidate citations, record stable source locators, update full-text status, and create extraction cards for selected full-text papers.

## Stop Rule

TBD

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/literature/AGENTS.md`
- `discovery/literature/paper_registry.csv`
- `discovery/literature/extraction_cards/TEMPLATE_extraction_card.md`

## Files to Inspect

- `discovery/literature/paper_registry.csv`
- `discovery/literature/search_log.csv`
- `discovery/literature/citation_audit.md`
- full-text paper files or official full-text URLs

## Files Allowed to Modify

- `discovery/literature/paper_registry.csv`
- `discovery/literature/citation_audit.md`
- `discovery/literature/search_log.csv`
- `discovery/literature/extraction_cards/`
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
- DOI is not required for sources that legitimately lack one, but DOI must be recorded when it exists.
- Every full-text-obtained, extracted, included, or synthesis-eligible paper must have at least one stable locator: DOI, official/publisher URL, working-paper page, database record, or private local PDF path.
- Do not commit copyrighted PDFs; record official URLs or local private paths instead.
- If full text is unavailable, mark `full_text_unavailable` or `abstract_only`.
- Extract only from papers with full text obtained.
- Do not use model memory or search snippets.
- If a detail is not stated, write `not stated`.
- Include page, section, table, or figure references when possible.
- Do not infer identification strategy unless explicitly described.
- For every extracted or included paper, write a concise content summary covering the question, setting, data, method, main result, and project relevance.
- Mark `screening_decision=include` only when the extraction card explains why the paper belongs in the evidence base.

## Expected Output

Updated registry and citation audit, plus extraction cards for selected full-text papers.

## Checks to Run

- `checks/check_literature_registry.py`
- `checks/check_literature_functions.py`
- `checks/check_extraction_cards.py`
- `checks/check_citation_audit.py`
- `checks/check_agent_run_report.py`

## Done When

- Citation audit is updated.
- DOI status is explicit: verified DOI, no DOI found, or not yet verified.
- Stable source locator is recorded for every paper promoted beyond search/screening.
- Full-text availability is explicit.
- Extraction cards exist for extracted papers.
- Registry statuses are updated.
- Run report is complete.

## Human Approval Required For

- Paid access
- Restricted access
- Uploading or sharing PDFs
- Treating abstract-only papers as sufficient evidence
