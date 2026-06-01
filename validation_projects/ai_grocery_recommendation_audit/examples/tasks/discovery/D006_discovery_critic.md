---
task_class: standard
allowed_skills: []
---
# D006 Discovery Critic

## Task ID

D006

## Task Name

Discovery Critic

## Renumbering Note

Formerly D008 before discovery task consolidation.

## Harness Mode

Worker required: yes

Critic required: no

Human gate required: yes, if recommending promote / revise / park / drop

Recommended work mode: read_only_or_report_only

## Objective

Review whether exploratory ideas, literature claims, data feasibility claims, and design options are properly labeled and grounded.

## Stop Rule

TBD

- `AGENTS.md`
- `discovery/AGENTS.md`
- `discovery/exploration_policy.md`
- `discovery/idea_bank.csv`
- `discovery/literature/paper_registry.csv`
- `discovery/literature/citation_audit.md`
- `discovery/literature/extraction_cards/`
- `discovery/data_inventory.csv`
- `discovery/feasibility_matrix.md`
- `discovery/design_options.md`
- `discovery/PROMOTE_TO_HARNESS.md`

## Files to Inspect

- `discovery/`
- `audits/discovery_audit_report.md`

## Files Allowed to Modify

- `audits/discovery_critic_report.md`
- `agent_runs/`

## Files Forbidden to Modify

- `data/raw/`
- `docs/protected_definitions.yml`
- `docs/method_card.md`
- `evidence/claim_registry.md`
- `code/`
- `paper/`

## Constraints

- Do not suppress creative exploration.
- Do not promote speculative ideas without evidence.
- Check whether speculative ideas are clearly labeled.
- Check whether gap claims rely on extracted gap-verification papers.
- Check whether data feasibility claims rely on real data sources.
- Check whether high-priority intake leads were actually mapped and, for data leads, probed rather than merely registered.
- Check whether causal design claims document plausible identifying variation.

## Expected Output

A discovery critic report classifying major ideas or design options as promote, revise, park, or drop.

## Checks to Run

- `checks/check_idea_bank.py`
- `checks/check_literature_registry.py`
- `checks/check_gap_grounding.py`
- `checks/check_feasibility_matrix.py`
- `checks/check_agent_run_report.py`

## Done When

- Discovery critic report exists.
- Speculative claims are flagged.
- Promotion blockers are listed.
- Registered-but-unprobed high-priority intake leads are listed.
- Human decisions needed are listed.

## Human Approval Required For

- Promoting ideas to design
- Moving from discovery to execution
