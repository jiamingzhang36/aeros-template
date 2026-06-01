# Claim Registry

## Claim Types

- descriptive
- measurement
- associational
- causal
- mechanism
- external-validity
- policy-translation
- forecast

## Registry

| Claim ID | Claim | Type | Status | Evidence ID(s) | Result ID(s) | Boundary / Limitation | Approved |
|---|---|---|---|---|---|---|---|
| C001 | The execution pipeline can produce a bounded measurement summary for an AI grocery recommendation audit using the selected O1 design. | descriptive | retired |  | R001 | Smoke validation only; retired before claim approval because R002/R003 supersede it for pilot validation. | no |
| C002 | In a small current-Codex-session pilot, the audit pipeline measured affordability, vagueness, and nutrition-flag summaries across low-income SNAP-relevant and moderate-budget personas. | measurement | ambiguous |  | R002;R003 | Pilot outputs from this Codex session only; not evidence about deployed AI systems, all models, or real consumers. Expanded G11 outputs may inform a future human-reviewed update but do not automatically upgrade this claim. | no |

## Status Values

- draft
- supported
- ambiguous
- unsupported
- retired

## Rules

- A claim cannot be marked supported without at least one evidence ID or result ID.
- A causal claim requires a method card that supports causal language.
- A forecast claim requires explicit forecast validation or must remain unsupported.
- Policy translation must stay within the protected sample, geography, period, and outcome definitions.
