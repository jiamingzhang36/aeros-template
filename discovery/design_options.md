---
status: filled
options:
  - id: O1
    name: "Staggered DiD on state ban timing"
    project_type: causal
    identification: "Staggered adoption timing of US state cultivated-meat bans as treatment variation; Callaway-Sant'Anna (2021) group-time ATT estimator (F04, P027) avoids negative-weighting from heterogeneous treatment effects; Goodman-Bacon (2021, P035) decomposition as diagnostic; Borusyak-Jaravel-Spiess (2024, P036) imputation estimator as robustness alternative; doubly-robust covariate-augmented DiD conditions on state beef GDP (D022) and political confounders to address F06 diffusion endogeneity"
    viability_condition: ">=10 US states with non-zero cultivated-meat firm presence or recorded investment in any pre-ban year 2020-2023 verified from D001 editions, AND >=5 states with confirmed ban passage dates in D007 (LegiScan); both conditions checkable once D001 and D007 are downloaded and merged"
    viability_test:
      metric: n_ban_states_with_firm_presence
      op: ">="
      threshold: 5
    max_claim: causal
    threats_addressed: [F06]
    priority: 1
    is_fallback_floor: false
    claim_boundary: "CAN claim: US state bans are associated with within-state declines in firm presence or investment relative to not-yet-treated and clean-control states, conditional on parallel pre-trends. CANNOT claim: national or global investment trends are caused by state bans; bans cause firm bankruptcy or exit (confounded by the 40 percent macro investment-cycle decline in 2024); results generalise beyond cultivated meat or beyond 2020-2025; Singapore or EU regulatory actions are causally identified under this design."

  - id: O2
    name: "Bill-text reuse / model-legislation diffusion as IV"
    project_type: causal
    identification: "Text-reuse analysis of enacted state ban legislation (D007 LegiScan full-text) computing cosine similarity of each bill to the earliest enacted ban (Alabama SB23) or a known ALEC model template; states with high similarity (coordinated-diffusion adopters) have ban timing driven by template availability rather than local economic conditions, providing a continuous instrument for ban adoption timing in a fuzzy-IV DiD; directly addresses F06 by turning the diffusion mechanism from an identification threat into an instrumentable source of variation (P029 Meseguer-Gilardi; P042 Shipan-Volden)"
    viability_condition: "Full text retrievable from D007 LegiScan for >=5 enacted ban states AND Alabama SB23 text is recoverable as the reference corpus; cosine-similarity scores span sufficient range (SD >= 0.1) across enacted bills to serve as a first-stage instrument"
    viability_test:
      metric: bill_text_extractable_states
      op: ">="
      threshold: 5
    max_claim: causal
    threats_addressed: [F06]
    priority: 2
    is_fallback_floor: false
    claim_boundary: "CAN claim: bans in states adopting near-verbatim model-legislation text are plausibly exogenous to local investment conditions; IV DiD identifies a local average treatment effect on complier states (those whose adoption timing was driven by template access). CANNOT claim: text similarity is a fully clean instrument without empirical validation of the exclusion restriction; aggregate ATT without the causal DiD scaffold from O1; identification survives if ALEC network membership is independently correlated with investment confounders."

  - id: O3
    name: "Synthetic control for national regulatory approval events"
    project_type: causal
    identification: "Synthetic control method (F05; Abadie-Gardeazabal 2003, P028; Abadie-Diamond-Hainmueller 2010, P037) using Singapore December 2020 first-ever cultivated-meat market approval (D006) and US FDA/USDA 2022-2023 pre-market consultation completions (D003) as treatment events; donor pool of non-approving countries constructed from GFI D001 annual investment series and WDI controls (D021); F06 addressed because national-level approval timing is driven by domestic science-regulatory processes rather than cross-jurisdiction legislative diffusion networks; placebo inference via permutation over donor pool"
    viability_condition: ">=8 donor jurisdictions with non-zero cultivated-meat investment data for >=3 pre-treatment calendar years available in D001 and D002 (2016-2019 pre-Singapore), AND pre-treatment RMSPE fit <20 percent of treated-unit mean investment level achievable; both conditions checkable once D001 and D002 jurisdiction-year investment table is constructed"
    viability_test:
      metric: donor_pool_size
      op: ">="
      threshold: 8
    max_claim: causal
    threats_addressed: [F06]
    priority: 3
    is_fallback_floor: false
    claim_boundary: "CAN claim: Singapore 2020 or US 2022-2023 approvals are associated with a post-treatment investment trajectory diverging from the synthetic counterfactual, conditional on adequate pre-treatment fit and a permutation p-value below threshold. CANNOT claim: cross-state DiD results; mechanism-level heterogeneity; reliable inference if donor pool falls below 8 jurisdictions or RMSPE criterion fails; SUTVA holds if approval signals spill over to donor countries."

  - id: O4
    name: "Regulatory-uncertainty index and investment panel"
    project_type: mechanism
    identification: "Time-varying regulatory-uncertainty index per jurisdiction-quarter constructed from Federal Register notice dates (D012), LegiScan bill introduction and hearing dates (D007), and GFI policy events (D002); jurisdiction-year panel regression of annual investment (D001) on lagged uncertainty index with jurisdiction and year fixed effects and political-economy controls (D022 state food-manufacturing GDP, D021 WDI regulatory quality, D016 incumbent lobbying expenditure); tests Dixit-Pindyck real-options prediction (F03, P026, P034) that irreversible investment falls when regulatory ambiguity rises; F06 addressed by including diffusion confounders as time-varying controls rather than treating the regulatory event as the exposure"
    viability_condition: ">=5 distinct regulatory events per year on average 2018-2025 codeable from D012 and D007 across jurisdictions, providing sufficient within-year and cross-jurisdiction variation in the uncertainty index to estimate a panel regression with two-way fixed effects"
    viability_test:
      metric: n_regulatory_events_coded_per_year_avg
      op: ">="
      threshold: 5
    max_claim: associational
    threats_addressed: [F06]
    priority: 4
    is_fallback_floor: false
    claim_boundary: "CAN claim: periods of higher measured regulatory uncertainty are associated with lower investment activity, consistent with the real-options mechanism. CANNOT claim: causal identification (uncertainty index is endogenous to investment expectations and sector technology maturity); that the mechanism is uniquely real-options rather than general investor pessimism; that coefficient magnitudes extrapolate to counterfactual policy scenarios."

  - id: O_floor
    name: "Descriptive cross-jurisdiction regulatory event chronicle"
    project_type: descriptive
    identification: "No causal identification; descriptive event-study plots of global and jurisdiction-level investment series (D001, D002) aligned to regulatory event dates (state bans, national approvals, labeling rules) with bootstrapped confidence intervals around pre/post event-window means; characterises co-movement and documents the regulatory timeline without asserting causality"
    viability_condition: "always viable (descriptive); requires only D001 annual investment series 2016-2024 and D002 regulatory event date table, both confirmed as public free downloads"
    viability_test:
      metric: always
      op: always
      threshold: 0
    max_claim: descriptive
    threats_addressed: []
    priority: 9
    is_fallback_floor: true
    claim_boundary: "CAN claim: descriptive co-movement between regulatory events and investment trends across jurisdictions; a documented chronology of the regulatory environment and investment series as a factual contribution. CANNOT claim: any causal direction; cannot rule out confounding by the global macro investment cycle (40 percent sector-wide decline in 2024 per D001/P019); cannot distinguish regulatory effects from technology-readiness or macroeconomic drivers."
---

# Design Options: Ranked Candidate Research Designs

This document is a discovery-stage deck of candidate designs. It is not a committed
method card. The selection rule below determines which option to pursue once data
diagnostics are run after the D001–D007 intake phase.

---

## Selection Rule

After completing data intake for D001 (GFI State of Industry Reports) and D007
(LegiScan state bills), run the following diagnostics in priority order. Select the
**lowest-priority-number option whose viability condition holds**.

1. **O1 viability check** — count the number of US states with non-zero cultivated-meat
   firm presence or recorded investment in any pre-ban year (2020–2023). If this count
   is >=10 AND >=5 states have confirmed ban passage dates in D007, O1 is viable:
   **proceed with O1 as the primary design**.

2. **O2 viability check** (run concurrently with O1) — attempt to retrieve bill full-text
   from D007 for >=5 enacted ban states. If text is available and cosine similarity
   scores span sufficient range (SD >= 0.1), O2 is viable as a **causal supplement and
   robustness arm** alongside O1, providing an alternative IV-based identification path.
   O2 does not replace O1; convergence between O1 and O2 estimates validates identification.

3. **O3 viability check** (independent of O1/O2) — once D001 and D002 jurisdiction-year
   investment tables are constructed, check whether >=8 donor jurisdictions have data for
   >=3 pre-Singapore years and whether RMSPE fit criterion is achievable. If yes, O3 is
   viable as a **complementary country-level causal analysis** alongside whichever
   US-state design was chosen.

4. **O4 viability check** — count distinct regulatory events codeable per year from D012
   and D007. If >=5 per year on average over 2018-2025, O4 is viable as a **mechanism
   analysis** supplementing the primary causal design or as the primary associational
   analysis if O1 and O2 fail.

5. **If only O_floor holds** — when the O1 pre-ban state count is <10 or confirmed ban
   states in D007 is <5, all causal options are infeasible with current data. Execute
   O_floor (descriptive event chronicle), downgrade all claims to descriptive, and
   document the data limitation in the revision log. Flag this as requiring D008
   (Crunchbase) or D010 (PitchBook) acquisition to restore causal identification at
   a later gate.

When a higher-priority option is selected, lower-priority options may still be
executed as robustness checks or secondary analyses, but the project claim is anchored
to the selected primary option's `max_claim` level and cannot be ratcheted up by
secondary analyses alone.

---

## Option O1 — Staggered DiD on State Ban Timing

### Identification logic

The primary source of identifying variation is the staggered enactment of US state
bans on cultivated meat production or sale. At least five states (Alabama, Florida,
Tennessee, Iowa, Idaho) enacted bans across distinct legislative sessions beginning in
2024, creating a staggered adoption structure of the type analysed by Callaway and
Sant'Anna (2021, P027). States that have not enacted bans serve as controls.

The Callaway–Sant'Anna group-time ATT estimator compares each cohort of states (those
enacting bans in the same legislative session) against not-yet-treated and never-treated
units only, avoiding the negative-weighting problem documented by Goodman-Bacon (2021,
P035) in two-way fixed-effects estimators with heterogeneous treatment timing. Event-study
plots from this estimator test pre-trend parallel trends as the primary identifying
assumption check. Borusyak, Jaravel, and Spiess (2024, P036) imputation estimator runs
as a robustness alternative.

The primary outcome is annual investment raised by cultivated-meat firms from GFI State
of Industry Reports (D001). Secondary outcomes are firm entry and exit counts from the
same source. The treatment variable is a binary ban indicator coded from LegiScan (D007)
bill passage dates, cross-referenced with GFI Global Policy tracker (D002).

### Addressing F06 (policy diffusion / endogenous treatment timing)

F06 warns that state ban timing was coordinated through model-legislation networks
(ALEC-linked bills), so treatment assignment is correlated with political and economic
characteristics — strength of cattlemen's associations, beef output per capita —
rather than being as-good-as-random. Pre-specified responses:

- **Pre-trend falsification**: event-study plots must show flat pre-treatment
  coefficients for ban-adopting states relative to controls. A significant pre-trend
  refutes parallel trends and degrades O1 to O_floor.
- **Covariate-augmented doubly-robust DiD**: include time-varying state controls
  (annual beef production, food-manufacturing GDP from D022, partisan vote share,
  WDI regulatory quality from D021) using Sant'Anna–Zhao (2020) doubly-robust
  estimator to condition on observables correlated with diffusion.
- **Placebo treatment date**: assign fake ban dates two years before actual adoption;
  a significant placebo effect indicates pre-existing trends drive the result.
- **Incumbent-lobbying control**: include OpenSecrets federal lobbying expenditure
  (D016) by NCBA and NPPC as a time-varying control for Stigler-capture dynamics
  (F01, P024) that independently predict both ban adoption and investment.

If O2 is also viable, the cosine-similarity instrument provides a fourth, stronger
response to F06 by directly modelling the diffusion mechanism.

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| Annual investment by firm or jurisdiction | GFI State of Industry Reports | D001 |
| State ban enactment dates | LegiScan | D007 |
| Regulatory event cross-reference | GFI Global Policy Report | D002 |
| State food-manufacturing GDP (control) | BEA Regional Data | D022 |
| WDI regulatory quality index (control) | World Bank WDI | D021 |
| Incumbent lobbying expenditure (control) | OpenSecrets | D016 |
| Federal regulatory milestones | Federal Register API | D012 |

---

## Option O2 — Bill-Text Reuse / Model-Legislation Diffusion as IV

### Identification logic

The F06 threat to O1 rests on diffusion endogeneity: states adopting bans earliest
may differ systematically from later adopters on dimensions correlated with investment
outcomes. O2 directly models the diffusion mechanism by measuring how closely each
enacted state bill reproduces the text of a model-legislation template, then uses
that similarity score as an instrumental variable for ban adoption timing.

States that adopt near-verbatim copies of the same model bill (cosine similarity above
a threshold to Alabama SB23 as reference corpus) adopted for coordinated-political rather
than locally-motivated reasons. States that drafted independent legislation may have
adopted for locally-driven economic motivations — exactly the endogeneity that F06
warns about. The cosine-similarity score separates these two adoption pathways, providing
a continuous instrument that affects investment outcomes only through the ban adoption
channel (the exclusion restriction), not directly.

The design draws on Meseguer and Gilardi (2009, P029) for the theoretical diffusion
mechanism and Shipan and Volden (2008, P042) for the four mechanisms of state policy
diffusion (learning, emulation, competition, coercion). It turns the diffusion mechanism
from a threat into an identified source of variation.

### Two analytical uses

1. **Fuzzy-IV DiD**: the cosine-similarity score serves as the first-stage instrument;
   the endogenous variable is ban adoption timing. The second-stage estimates the LATE
   for complier states (those whose adoption timing was determined by template access
   rather than local economic pressure).
2. **Effect-modifier subgroup DiD**: run O1 separately for high-similarity (coordinated)
   and low-similarity (independent) adopter states. If only coordinated adopters show
   investment effects, the estimate for low-similarity states is a cleaner causal
   estimate less contaminated by the F06 confounders.

### Exclusion restriction validation

The instrument (cosine similarity to model template) must satisfy: template-similarity
scores are uncorrelated with pre-period investment trends and economic characteristics
after conditioning on legislative-session fixed effects. Pre-specified test: regress
bill-text similarity score on pre-ban state beef production per capita, partisan vote
share, and pre-period investment growth rate; near-zero coefficients validate the
exclusion restriction.

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| State ban bill full-text | LegiScan JSON export | D007 |
| Reference template text (Alabama SB23) | LegiScan | D007 |
| Cosine similarity scores | computed from D007 | — |
| Investment and entry outcomes | GFI State of Industry Reports | D001 |

---

## Option O3 — Synthetic Control for National Regulatory Approval Events

### Identification logic

While O1 and O2 exploit cross-state variation within the US, O3 exploits cross-country
variation in national regulatory approval events: Singapore's first-ever cultivated-meat
approval (December 2020, D006), US FDA/USDA pre-market consultation completions for
UPSIDE Foods (November 2022) and GOOD Meat (March 2023, D003), and Israel's approval
of Aleph Farms cultivated beef (December 2023, D015). Italy enacted a national
production ban (October 2023) from D002/D005 context.

The synthetic control method (Abadie and Gardeazabal 2003, P028; Abadie, Diamond, and
Hainmueller 2010, P037) constructs a weighted combination of donor countries to form
a counterfactual investment trajectory for each treated jurisdiction. The key inferential
question is whether Singapore's investment trajectory post-2020 diverged from its
synthetic counterfactual, and whether the US trajectory diverged in 2022–2023.
Placebo inference uses leave-one-out resampling and permutation tests over the donor pool.

### Addressing F06 at the national level

The F06 diffusion threat is qualitatively less severe for national approval events than
for US state bans. Singapore's SFA review, the FDA/USDA joint-framework consultation
process, and Israel MoH's assessment were driven by domestic science-regulatory
processes rather than by cross-national legislative diffusion networks. The main
residual threat is that approval timing coincides with domestic political-economy
factors (F01, P024) correlated with investment trends. This is addressed by including
pre-treatment investment growth rate as a predictor variable in the synthetic control
construction and by requiring adequate pre-treatment RMSPE fit before reporting results.

### Thin donor pool risk (F05 caveat)

F05 explicitly warns that fewer than ten jurisdictions have both regulatory events of
interest and outcome data, risking that the synthetic control collapses to interpolation
among structurally dissimilar economies. The viability condition (>=8 donors with >=3
pre-treatment years, RMSPE <20 percent) is the binding constraint; if unmet, O3 is
infeasible and O1 or O_floor remains.

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| Annual investment by country (2016–2024) | GFI State of Industry Reports | D001 |
| National approval event dates | GFI Global Policy Report | D002 |
| Singapore approved novel foods list | Singapore Food Agency | D006 |
| Israel MoH approval and IIA grants | Israel MoH / IIA | D015 |
| WDI country controls | World Bank WDI | D021 |
| AgFunder sector investment reports | AgFunder | D013 |

---

## Option O4 — Regulatory-Uncertainty Index and Investment Panel

### Identification logic

Regulatory uncertainty — periods when firms do not know whether the FDA will complete
a pre-market review, whether a state ban will pass, or whether labeling rules will
change — raises the option value of waiting before committing to irreversible investments
in production facilities or long-term supply contracts (Dixit-Pindyck 1994, P026;
Pindyck 1991, P034). O4 constructs a quarterly regulatory-uncertainty index at the
jurisdiction level and estimates its association with investment flows in a panel
regression.

Three input streams are merged: (a) Federal Register API (D012) records of FDA and
USDA-FSIS notices, proposed rules, and public comments mentioning cultivated meat;
(b) LegiScan D007 bill introductions and hearing dates for cultivated-meat legislation
across all states; (c) GFI D002 policy event dates. Each event is coded by type and
jurisdiction and aggregated into a quarterly count index, optionally weighted by event
severity (ban passage > bill introduction > regulatory notice).

The jurisdiction-year panel regression of annual investment (D001) on lagged uncertainty
index includes jurisdiction and year fixed effects plus political-economy controls:
state food-manufacturing GDP (D022), WDI regulatory quality index (D021), and
incumbent-industry lobbying expenditure (D016). This conditions on the observable
confounders that drive both regulatory uncertainty and investment decisions (F06).

### Role and claim level

Because the uncertainty index is endogenous to the investment landscape (periods of
high investor interest attract legislative scrutiny, creating reverse causality), the
max_claim is associational. O4's primary value is as a mechanism-consistency test
for the real-options prediction (F03) and as a source of the time-varying uncertainty
covariate used in O1 and O2 specifications. When O1 is selected as primary, O4
runs as a secondary mechanism analysis; when O1 is infeasible, O4 provides the
strongest attainable associational result.

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| Federal regulatory notices (FDA, USDA) | Federal Register API | D012 |
| State bill introduction and hearing dates | LegiScan | D007 |
| Cross-jurisdiction regulatory events | GFI Global Policy Report | D002 |
| Annual investment outcomes | GFI State of Industry Reports | D001 |
| State food-manufacturing GDP (control) | BEA Regional Data | D022 |
| WDI regulatory quality index (control) | World Bank WDI | D021 |
| Incumbent lobbying expenditure (control) | OpenSecrets | D016 |

---

## Option O_floor — Descriptive Cross-Jurisdiction Regulatory Event Chronicle

### Design logic

The floor design is always viable because it requires only the GFI annual investment
series (D001) and GFI global regulatory event dates (D002), both confirmed as public
free downloads. It makes no causal claims and requires no identification assumption.

The design produces:

1. **Regulatory timeline figure**: a chronological map of all regulatory events
   (national approvals, state bans, EU novel food filings, public funding
   announcements) sourced from D002, annotated on the global investment series
   from D001.
2. **Descriptive event-study plots**: investment-series plots centered on each major
   regulatory event date, showing the raw investment trajectory in the two years
   before and two years after each event, without difference-in-differences
   identification.
3. **Cross-jurisdiction matrix**: a jurisdiction-year matrix of regulatory status
   (approved / banned / pending / absent) against investment and firm-count outcomes
   from D001 and D017.

### When this design is the primary contribution

If the pre-ban state count is <10 (O1 infeasible) and bill texts are insufficient for
O2, this floor design represents the main deliverable. The factual contribution is a
systematic, data-grounded chronology of the regulatory environment and its co-movement
with investment flows — a contribution not yet consolidated in the existing literature
(Johnson and Monaco 2025, P002; Stephens et al. 2018, P006; Post et al. 2020, P040).
Claim language must be explicitly descriptive: "regulatory approvals coincide with
subsequent investment growth" rather than "caused."

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| Annual global investment totals | GFI State of Industry Reports | D001 |
| Regulatory event dates (all jurisdictions) | GFI Global Policy Report | D002 |
| Firm count and founding dates | GFI Company Tracker | D017 |
