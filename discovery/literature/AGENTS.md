# Literature Review Rules

## Role

You are working inside the source-grounded literature review harness.

Core evidence and governance rules are in:
- [AGENTS.md](../../AGENTS.md)
- [discovery/AGENTS.md](../AGENTS.md)
- [harness/common_rules.md](../../harness/common_rules.md)

Before adding a literature queue, extraction schema, retrieval policy, or citation check, apply the root `NODIUJ` Scope and Complexity Gate. Reuse the current registry, extraction-card, and risk-tier mechanisms unless the new surface addresses an observed gap.

## Hard Rules

Apply the full source-grounded rules in [discovery/literature/literature_rules.md](literature_rules.md), and keep them aligned with the shared governance rules above.

Literature items surfaced by `aeros adopt` or AI-assisted synthesis are leads only. They must enter the registry, obtain the appropriate status, and receive extraction cards before they can support synthesis or gap claims.

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
