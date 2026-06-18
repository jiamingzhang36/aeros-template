# Literature Review Hard Rules

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
14. DOI is optional, but if a DOI exists it must be recorded.
15. Before a paper can be treated as full-text obtained, extracted, included, or used in synthesis, it must have at least one stable source locator in `paper_registry.csv`: DOI, official/publisher URL, working-paper page, database record, or private local PDF path.
16. Mark `screening_decision=include` only after the source has an extraction card with a content summary, inclusion reason, direct evidence notes, and opened source.
17. Use `maybe` for unverified candidates, `exclude` for checked non-evidence, and `defer` for plausible but out-of-scope or lower-priority sources.

18. Source-bound or metadata-only cards are bookkeeping artifacts. They may repair registry/card consistency but may not support synthesis, gap claims, paper literature positioning, or claim registry entries.
19. A card supports substantive synthesis only when `Full Text Status` includes `full_text_obtained`, `Extraction Depth` is `full_text_extraction`, registry `evidence_basis` is `full_text` or `extraction_card`, and Direct Evidence Notes contain at least one page/section-bound non-placeholder row.
20. Every function-specific synthesis must cite only verified full-text extraction cards and must state what each cited paper can and cannot support.
21. Dashboard backlog repair is not literature review completion. Report it as bookkeeping or guardrail repair unless LIT-FULL/LIT-SYNTH/LIT-PAPER artifacts were produced.
