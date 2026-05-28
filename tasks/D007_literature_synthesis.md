# D007 Literature Synthesis

## Task ID

D007

## Task Name

Literature Synthesis

## Harness Mode

Worker required: yes

Critic required: yes

Human gate required: yes, if claiming a gap is real

Recommended work mode: discovery_report_only

## Objective

Synthesize the literature using only extraction cards and audited citations.

## Required Reading

- `AGENTS.md`
- `project_manifest.yml`
- `discovery/literature/AGENTS.md`
- `discovery/literature/paper_registry.csv`
- `discovery/literature/citation_audit.md`
- `discovery/literature/extraction_cards/`

## Files to Inspect

- `discovery/literature/extraction_cards/`
- `discovery/literature/paper_registry.csv`
- `discovery/literature/citation_audit.md`

## Files Allowed to Modify

- `discovery/literature/synthesis/`
- `discovery/gap_memo.md`
- `audits/discovery_audit_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`

## Constraints

- Use only papers with extraction cards.
- Every substantive claim must cite `paper_id`.
- Every cited paper must have citation audit coverage and a stable source locator; DOI is preferred when available but not required.
- Every cited paper must have an extraction-card content summary and inclusion decision.
- Do not cite abstract-only papers as full evidence.
- Gap claims require extracted `gap-verification` papers.
- Do not use `idea-inspiring` papers as gap evidence.
- Separate causal, descriptive, measurement, theory, and policy evidence.
- Identify disagreement across papers.

## Expected Output

Source-grounded literature map, method matrix, data matrix, findings matrix, gap memo, and optional literature review draft.

## Checks to Run

- `checks/check_literature_registry.py`
- `checks/check_literature_functions.py --require-complete-matrix`
- `checks/check_extraction_cards.py`
- `checks/check_synthesis_grounding.py`
- `checks/check_citation_audit.py`
- `checks/check_gap_grounding.py`
- `checks/check_agent_run_report.py`

## Done When

- Synthesis files are updated.
- All synthesis claims are grounded in extraction cards.
- Abstract-only papers are not used as full evidence.
- Critic review is complete if a real gap is claimed.

## Human Approval Required For

- Treating the literature gap as established
- Promoting the project to execution harness
