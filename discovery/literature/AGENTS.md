# Literature Review Rules

## Role

You are working inside the source-grounded literature review harness.

## Hard Rules

1. Do not summarize a paper unless its status is `full_text_read` or `extracted`.
2. If only the abstract is available, label all statements as abstract-based.
3. Do not infer identification strategy from the title.
4. Do not infer data details unless stated in the paper.
5. Do not cite a paper that is not in `discovery/literature/paper_registry.csv`.
6. Do not include invented citations.
7. Every synthesis claim must link to at least one extraction card.
8. Every claim about method, data, or finding must include `paper_id`.
9. If full text cannot be obtained, mark `full_text_unavailable`.
10. If evidence is ambiguous, write ambiguous, not likely.
11. Every paper must have a `primary_function`.
12. `gap-verification` papers require full text and an extraction card before they can support gap claims.
13. `idea-inspiring` papers cannot be used as closest-literature evidence unless reclassified and extracted.

## Literature Functions

- `idea-inspiring`
- `gap-verification`
- `method-identification`
- `data-measurement`
- `background-institutional`
- `theory-mechanism`

## Status Flow

```text
discovered
-> title_abstract_screened
-> abstract_only OR full_text_obtained
-> full_text_read
-> extracted
-> included OR excluded
```

## Output Rule

Final literature synthesis must be based only on `discovery/literature/extraction_cards/`.
