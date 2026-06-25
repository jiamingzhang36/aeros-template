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

## Economics Discovery Adapter Boundaries

OpenAlex, CitEc/RePEc, pyBiblioNet, and PreprintResolver are allowed as economics literature discovery adapters, not as evidence certifiers.

- OpenAlex may generate metadata, author/source disambiguation, and citation-neighborhood candidates.
- CitEc/RePEc may generate economics-specific citation graph candidates.
- pyBiblioNet may help explore OpenAlex-based bibliometric networks.
- PreprintResolver may propose working-paper/preprint to published-version matches, but identity resolution must be reviewed before overwriting registry identity or final bibliography entries.
- Adapter outputs must be logged as discovery artifacts such as `search_log.csv`, `citation_graph_edges.csv`, `citation_audit.md`, or `preprint_resolution_log.csv`.
- Adapter outputs cannot support gap claims, method claims, findings claims, or paper literature positioning until full-text extraction cards exist.


## Citation Faithfulness Rules

Citation checking has three separate questions:

- `Citation exists`: the cited work or stable bibliographic record exists.
- `Metadata faithful`: title/authors/year/DOI/venue match the cited work closely enough for the current purpose.
- `Claim support checked`: the cited work has been checked against the sentence or claim it is supposed to support.

A paper can be real and still fail claim-support alignment. If alignment is uncertain, mark `partial` or `not_checked` and escalate to full-text extraction; do not infer support from metadata or title/abstract alone.
