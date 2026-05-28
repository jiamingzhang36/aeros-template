# Exploration Policy

Discovery should be flexible, verification should be strict, and claims should be conservative.

Agents may propose speculative ideas, adjacent literatures, alternative data sources, mechanisms, and possible empirical designs during discovery. These exploratory outputs are valuable, but they are not evidence.

## Exploration Labels

Every exploratory output should be labeled as one of:

- speculative idea
- possible literature strand
- possible data source
- possible mechanism
- possible design
- verified evidence

## Promotion Requirements

- A literature claim requires at least one extraction card.
- A data feasibility claim requires an entry in `discovery/data_inventory.csv`.
- A gap claim requires closest-literature comparison and extracted `gap-verification` papers.
- A causal design claim requires documented identifying variation.
- A policy implication requires evidence and human approval.

## Zones

### Exploratory Zone

Allowed: brainstorming, adjacent literature, possible data, mechanisms, alternative designs.

Required label: speculative / possible / needs verification.

### Verification Zone

Allowed: source search, citation verification, full-text extraction, data-source verification, feasibility scoring.

Required evidence: registry entries, extraction cards, data inventory entries, matrices, or audit notes.

### Commitment Zone

Allowed: feasibility memo, design options, promotion gate, method card, protected definitions, claim registry.

Required evidence: verified literature, real data sources, documented design assumptions, and human approval when needed.

## Red / Yellow / Green Lines

Red lines:

- invent citations
- invent DOI or data access
- summarize unread papers as evidence
- declare unavailable data feasible
- package speculative ideas as conclusions
- make final go / no-go decisions without human approval

Yellow lines:

- possible gap
- possible data source
- possible mechanism
- possible design
- possible contribution

Green lines:

- expand keywords
- identify adjacent literature
- propose alternative framing
- record search queries
- populate registries
- generate clearly labeled idea candidates
