---
schema_version: 1
status: filled
required_sections:
  - ## Literature Functions to Search
  - ## Closest-Literature Standard
---
# Literature Scope

Use this file before literature search to define what counts as relevant, adjacent, or out of scope.

The goal is to prevent the literature search from becoming either too narrow to find useful angles or too broad to support a real gap claim.

## Starting Idea

How do government regulatory and policy actions toward cultivated (cell-cultured) meat — regulatory approvals, state-level bans, labeling rules, and public funding — affect industry outcomes such as firm entry, investment, R&D activity, and commercialization across jurisdictions?

## Core Research Domain

Field or subfield:

Agricultural and food economics; regulatory and innovation economics; alternative-protein / cellular-agriculture policy.

Primary phenomenon, policy, market, institution, or behavior:

Government regulation of cultivated meat (also called cultured meat, cell-based meat, lab-grown meat, cell-cultivated meat) and the response of firms, investors, and markets to that regulation across jurisdictions (US federal and state, Singapore, EU, Israel, and others).

## Literature Functions to Search

Classify candidate literature into these functions:

| Function | Search target | Reading depth | Can support gap claim? |
| --- | --- | --- | --- |
| idea-inspiring | Papers that suggest angles, variables, mechanisms, or designs | skim or targeted | no |
| gap-verification | Closest papers that could make the idea redundant | full text and extraction card | yes |
| method-identification | Papers that teach identification or estimation design | targeted or full text | method claims only |
| data-measurement | Papers that define variables, measurement protocols, validation, or data limitations | targeted or full text | data and measurement claims only |
| background-institutional | Policy, institutional, legal, historical, or market background | targeted | background only |
| theory-mechanism | Theory or conceptual mechanism papers | targeted or full text | mechanism claims only |

## Core Search Terms

| Concept | Keywords | Synonyms / adjacent terms | Exclusions |
| --- | --- | --- | --- |
| Main topic | cultivated meat regulation | cultured meat, cell-based meat, lab-grown meat, cell-cultivated meat, cellular agriculture | plant-based meat (unless comparative) |
| Population / market / institution | alternative-protein firms, food regulators | FDA, USDA-FSIS, EFSA, Singapore Food Agency, state legislatures, startups, investors | generic biotech firms unrelated to food |
| Outcome | firm investment, market entry | venture funding, R&D, commercialization, product launch, firm survival, consumer acceptance | tissue-engineering yield, cell-line biology |
| Treatment / exposure / shock | regulatory approval, state ban | labeling regulation, government funding, novel-food authorization, moratorium | non-regulatory market shocks |
| Mechanism | regulatory uncertainty | market signaling, legitimacy, first-mover advantage, compliance cost | — |
| Method | event study, difference-in-differences | policy timeline, comparative case study, descriptive analysis, synthetic control | bench-science experimental methods |

## Initial Search Sources

Use credible academic or official sources first:

- EconLit / RePEc / IDEAS
- NBER / CEPR / IZA / SSRN
- AEA, journal, and publisher pages
- Google Scholar / Semantic Scholar / OpenAlex
- Official author pages or university working paper pages
- Government, court, regulator, or institutional sources (FDA, USDA-FSIS, EFSA, SFA, state legislative records) for background literature

## Inclusion Criteria

- Empirical, policy-analysis, or applied-economics work on cultivated-meat regulation, alternative-protein policy, or cellular-agriculture markets.
- Comparative or single-jurisdiction regulatory analysis with an economic, market, or firm-behavior angle.
- Methodology papers on event studies, DiD, or policy-timeline construction directly applicable to this setting.
- Measurement papers on alt-protein investment, firm-entry, or regulatory-stringency indicators.

## Exclusion Criteria

- Pure food-science, tissue-engineering, or bioprocess papers with no economic or policy content.
- Plant-based or fermentation-only alternative-protein papers, unless they directly compare to cultivated meat or its regulation.
- Opinion, advocacy, or trade pieces with no analysis, data, or method.

## Closest-Literature Standard

A paper can be treated as closest literature only if:

1. it directly overlaps with the research question, setting, data, outcome, method, or mechanism;
2. it has been opened and registered in `discovery/literature/paper_registry.csv`;
3. its evidence status is clear; and
4. it has an extraction card before being used to support a gap claim.

## Search Boundaries

Time period:

2013 to present (the first cultured-meat proof-of-concept burger was 2013), with emphasis on 2020–2026 (Singapore's 2020 approval, US FDA/USDA approvals in 2023, and US state-level bans in 2024–2025).

Geographic or institutional scope:

Global regulatory comparison, with emphasis on the United States (federal and state), Singapore, the European Union, and Israel.

Methods in scope:

Descriptive policy analysis, event study, difference-in-differences, comparative case study, regulatory-timeline construction, synthetic control.

Methods out of scope:

Laboratory or bench science, life-cycle-assessment-only engineering studies (unless explicitly linked to policy or market outcomes).

## Open Scope Questions

| Question | Why it matters | Next action |
| --- | --- | --- |
| Is there enough cross-jurisdiction regulatory variation plus firm-level outcome data to support a causal design, or is this a descriptive/measurement contribution? | Determines whether the project is a causal event-study or a measurement/descriptive pilot | Probe data availability in D002 data scouting before any causal language |
| Does a usable, comparable measure of regulatory stringency across jurisdictions already exist? | A measurement contribution depends on whether this must be built from scratch | Search data-measurement function papers and official regulatory records |
