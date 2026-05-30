---
status: filled
options:
  - id: O1
    name: "Staggered DiD on state ban timing"
    project_type: causal
    identification: "Staggered difference-in-differences exploiting within-state before-vs-after variation in ban enactment timing across US states (F04); Callaway–Sant'Anna 2021 group-time ATT estimator (P027) avoids negative-weighting from heterogeneous treatment effects; Goodman-Bacon 2021 decomposition (P035) as diagnostic; Borusyak-Jaravel-Spiess 2024 imputation estimator (P036) as robustness alternative"
    viability_condition: ">=10 US states have non-zero cultivated-meat firm presence or recorded investment in any pre-ban year verified from D001 editions 2020-2024; >=5 states have confirmed ban passage dates in D007 (LegiScan); both conditions checkable once D001 and D007 are downloaded and merged"
    threats_addressed: [F06]
    priority: 1
    is_fallback_floor: false
    claim_boundary: "CAN claim: US state bans are associated with within-state declines in firm presence or investment relative to not-yet-treated and clean-control states, conditional on parallel pre-trends. CANNOT claim: national or global investment trends are caused by state bans; bans cause firm bankruptcy or exit; results generalise beyond cultivated meat or beyond 2020-2025; Singapore or EU regulatory actions are causally identified under this design."
  - id: O2
    name: "Bill-text cosine-similarity / model-legislation diffusion instrument"
    project_type: mechanism
    identification: "Text-reuse analysis of enacted state ban legislation (D007 LegiScan full-text) computing cosine similarity of each bill to the earliest enacted ban (Alabama SB23) or a known ALEC model template; high-similarity states classified as coordinated-diffusion adopters used as instrument or effect-modifier in 2SLS or subgroup DiD, directly addressing F06 endogenous-diffusion threat (P029 Meseguer-Gilardi; P042 Shipan-Volden)"
    viability_condition: "D007 full-text is extractable for >=5 enacted ban states via LegiScan JSON or bulk export; Alabama SB23 text is recoverable as reference corpus; text preprocessing and cosine similarity computation feasible in Python; viability checkable once D007 is accessed and bill texts are retrieved"
    threats_addressed: [F06]
    priority: 2
    is_fallback_floor: false
    claim_boundary: "CAN claim: states adopting near-verbatim model-legislation text show a different investment response than states with independently drafted bans, consistent with a coordinated national campaign rather than local economic conditions driving ban adoption. CANNOT claim: text similarity is a fully clean instrument without additional evidence that ALEC membership is uncorrelated with investment confounders; cannot estimate an aggregate average treatment effect without the causal DiD scaffold from O1; cannot purge all endogeneity absent a formal exclusion-restriction argument."
  - id: O3
    name: "Synthetic control for national regulatory approval events"
    project_type: causal
    identification: "Synthetic control method (F05; Abadie-Gardeazabal 2003 P028; Abadie-Diamond-Hainmueller 2010 P037) using Singapore December 2020 first-ever cultivated-meat market approval and US FDA/USDA 2022-2023 pre-market consultation completions as treatment events; donor pool of non-approving countries constructed from GFI D001 and D002 annual investment series; placebo inference via leave-one-out and permutation tests"
    viability_condition: ">=8 donor jurisdictions have non-zero cultivated-meat investment data for >=3 pre-treatment calendar years available in D001 and D002 (2016-2019 pre-Singapore); pre-treatment RMSPE fit <20 percent of treated unit mean investment level achievable; both conditions checkable once D001 and D002 jurisdiction-year investment table is constructed"
    threats_addressed: [F06]
    priority: 3
    is_fallback_floor: false
    claim_boundary: "CAN claim: Singapore 2020 approval or US 2022-2023 approvals are associated with a post-treatment investment trajectory diverging from the synthetic counterfactual, conditional on adequate pre-treatment fit. CANNOT claim: cross-state DiD results; mechanism-level heterogeneity; F06 endogeneity is fully resolved since national approval timing also reflects political economy; donor pool violations of SUTVA if approval signals spill over to donor countries."
  - id: O_floor
    name: "Descriptive cross-jurisdiction regulatory event-study"
    project_type: descriptive
    identification: "No causal identification; descriptive event-study plots of global and jurisdiction-level investment series (D001, D002) aligned to regulatory event dates (state bans, national approvals, labeling rules) with bootstrapped confidence intervals; characterises co-movement and documents the regulatory timeline without asserting causality"
    viability_condition: "always viable (descriptive); requires only D001 annual investment series 2016-2024 and D002 regulatory event date table, both confirmed as public free downloads"
    threats_addressed: []
    priority: 9
    is_fallback_floor: true
    claim_boundary: "CAN claim: descriptive co-movement between regulatory events and investment trends across jurisdictions; provides a documented chronology of the regulatory environment and investment series as a factual contribution. CANNOT claim: any causal direction; cannot rule out confounding by the global macro investment cycle (40 percent sector-wide decline in 2024 per D001/P019); cannot distinguish regulatory effects from technology-readiness or macroeconomic drivers."
---

# Design Options: Ranked Candidate Research Designs

This document is a discovery-stage deck of candidate designs. It is not a committed
method card. The selection rule below determines which option to pursue once data
diagnostics are run after the D001–D007 intake phase.

---

## Selection Rule

After completing data intake for D001 (GFI State of Industry Reports) and D007
(LegiScan state bills), run the following diagnostics in priority order:

1. **O1 viability check** — count the number of US states with non-zero cultivated-meat
   firm presence or recorded investment in any pre-ban year (2020–2023). If this count
   is >=10 AND >=5 states have confirmed ban passage dates in D007, O1 is viable:
   **proceed with O1 as the primary design**.

2. **O2 viability check** (conditional on O1 viable) — attempt to retrieve bill full-text
   from D007 for >=5 enacted ban states. If text is available and cosine similarity to
   Alabama SB23 is computable, O2 is viable as a **mechanism supplement** to O1. O2
   runs in parallel with O1, sharpening the F06 response; it does not replace O1.

3. **O3 viability check** (independent of O1/O2) — once D001 and D002 jurisdiction-year
   investment tables are constructed, check whether >=8 donor jurisdictions have data for
   >=3 pre-Singapore years and whether RMSPE fit criterion is achievable. If yes, O3 is
   viable as a **complementary country-level analysis** alongside whichever US-state
   design was chosen.

4. **If only O_floor holds** — when the O1 pre-ban state count is <10 or confirmed ban
   states in D007 is <5, all causal options are infeasible with current data. Execute
   O_floor (descriptive event-study), downgrade all claims to associational, and document
   the data limitation in the revision log. Flag this as requiring D008 (Crunchbase) or
   D010 (PitchBook) acquisition to restore causal identification at a later gate.

The selected design is the **lowest-priority option whose viability condition holds**.
O1 is tried first; O_floor is the guaranteed floor. O2 and O3 can be layered as
supplementary analyses if their own conditions also hold independently.

---

## Option O1: Staggered DiD on state ban timing

### Identification logic

The primary source of identifying variation is the staggered enactment of US state
bans on cultivated meat production or sale. At least five states (Alabama, Florida,
Tennessee, Iowa, Idaho) enacted bans across distinct legislative sessions beginning in
2024, creating a staggered adoption structure of the type analysed by Callaway and
Sant'Anna (2021, P027). States that have not enacted bans — and states that have not
yet enacted bans — serve as controls.

The Callaway–Sant'Anna group-time ATT estimator compares each cohort of states (those
enacting bans in the same legislative session) against not-yet-treated and never-treated
units only, avoiding the negative-weighting problem documented by Goodman-Bacon (2021,
P035) in two-way fixed-effects estimators with heterogeneous treatment timing. Event-study
plots from this estimator test pre-trend parallel trends as the primary identifying
assumption check.

The primary outcome is annual investment raised by cultivated-meat firms, drawn from GFI
State of Industry Reports (D001). The secondary outcome is firm entry and exit counts from
the same source. The treatment variable is a binary ban indicator coded from LegiScan
(D007) bill passage dates, cross-referenced with GFI Global Policy tracker (D002).

### Addressing F06 (policy diffusion / endogenous treatment timing)

F06 warns that state ban timing was coordinated through model-legislation networks
(ALEC-linked bills), so treatment assignment is correlated with political and economic
characteristics rather than being as-good-as-random. Three pre-specified responses:

- **Pre-trend falsification**: event-study plots must show flat pre-treatment coefficients.
  Rejection refutes parallel trends and degrades O1 to O_floor.
- **Covariate-augmented DiD**: include time-varying state-level controls (annual beef
  output, partisan vote share, state GDP) using Sant'Anna–Zhao (2020) doubly robust
  estimator to condition on observable confounders correlated with diffusion.
- **Placebo treatment date**: assign fake ban dates two years before actual adoption;
  a significant placebo effect indicates pre-existing trends are driving the result.

If O2 is also viable, the cosine-similarity instrument provides a fourth, stronger
response to F06 by separating coordinated-diffusion adopters from independently
motivated adopters.

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| Annual investment by firm or jurisdiction | GFI State of Industry Reports | D001 |
| State ban enactment dates | LegiScan | D007 |
| Regulatory event cross-reference | GFI Global Policy Report | D002 |
| Public funding by jurisdiction (control) | GFI Global Policy Report | D002 |
| Federal regulatory milestones | Federal Register API | D012 |

---

## Option O2: Bill-text cosine-similarity / model-legislation diffusion instrument

### Identification logic

The F06 threat to O1 rests on diffusion endogeneity: states that adopt bans first may
differ systematically from later adopters on dimensions correlated with investment
outcomes. O2 directly models the diffusion mechanism by measuring how closely each
enacted state bill reproduces the text of a model-legislation template.

States that adopt near-verbatim copies of the same model bill (e.g. cosine similarity
>0.85 to Alabama SB23 as reference) adopted for coordinated-political rather than
locally-motivated reasons; states that drafted independent legislation may have adopted
for different reasons. This classification, derived from D007 full-text, creates a
moderating variable — or an instrumental variable in a 2SLS framework — that partials
out the diffusion pathway from the causal effect of interest.

The design draws on Meseguer and Gilardi (2009, P029) for the theoretical diffusion
mechanism and Shipan and Volden (2008, P042) for the four mechanisms of state policy
diffusion. It directly addresses F06 by turning the diffusion mechanism from a threat
into an identified source of variation.

### Two analytical uses

1. **Effect-modifier subgroup DiD**: run O1 separately for high-similarity (coordinated)
   and low-similarity (independent) adopter states. If only coordinated adopters show
   investment effects, the estimate for low-similarity states is a cleaner causal
   estimate less contaminated by the F06 confounders.
2. **Instrument for ban adoption timing**: use the bill-introduction date of the model
   template in the national legislative calendar as an instrument for state ban timing,
   conditional on the state being in a high-similarity cluster. The exclusion restriction
   requires that the national template introduction date affects local investment
   outcomes only through the state ban timing, not directly.

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| State ban bill full-text | LegiScan JSON export | D007 |
| Reference template text (Alabama SB23) | LegiScan | D007 |
| Cosine similarity scores | computed from D007 | — |
| Investment and entry outcomes | GFI State of Industry Reports | D001 |

---

## Option O3: Synthetic control for national regulatory approval events

### Identification logic

While O1 exploits cross-state variation within the US, O3 exploits cross-country
variation in national regulatory approval events: Singapore's first-ever cultivated-meat
approval (December 2020) and the US FDA/USDA pre-market consultation completions for
UPSIDE Foods (November 2022) and GOOD Meat (March 2023).

The synthetic control method (Abadie and Gardeazabal 2003, P028; Abadie, Diamond, and
Hainmueller 2010, P037) constructs a weighted combination of donor countries to form a
counterfactual investment trajectory for the treated jurisdiction. The key inferential
question is whether Singapore's investment trajectory post-2020 diverged from its
synthetic counterfactual, and whether the US investment trajectory diverged from its
synthetic counterfactual in 2022–2023.

Placebo inference uses leave-one-out resampling and permutation tests to assess whether
the treatment gap exceeds what would arise if the same method were applied to
randomly-selected donor units (Abadie et al. 2010, P037).

### Addressing F06 at the national level

The F06 threat is less acute for national approval events than for US state bans because
Singapore's approval timeline was driven by the Singapore Food Agency's independent
review process rather than a model-legislation network. However, the timing of national
approvals still reflects political economy (F01/Stigler P024), which could correlate with
investment trends. This is addressed by including pre-treatment investment growth rate
as a matching variable in the synthetic control construction so that donor weights
prioritise countries with similar pre-treatment trajectories.

### Thin donor pool risk (F05 caveat)

F05 explicitly warns that the donor pool is extremely thin at the national level. The
viability condition (>=8 donors with >=3 pre-treatment years) is the binding constraint.
If the donor pool is insufficient, O3 is infeasible; O1 and O_floor remain.

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| Annual investment by country (2016–2024) | GFI State of Industry Reports | D001 |
| National approval event dates | GFI Global Policy Report | D002 |
| Singapore approved novel foods list | Singapore Food Agency | D006 |
| EU novel food application timeline | EU Novel Food Register | D005 |

---

## Option O_floor: Descriptive cross-jurisdiction regulatory event-study

### Design logic

The floor design is always viable because it requires only the GFI annual investment
series (D001) and GFI global regulatory event dates (D002), both confirmed as public
free downloads. It makes no causal claims.

The design produces:
1. **Regulatory timeline figure**: a chronological map of all regulatory events
   (national approvals, state bans, EU novel food filings, public funding announcements)
   sourced from D002, annotated on the global investment series from D001.
2. **Descriptive event-study plots**: investment-series plots centered on each major
   regulatory event date, showing the raw investment trajectory in the two years before
   and two years after each event, without difference-in-differences identification.
3. **Cross-jurisdiction table**: a jurisdiction-year matrix of regulatory status
   (approved / banned / pending / absent) against investment and firm-count outcomes.

### When this design is the primary contribution

If the pre-ban state count is <10 (O1 infeasible), this floor design represents the
main deliverable. The contribution is documenting the regulatory chronology and its
co-movement with investment flows in a systematic, data-grounded way that existing
literature has not done — a factual contribution even without causal identification.
Claim language must be explicitly associational: "regulatory approvals are associated
with subsequent investment growth" rather than "caused".

### Candidate data

| Variable | Source | data_id |
|---|---|---|
| Annual global investment totals | GFI State of Industry Reports | D001 |
| Regulatory event dates (all jurisdictions) | GFI Global Policy Report | D002 |
