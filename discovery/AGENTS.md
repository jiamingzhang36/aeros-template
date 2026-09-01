# Discovery Agent Rules

## Role

You are working in the discovery harness. Your job is to test whether an idea deserves a full execution harness.

Shared universal rules are in [harness/common_rules.md](harness/common_rules.md).

Discovery-specific requirements follow the same governance baseline in the root file and should be applied together.

Before adding a discovery workflow, registry, search policy, or new review surface, apply the root `NODIUJ` Scope and Complexity Gate. Prefer a bounded lead, route decision, or existing evidence path over a new discovery layer.

Use `aeros adopt` as the default intake path for new ideas, source memos, or partially completed projects. Adoption outputs are advisory drafts and inventories; they do not approve gates, certify claims, or replace source-grounded discovery work.

## Exploration Policy

Be creative in exploration and strict in verification.

You may propose new angles, adjacent literatures, possible data sources, mechanisms, and alternative designs. Label them clearly and record them in `discovery/idea_bank.csv` when they may be worth revisiting.

Do not promote exploratory ideas to formal conclusions unless they pass the relevant verification gate.

## Literature Function Rules

Separate literature by function:

- `idea-inspiring`
- `gap-verification`
- `method-identification`
- `data-measurement`
- `background-institutional`
- `theory-mechanism`

Do not treat inspiration papers as closest literature unless they are reclassified and verified.

## Source-Grounded Rules

- Do not summarize findings unless the paper has been opened and read.
- If only the abstract is available, mark `abstract_only`.
- Every gap claim must cite at least one `gap-verification` extraction card.
- Every data feasibility claim must cite a real data source.
- Do not propose a causal design unless data contain plausible identifying variation and the data engineering path has been probed.
- Always distinguish feasible now, feasible with paid/protected data, and interesting but currently infeasible.
- Treat early data-source findings as provisional. Record what has been verified, what has only been located, what data engineering remains, and what next probe would change the judgment.
- Final recommendation must be `pursue`, `revise`, `pause`, `drop`, or `TBD`.

## Stage Rule

Before promotion, keep treatment, exposure, sample, outcome, model, and claim language provisional.

If discovery starts from an adopted memo or existing folder, keep adoption-derived claims in adoption drafts until they are verified through literature extraction cards, data feasibility evidence, receipts, or task checks.

## Critic Rule

The discovery critic should not suppress creativity. The critic should identify which ideas are speculative, under verification, supported, revised, parked, dropped, or promoted to design.
