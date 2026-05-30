---
schema_version: 1
required_sections:
  - ## Project Type
  - ## Candidate Data
status: filled
project_type: causal
claim_type: "Regulatory events (state bans, national approvals) causally shift cultivated-meat firm investment and entry rates across jurisdictions"
unit_of_analysis: "firm-year (primary); jurisdiction-year (secondary)"
grounded_data_ids: [D001, D002, D007]
addresses_threats: [F06]
---

# Research Design Sketch

This is a provisional sketch. It is not yet the protected method card.

## Research Question

Do government regulatory actions toward cultivated meat — specifically US state-level bans
enacted 2024–2025 and national-level market approvals (Singapore 2020, US 2023) — causally
affect cultivated-meat firm investment activity and market entry across jurisdictions?

The identifying variation is the staggered timing of US state bans (at least 5 states:
Alabama, Florida, Tennessee, Iowa, Idaho) enacted across different legislative sessions from
2024 onward, combined with cross-jurisdiction panel data on firm-level investment flows and
entry/exit events constructed from GFI annual reports (D001) and GFI global policy tracker
(D002).

## Project Type

**Causal** — the design relies on staggered legislative adoption of state-level bans as a
source of identifying variation in regulatory treatment timing. The key variation is
within-firm or within-jurisdiction, before versus after ban enactment, across states that
adopted bans in different legislative sessions. This justifies calling the design causal
conditional on the parallel-trends assumption and subject to the threats addressed in the
Threats to Validity section.

The design is NOT purely descriptive because it attempts to go beyond documenting
covariation between regulatory events and investment outcomes, and instead uses the temporal
ordering and cross-sectional heterogeneity in adoption timing to identify a causal effect.
It is NOT a mechanism study in the first instance, though the three mechanism channels
(regulatory capture F01, organizational legitimacy F02, real options F03) generate
testable predictions that the design can evaluate as secondary analyses.

## Unit of Analysis

**Primary:** firm-year. Each observation is a cultivated-meat firm observed in a given
calendar year. The outcome is firm-level investment raised in that year (from GFI D001 firm
profiles where available) or an indicator of active status / market entry.

**Secondary:** jurisdiction-year. Each observation is a jurisdiction (US state or country)
in a calendar year, with outcomes being total investment flows and active firm count
attributable to that jurisdiction.

The firm-year unit is preferred because it allows within-firm identification of investment
changes around ban adoption. The jurisdiction-year unit is the fallback if firm-level panel
structure is insufficient across GFI annual report editions.

## Treatment / Exposure

**Primary treatment:** passage of a state-level ban on cultivated meat production or sale
(binary, equal to 1 in the year of enactment and all subsequent years for that jurisdiction).
Treatment events are sourced from LegiScan (D007) and cross-referenced with GFI global
policy tracker (D002). As of 2025, at least five states have enacted bans (Alabama SB23,
Florida SB1084, Tennessee, Iowa, Idaho).

**Secondary treatment:** national-level market approval (Singapore December 2020; US FDA/USDA
joint pre-market consultation completion for UPSIDE Foods November 2022 and GOOD Meat March
2023). These are single large-N events for event-study analysis at the global investment
series level using GFI D001 annual totals.

**Regulatory uncertainty index:** periods of pending FDA pre-market review or anticipated
state legislation create regulatory ambiguity; this can be coded as a continuous exposure
using Federal Register notice dates (D012) and LegiScan bill introduction dates (D007).

## Outcome

1. **Annual investment raised by cultivated-meat firms** (USD, from GFI D001 annual series
   2016–2024 and Crunchbase D008 for firm-level detail): primary outcome variable.
2. **Firm entry rate**: count of new cultivated-meat firms founded or first reporting activity
   in GFI annual firm profiles.
3. **Firm exit / inactive rate**: firms dropping out of GFI annual firm profiles.
4. **Patent filings** (PatentsView D009): R&D activity proxy, used as secondary outcome to
   test whether investment effects are accompanied by reduced innovation activity.

## Identification Strategy

**Estimator:** Staggered difference-in-differences using the Callaway and Sant'Anna (2021)
group-time ATT estimator (framing card F04, anchor P027), supplemented by Goodman-Bacon
(2021) decomposition (P035) to diagnose negative-weighting from heterogeneous treatment
effects in the TWFE baseline.

The Callaway–Sant'Anna estimator compares each cohort of treated jurisdictions (states
enacting bans in the same legislative session) against not-yet-treated and clean-control
units, avoiding contamination from already-treated units. Group-time ATTs are aggregated to
an average treatment effect and to event-study plots that test pre-trend parallel trends.

**Robustness:** Borusyak, Jaravel, and Spiess (2024) imputation estimator (P036) as an
alternative. If the panel is too thin for staggered DiD, downgrade to synthetic control
(Abadie and Gardeazabal 2003, P028; Abadie, Diamond, and Hainmueller 2010, P037) using
donor jurisdictions with comparable pre-period investment trajectories (framing card F05).

**Mechanism tests:** After establishing the reduced-form effect, test mechanism heterogeneity
by interacting treatment with (a) state-level conventional beef production per capita as a
proxy for capture intensity (F01/Stigler P024), (b) presence of cultivated-meat firms
headquartered in the state before ban as a proxy for legitimacy disruption (F02/Suchman
P025), and (c) regulatory uncertainty index around pre-ban legislative activity as a proxy
for option-value delay incentive (F03/Dixit-Pindyck P026).

## Threats to Validity

**F06 — Policy diffusion / endogenous treatment timing (primary threat):**
State bans were coordinated through national model-legislation networks (ALEC-linked bills),
so treatment timing is correlated with political and economic characteristics — strength of
cattlemen's associations, conventional beef output per capita, partisan composition — that
may independently predict investment outcomes, violating parallel trends. Responses:

1. *Diffusion timing instrument*: exploit within-wave variation in which states adopted first,
   conditional on being in the same ideological wave of model legislation. If bill introduction
   date is driven by legislative calendar rather than local economic conditions, within-wave
   adoption sequence may be quasi-random (as noted in F06 caveat).
2. *Pre-trend falsification*: event-study plots from the Callaway–Sant'Anna estimator must
   show flat pre-treatment trends for banning states relative to controls.
3. *Covariate-augmented DiD*: condition on state-level time-varying confounders (annual beef
   output, state GDP, Republican vote share) using Sant'Anna and Zhao (2020) doubly robust
   estimator.
4. *Placebo tests*: assign fake ban dates two years before actual adoption; if pre-placebo
   effects are non-zero, parallel trends is refuted.

**F04 caveat — Staggered adoption with heterogeneous effects:**
Addressed by using Callaway–Sant'Anna rather than TWFE, and by Goodman-Bacon decomposition
to check whether negative-weighting groups are driving results.

**F02 caveat — Global legitimacy spillovers:**
A single approval anywhere may signal global institutional endorsement, so a purely spatial
treatment design understates the mechanism. Addressed by including global-level investment
series as a separate event-study around the Singapore 2020 and US 2022–2023 approvals, and
testing whether state-level effects persist conditional on global investment trends.

**F03 caveat — Competitive first-mover dynamics dominating real-options delay:**
Real-options logic predicts reduced investment under uncertainty, but competitive pressure may
override waiting incentives. Addressed by including a firm-count outcome: if competition is
the dominant mechanism, we should see continued entry even as individual firm investment
falls. Entry acceleration post-approval would be consistent with competitive first-mover
dynamics (F03 caveat noted).

**F05 caveat — Thin donor pool for synthetic control:**
If fewer than ten jurisdictions have both treatment events of interest and outcome data,
synthetic control is unreliable. This is acknowledged as a binding constraint; the minimum
viable version (below) uses DiD at the US state level where N is larger, reserving synthetic
control for secondary country-level analysis with explicit pre-treatment fit diagnostics.

**F01 caveat — Genuine food-safety concern vs. capture:**
If bans passed in jurisdictions with negligible conventional meat production, capture
mechanism is refuted. Test: regress ban adoption on lagged beef production per capita in
event-history (probit/hazard) model using D007 (LegiScan) ban dates.

## Candidate Data

| Variable | Data Source | data_id | Notes |
|---|---|---|---|
| Annual investment raised (firm-year or agg) | GFI State of Industry Reports | D001 | 2016–2024 series; firm-level in some editions |
| Regulatory event dates (bans, approvals) | GFI Global Policy Report | D002 | 2019–2024; cross-jurisdiction policy timeline |
| State ban passage dates | LegiScan US State Legislative Database | D007 | Bill-level dates for 50 states; cross-ref D002 |
| Firm founding / exit dates | GFI State of Industry + Crunchbase | D001, D008 | Crunchbase adds founding dates and round-level data |
| Patent filings (R&D proxy) | PatentsView | D009 | Annual filing counts by assignee; secondary outcome |
| US federal regulatory milestones | FDA Pre-Market Consultation DB | D003 | Small N (2 completions); used as treatment event |
| USDA grant-of-inspection dates | USDA FSIS Directory | D004 | Corroborates D003 federal treatment timing |
| Public funding by jurisdiction | GFI Global Policy Report | D002 | $523M globally in 2023; time-varying control |
| Federal Register regulatory notices | Federal Register API | D012 | Uncertainty index construction (pre-review periods) |

All data_ids listed above (D001, D002, D003, D004, D007, D008, D009, D012) are present in
discovery/data_inventory.csv. The grounded_data_ids in the front matter are limited to
[D001, D002, D007] as the three sources directly providing treatment and outcome variables;
the others are supplementary.

## Minimum Viable Version

**Design:** US-state-level jurisdiction-year panel, 2020–2025, comparing investment activity
attributable to firms headquartered in states that enacted bans (treatment) against states
without bans (control), using the Callaway–Sant'Anna staggered DiD estimator.

**Outcome:** GFI annual firm count and total investment by jurisdiction, extracted from D001
editions 2020–2025 (six observation years, ~50 states, ~300 observations before subsetting
to states with any cultivated-meat firm presence).

**Treatment:** Binary ban indicator coded from D007 (LegiScan) and cross-referenced with D002.

**What this does NOT require at minimum viable stage:** firm-level panel data (use
jurisdiction-year aggregates), Crunchbase Pro subscription (use GFI firm profiles), patent
data (defer D009), or EU/Singapore synthetic control (defer D005/D006).

**Credibility condition:** The minimum viable version is credible only if at least 10–15
states have non-zero cultivated-meat firm or investment presence in the pre-period so that
the parallel-trends assumption is estimable. If GFI reports show firm presence is heavily
concentrated in California, New York, and a few other states, the effective N may be too
small for DiD and the design degrades to a qualitative event-study with descriptive
commentary.

## Claim Boundary

**CAN claim (if identifying assumptions hold):**
- US state-level bans on cultivated meat are associated with a measurable reduction in
  investment activity or firm presence in banning jurisdictions, relative to non-banning
  states, after controlling for pre-period trends.
- The magnitude and timing of investment responses are consistent with (or inconsistent with)
  the real-options, legitimacy, and regulatory capture mechanisms.

**CANNOT claim:**
- National or global investment trends are caused by US state bans (too small a share of
  global market).
- Bans cause firm bankruptcy or exit (not enough exit observations; confounded by
  macroeconomic investment cycle, which dropped 40% globally 2024 regardless of state bans).
- Singapore or EU regulatory actions are causally identified (no plausible within-jurisdiction
  variation; synthetic control requires adequate donor pool not yet confirmed).
- The results generalize beyond the cultivated-meat sector or beyond the 2020–2025 period.
- Welfare or social optimality of any regulatory policy (design is positive, not normative).
- Effects on conventional meat industry or consumer prices (outcome data not available).
