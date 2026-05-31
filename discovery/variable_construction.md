---
status: filled
variables:
  - name: state_ban
    role: treatment
    definition: "binary = 1 in the calendar year a US state enacts a cultivated-meat
      production or sale ban (by governor signature or enactment date) and in all
      subsequent years; = 0 in all pre-enactment years and for never-treated states;
      coded at the state-year level for the US panel"
    source_data_id: D007
    construction: "query LegiScan fulltext search and JSON API for bills containing
      'cultivated meat', 'cell-cultured meat', 'lab-grown meat', 'cell-based meat'
      across all 50 states and DC; record state, bill number, introduction date,
      committee passage date, floor passage date, and governor action date; cross-check
      each entry against GFI Global Policy Report (D002) ban listings and individual
      state legislature websites for confirmed states (Alabama SB23, Florida SB1084,
      Tennessee, Iowa, Idaho); code the treatment year as the calendar year of the
      governor signature or, where absent, the legislative enactment date; build
      state-year panel with ban_active indicator; distinguish production bans from
      sale-only bans and labeling-only rules in a supplementary policy_type variable"
    validity_concern: "ambiguity between production bans, sale bans, and labeling-only
      rules means a single binary misspecifies treatment intensity; LegiScan free
      API has rate limits and full bulk export requires a paid GAITS subscription,
      so free-tier access may not capture all relevant bills or provide full-text;
      bills still in committee at data extraction date must be coded as missing (not
      zero); coordinated model-legislation adoption means enactment timing is correlated
      with state political characteristics, threatening parallel trends (F06)"
    constructible: uncertain

  - name: national_approval_event
    role: treatment
    definition: "binary = 1 in the calendar year a national food regulatory authority
      grants the first formal market authorization or regulatory clearance for a
      cultivated-meat product in a given jurisdiction; = 0 in all prior years; coded
      separately per jurisdiction (Singapore: December 2020; United States: November
      2022 for UPSIDE Foods FDA no-questions letter; EU: no approval through 2025)"
    source_data_id: D002
    construction: "primary event coding from GFI Global Policy Report (D002) regulatory
      event table across 2019-2024 editions; confirm Singapore SFA first approval
      date from Approved Novel Foods List (D006) — earliest entry dated May 2019
      with cultivated-chicken approval December 2020; confirm US FDA pre-market
      consultation completion dates from FDA database (D003) — UPSIDE Foods November
      16 2022, GOOD Meat March 21 2023; confirm US Federal regulatory notices via
      Federal Register API (D012); code jurisdiction-year binary; where multiple
      clearances occur in one year, record first event date and also construct an
      event_count variable; EU coded 0 throughout sample given no authorization"
    validity_concern: "FDA voluntary pre-market consultation no-questions letters
      are not legally equivalent to Singapore's formal authorization under the Novel
      Food Act, so a single binary treatment conflates distinct regulatory pathways;
      the US has two events in close succession (2022, 2023) creating potential
      interference between treatment doses; donor-country coding for O3 synthetic
      control requires that no spillover from Singapore approval contaminates donor
      investment trends (SUTVA), which is uncertain given global investor attention
      to Singapore as a signal event"
    constructible: yes

  - name: annual_investment
    role: outcome
    definition: "total USD value of investment raised by cultivated-meat firms in
      a jurisdiction (country or US state) in a given calendar year, reported in
      millions USD; for the country-level synthetic control (O3), this is a country-year
      aggregate; for the US state DiD (O1), this is a state-year aggregate constructed
      from firm headquarters location"
    source_data_id: D001
    construction: "extract annual investment series from all available GFI State
      of Industry Reports (D001) 2016-2024; record global aggregates and any jurisdiction-level
      breakdowns reported; for country-level panel, use explicitly reported country
      figures; for state-level panel, assess whether firm profiles in each GFI edition
      include HQ state — if so, aggregate disclosed investment rounds by HQ state
      and year; cross-check global investment totals against AgFunder (D013) for
      series consistency; deflate all USD amounts to constant 2020 USD using US
      CPI; log-transform for regression specifications given the right-skewed distribution
      typical in venture investment data"
    validity_concern: "GFI reports provide global aggregates and firm profiles but
      do not systematically report state-year investment breakdowns; firm HQ state
      is a proxy for investment location and may differ from where facilities or
      employees are concentrated; investment is recorded at fundraising close date,
      which may lag commitment by months; the 40 percent sector-wide decline in
      2024 (P019/D001) reflects global macro conditions that confound state-level
      regulatory effects unless time fixed effects absorb it; country-level panel
      for O3 requires >=3 pre-Singapore years (pre-2020) with non-zero investment
      for >=8 donor countries, which GFI 2016-2019 editions may not consistently
      provide"
    constructible: uncertain

  - name: firm_count
    role: outcome
    definition: "count of active cultivated-meat firms in a jurisdiction in a given
      year, where 'active' means the firm has received investment, announced incorporation,
      or publicly announced operations in that year or any prior year and has not
      announced closure or dissolution; coded as a jurisdiction-year integer count"
    source_data_id: D001
    construction: "compile firm-level profiles from GFI State of Industry Reports
      (D001) across all available editions 2016-2024; for each edition, record firm
      name, HQ country, HQ state (where reported), and any recorded closure announcement;
      merge across editions to build an unbalanced firm-year panel; code active_firm
      = 1 from founding year until last observed year or closure year; aggregate
      to jurisdiction-year count; supplement with EU applicant firm names from EU
      Novel Food Register (D005) and EFSA register (D014) for EU entry counts;
      cross-check against Crunchbase (D008) founding dates where free-tier access
      allows"
    validity_concern: "GFI firm-list coverage is not guaranteed exhaustive or stable
      across editions — firms may be added or dropped based on GFI's own reporting
      criteria rather than actual market entry or exit; state-level location data
      is often absent or approximated in GFI profiles; firm closure is rarely explicitly
      recorded, creating right-censoring in any exit analysis; edition-to-edition
      inconsistency in coverage methodology would introduce measurement error correlated
      with time, threatening DiD validity"
    constructible: uncertain

  - name: bill_text_similarity
    role: moderator
    definition: "cosine similarity score in [0, 1] between the preprocessed full
      text of an enacted US state cultivated-meat ban bill and the full text of Alabama
      SB23 (2024), the first enacted state ban, used as the reference model-legislation
      corpus; states with similarity >= 0.85 are classified as coordinated-diffusion
      adopters; states below the threshold are classified as independently motivated
      adopters; used in O2 as an effect-modifier (subgroup DiD) or instrumental
      variable"
    source_data_id: D007
    construction: "retrieve full-text JSON or PDF of each enacted state ban bill
      from LegiScan API or bulk export (D007); retrieve Alabama SB23 text as reference
      document; apply standard NLP preprocessing — lowercase, punctuation removal,
      stopword removal, TF-IDF vectorization on the unigram and bigram token space;
      compute cosine similarity of each enacted bill to SB23; record raw score and
      binary classification at thresholds 0.75, 0.80, 0.85, 0.90 for sensitivity
      analysis; store scores and classifications in a state-level crosswalk file;
      note that full-text retrieval from LegiScan may require GAITS paid subscription
      for bulk export"
    validity_concern: "cosine similarity is a surface lexical measure that may flag
      shared boilerplate statutory language (e.g. standard agricultural code references)
      rather than intentional model-bill adoption; the threshold of 0.85 is arbitrary
      and results may be sensitive to it; using bill-text similarity as an instrument
      requires the exclusion restriction that national model-bill introduction date
      affects state investment outcomes only through subsequent ban enactment, not
      directly — this assumption is untestable and its plausibility depends on whether
      ALEC membership is independently correlated with state investment climate"
    constructible: uncertain

  - name: public_funding
    role: control
    definition: "total government (public) funding committed to cultivated meat or
      alternative proteins in a jurisdiction in a given calendar year, in millions
      USD; used as a time-varying control to absorb the component of government policy
      that directly injects capital and may independently affect private investment"
    source_data_id: D002
    construction: "extract jurisdiction-year public funding amounts from GFI Global
      Policy Report (D002) editions 2019-2024; GFI reports $523M globally in public
      alt-protein investment in 2023 with country breakdowns for US, EU, Singapore,
      Israel, and others (P023); cross-reference Federal Register API (D012) for
      US federal program announcement dates and amounts; where jurisdiction-year
      breakdown is not reported, code as missing rather than zero; assess whether
      D002 consistently separates cultivated-meat-specific public funding from broader
      alternative-protein funding across editions"
    validity_concern: "GFI Global Policy Report may not provide consistent annual
      jurisdiction-year breakdowns across all editions 2019-2024; aggregate alt-protein
      public funding figures may not be separable into cultivated-meat-specific amounts;
      coding missing as zero conflates absence of funding with absence of reported
      data; public funding commitments may be announced in one year but disbursed
      over multiple years, creating a timing mismatch with the annual panel structure"
    constructible: uncertain

  - name: fda_consultation_complete
    role: treatment
    definition: "binary = 1 for the United States in the calendar year the US FDA
      issues a no-questions letter completing a pre-market consultation for a cultivated-meat
      product (UPSIDE Foods: 2022; GOOD Meat: 2023); = 0 in all prior US years;
      used as a US federal-level regulatory milestone variable supplementing the
      state-level state_ban treatment in O1 and as the primary treatment event for
      US synthetic control comparison in O3"
    source_data_id: D003
    construction: "download the FDA Cultured Animal Cells Pre-Market Consultation
      Database (D003); enumerate all submitted and completed consultations; record
      firm name, product description, submission date, and no-questions letter date;
      as of early 2026 there are two completed consultations — UPSIDE Foods (November
      16 2022) and GOOD Meat (March 21 2023); code the US-year binary = 1 from
      2022 onward; cross-check letter dates against Federal Register API (D012)
      formal notices; supplement with USDA FSIS Inspection Directory (D004) grant-of-inspection
      dates as corroborating milestone for UPSIDE Foods and GOOD Meat"
    validity_concern: "only two completed consultations through 2026 provide negligible
      statistical power for any time-series regression involving this variable alone;
      FDA voluntary no-questions letters are not legally equivalent to Singapore
      SFA formal authorization — treating them as the same treatment type in O3
      cross-jurisdiction comparisons misspecifies the regulatory event; this variable
      is most credible as an event annotation for descriptive event-study plots (O_floor)
      or as a robustness check against the state_ban primary treatment in O1 rather
      than a standalone causal treatment"
    constructible: yes

  - name: state_gdp_food_manuf
    role: control
    definition: "annual real GDP (chained USD) attributed to food manufacturing (NAICS
      311) in each US state, in millions of constant 2017 USD; used as a time-varying
      control in O1 covariate-augmented DiD to absorb incumbent conventional food-industry
      economic weight correlated with state ban adoption (F06); also used to test
      whether pre-ban state GDP growth differs between ban and non-ban states as a
      parallel-trends diagnostic"
    source_data_id: D022
    construction: "download BEA state GDP by industry bulk CSV from the BEA Regional
      Data portal (D022); filter to NAICS 311 (food manufacturing) for all 50 states
      and years 2016-2025; where NAICS 3116 (animal slaughter and processing) is
      separately available as a sub-industry, extract it as a supplementary proxy
      for conventional meat industry weight; merge state-year GDP series with the
      LegiScan ban panel (D007) on state × year key; deflate to constant USD using
      BEA implicit price deflators; log-transform for regression specifications"
    validity_concern: "NAICS 311 food manufacturing is broader than conventional
      meat processing and includes dairy, bakery, beverage, and other sub-industries
      that are not relevant to the cultivated-meat regulatory motivation; the more
      precise NAICS 3116 sub-industry may not be reported for all states in BEA's
      state-level tables; state GDP is an imperfect proxy for conventional-meat-industry
      lobbying power, which would be better measured by livestock value-added (USDA
      NASS) or lobbying expenditure (D016); BEA API key required for programmatic
      access but access itself is confirmed free"
    constructible: yes

  - name: regulatory_quality_index
    role: control
    definition: "World Bank Worldwide Governance Indicators (WGI) regulatory quality
      subscale score for a given country in a given year, ranging from approximately
      -2.5 (weakest) to +2.5 (strongest); used as a time-varying country-level control
      in O3 synthetic control analysis to adjust donor weights for baseline differences
      in regulatory environment quality unrelated to cultivated-meat policy"
    source_data_id: D021
    construction: "query World Bank WDI API (D021) for WGI regulatory quality indicator
      (indicator code RQ.EST or WGI.RQ) for key jurisdictions: US, Singapore, EU
      member states individually (Germany, France, Netherlands as major markets),
      Israel, UK, Australia, and the broader donor-pool candidate set; extract annual
      scores for 2013-2024; merge with country-year investment panel on country ×
      year key; use as a predictor in the synthetic control donor-weight optimization
      alongside pre-treatment investment growth rate"
    validity_concern: "WGI regulatory quality changes slowly (annual revisions are
      modest) and captures broad business-regulation quality rather than food-safety
      regulatory capacity specifically; EU member states have individual WGI scores
      but cultivated-meat regulation is set at the EU level, so Germany or France
      scores introduce measurement error when used as EU proxies; WGI scores for
      small economies (Singapore, Israel) are computed from fewer underlying surveys
      and have wider confidence intervals; the WGI series is available through the
      World Bank DataBank but coverage of 2024 may be one year lagged"
    constructible: yes

  - name: lobbying_expenditure
    role: control
    definition: "annual total federal lobbying expenditure (USD) reported by the National
      Cattlemen's Beef Association (NCBA), National Pork Producers Council (NPPC), and
      National Chicken Council (NCC) combined, from OpenSecrets federal lobbying disclosure
      data; used as a time-varying proxy for incumbent conventional-meat industry political
      pressure on regulators and legislators, testing the Stigler (1971) capture mechanism
      (F01); coded at the US federal level and applied uniformly across all states in a
      given year"
    source_data_id: D016
    construction: "register for free OpenSecrets bulk data access; download federal lobbying
      disclosure CSV records for fiscal years 2018-2026; filter client organization names
      to NCBA, NPPC, and NCC; sum the annual reported lobbying amount across the three
      organizations; search the issue-area text fields of each disclosure for explicit
      mentions of 'cultivated meat', 'cell-based', or 'lab-grown' to identify the year
      when incumbent-industry lobbying first targeted this sector specifically; record
      this targeted-lobbying onset year as a supplementary event marker; link the
      combined annual total to the state-ban panel at the federal level (constant across
      states within a year)"
    validity_concern: "OpenSecrets captures only federal lobbying disclosure filings; state-level
      lobbying by NCBA state affiliates or local cattlemen's associations — which may be
      more directly relevant to state ban adoption than federal lobbying — is governed
      by state disclosure laws that vary widely in completeness and electronic availability;
      the combined three-organization total conflates beef and pork lobbying whose strategic
      priorities diverge; lobbying amounts are the same for all states in a given year,
      providing no within-year cross-state variation and limiting identification power
      in within-state estimators; lobbying expenditure may be endogenous to anticipated
      regulatory action (incumbents ramp up when they perceive threat), creating reverse
      causality between lobbying and ban adoption timing"
    constructible: yes

  - name: regulatory_uncertainty_index
    role: treatment
    definition: "quarterly count-based index of cultivated-meat regulatory events per
      jurisdiction, constructed by aggregating Federal Register notices (D012), LegiScan
      state bill introductions and committee hearing dates (D007), and GFI Global Policy
      Report event dates (D002); a higher index value in a jurisdiction-quarter signals
      greater policy activity and hence greater regulatory uncertainty for that
      jurisdiction during that period; used as the primary exposure variable in Design O4
      and as a time-varying covariate in O1 supplementary specifications"
    source_data_id: D012
    construction: "query Federal Register API (D012) for all FDA CFSAN and USDA-FSIS
      documents mentioning 'cultivated meat', 'cell-cultured', or 'lab-grown meat'
      from 2018 to 2026; extract document type (proposed rule, final rule, guidance,
      notice), publication date, docket number, and agency; query LegiScan (D007)
      for all cultivated-meat bill introduction dates and committee hearing dates
      across all states and years; merge with GFI D002 policy event table; assign
      each event to a jurisdiction-quarter cell; aggregate event counts by jurisdiction
      and quarter; apply optional severity weighting (ban enactment > bill passage >
      committee hearing > Federal Register notice > bill introduction); lag index by
      one quarter in panel regressions to reduce reverse-causality bias; winsorize
      top 1 percent of jurisdiction-quarter counts to limit influence of legislative
      session spikes"
    validity_concern: "the index conflates uncertainty-increasing events (bill introduction,
      proposed rules) with uncertainty-resolving events (final rules, withdrawals) by
      treating all regulatory activity as symmetrically uncertainty-raising; severity
      weights are analytically arbitrary and not derived from theory; legislative calendar
      clustering artificially concentrates index values in Q1-Q2 of each year, potentially
      biasing within-year seasonal variation; the index is endogenous to the investment
      environment — high investment interest attracts legislative scrutiny and FDA review
      requests — making causal identification impossible without a credible instrument
      for regulatory attention; the index spans multiple data sources (D012, D007, D002)
      each with distinct access procedures, requiring three simultaneous intake pipelines
      to be operational before construction can begin; O4 max_claim is therefore
      associational regardless of index quality"
    constructible: uncertain
---

# Variable Construction: Cultivated Meat Policy Database

This document specifies how each key variable required by the candidate research designs
(O1–O_floor in `discovery/design_options.md`) is constructed from identified data sources
in `discovery/data_inventory.csv`. Constructibility flags reflect honest assessment of
whether the named source plausibly delivers the variable as specified; `uncertain` means
the construction is technically plausible but depends on data characteristics that cannot
be confirmed without hands-on access.

---

## state_ban

**Design use:** Primary treatment in O1 (Staggered DiD on state ban timing) and the
moderating covariate in O2 (bill-text diffusion analysis).

**Unit:** US state × calendar year binary indicator.

The treatment variable is a binary flag equal to one in the year a US state enacts a
cultivated-meat production or sale ban and in all subsequent years, and zero before
enactment or for states that never enact a ban. Construction proceeds from LegiScan
(D007), which provides a fulltext-searchable database of US state bills with bill numbers,
introduction dates, passage dates, and governor action dates. At least five states enacted
bans beginning in 2024 — Alabama (SB23), Florida (SB1084), Tennessee, Iowa, and Idaho —
providing the minimum staggered adoption structure that O1 requires.

The main construction challenge is that LegiScan's free API tier imposes rate limits and
does not guarantee programmatic access to the full population of relevant bills without
a paid GAITS subscription. Individual state legislature websites provide corroborating
passage dates for confirmed ban states and serve as a free backup. The GFI Global Policy
Report (D002) tracks enacted bans at the jurisdiction level and provides a cross-check.

A critical coding decision is the distinction between production bans (manufacturing is
prohibited), sale-only bans (selling to consumers is prohibited but manufacturing is not),
and labeling-only rules (no prohibition, only terminology restrictions). Conflating these
under one binary overstates treatment homogeneity. The construction must code a supplementary
`policy_type` categorical alongside the binary. The `uncertain` flag reflects (a) the
LegiScan access uncertainty and (b) the possibility that bills still moving through
committees as of the extraction date will be missing and must be coded as missing rather
than zero.

---

## national_approval_event

**Design use:** Primary treatment in O3 (Synthetic control for national approval events)
and a regulatory milestone annotation in O_floor (Descriptive event-study).

**Unit:** Jurisdiction × calendar year binary indicator.

The treatment variable flags the year in which a national food regulatory authority grants
the first formal market authorization or regulatory clearance for a cultivated-meat product
in a jurisdiction. Established events are Singapore SFA December 2020 (confirmed in D006,
with 14+ approved products as of March 2026), and US FDA no-questions letters for UPSIDE
Foods (November 2022) and GOOD Meat (March 2023) (confirmed in D003). The EU has no
authorization through 2025 and is coded zero throughout the sample.

Construction is reliable because these events are documented in multiple overlapping sources
(D002, D003, D006, D012), are publicly announced with clear dates, and are not subject to
data access barriers. The `yes` constructibility flag reflects this redundancy and
documentation clarity. The primary validity concern is not about data access but about
conceptual validity: FDA voluntary no-questions letters differ legally from Singapore's
mandatory authorization, so a single binary pools structurally distinct regulatory actions.
Researchers using O3 should assess whether a pooled binary or separate jurisdiction-specific
indicators better map to the theoretical mechanism being tested.

---

## annual_investment

**Design use:** Primary outcome in O1 (state-level DiD), O3 (synthetic control
counterfactual), and O_floor (descriptive event-study plots).

**Unit:** Jurisdiction × calendar year, in millions USD (constant 2020 USD).

Annual investment raised by cultivated-meat firms is the central economic outcome of
interest across all candidate designs. GFI State of Industry Reports (D001) are the
primary source, providing a global investment series running from 2013 (cumulative) and
from approximately 2016 annually. The 2022 edition (P013), 2023 edition (P012), and
2024 edition (P019) are confirmed as publicly available; earlier editions require
verification.

The construction faces two unresolved structural challenges that drive the `uncertain`
constructibility flag. First, for O3 (country-level synthetic control), the donor pool
requires that >=8 countries have non-zero investment data for at least three pre-Singapore
years (2017-2019), but GFI reports from that period may report only global aggregates
rather than country-level breakdowns. Second, and more critically for O1, the staggered
DiD design requires *state-year* investment variation within the United States. GFI reports
typically present global aggregates and occasionally firm-level profiles; they do not
systematically report investment by US state. If firm profiles in GFI editions include
headquarters state, investment can be aggregated to state-year cells using HQ location
as a proxy — but coverage gaps, inconsistent firm-list composition across editions, and
the gap between firm location and investment activity location all introduce measurement
error. Until GFI editions are downloaded and inspected (engineering_status: not_started
in D001), it is unknown whether the state-year investment panel can be constructed from
D001 alone. If it cannot, O1 would require supplementation from Crunchbase (D008) or
PitchBook (D010), neither of which has verified access. This is the binding data risk
for O1 viability.

---

## firm_count

**Design use:** Secondary outcome in O1 (measuring firm entry/exit in response to state
bans) and descriptive count in O_floor.

**Unit:** Jurisdiction × calendar year count of active firms.

Firm count is the number of active cultivated-meat firms in a jurisdiction in a given
year. GFI State of Industry Reports (D001) include company profiles and active firm counts
as headline statistics. Construction requires compiling firm-level profiles across all
available editions (2016-2024), recording firm name, headquarters country, headquarters
state where available, and any closure announcement, then aggregating to jurisdiction-year
active counts.

The `uncertain` constructibility flag reflects several issues. GFI's firm-list methodology
is not guaranteed to be consistent across editions — firms may enter or exit the GFI
tracking list for reporting reasons unrelated to actual market entry or exit. State-level
HQ data is frequently absent or approximated in firm profiles. Firm closure is rarely
explicitly recorded (firms more often become inactive quietly), creating right-censoring
that biases firm-count series upward over time. For the EU, D005 (EC Novel Food Register)
and D014 (EFSA register) provide applicant firm names as a partial proxy for EU market
entry attempts, but these capture only firms that progressed to formal application —
not all entrants. Despite these issues, the global firm count series from D001 is likely
reliable enough for O_floor descriptive use; the state-year disaggregation for O1 is
the structural barrier.

---

## bill_text_similarity

**Design use:** Moderator and potential instrument in O2 (Bill-text cosine-similarity /
model-legislation diffusion analysis).

**Unit:** US state (cross-sectional score for each enacted ban state).

This variable measures the textual proximity of each enacted state ban bill to Alabama
SB23, the first enacted US cultivated-meat ban (2024), operationalized as a cosine
similarity score computed on TF-IDF-weighted token vectors. High similarity (>=0.85)
classifies a state as a coordinated-diffusion adopter — one whose legislature copy-pasted
or lightly adapted the model-legislation template rather than drafting independently.
This classification drives the O2 mechanism analysis: coordinated adopters' ban timing
reflects a national template-introduction shock rather than local economic conditions,
partially restoring quasi-random variation in treatment timing for that subset.

Constructibility is `uncertain` for two reasons. First, full-text retrieval from LegiScan
(D007) at scale requires either the paid GAITS bulk-export subscription or careful use
of the free JSON API across all enacted ban states, which may be feasible but is not
confirmed. Second, the cosine-similarity instrument's identifying assumption — that
Alabama SB23's introduction date in the national legislative calendar affects investment
outcomes only through subsequent state ban enactment, not directly — is untestable
and its plausibility is contested. The variable is scientifically important for addressing
F06 but faces both data-access and conceptual-validity barriers.

---

## public_funding

**Design use:** Time-varying control in O1 (covariate-augmented DiD) and contextual
variable in O_floor (regulatory timeline figure).

**Unit:** Jurisdiction × calendar year, in millions USD.

Public funding captures government grants, subsidies, and investment programs directed
at cultivated meat or alternative proteins in a jurisdiction and year. It is included as
a control to absorb the direct government-investment channel that may confound private
investment outcomes: a state or country with active public funding may attract private
co-investment regardless of its regulatory posture. GFI Global Policy Report (D002)
reports $523M globally in public alt-protein investment in 2023 with country-level
breakdowns for major jurisdictions.

Constructibility is `uncertain` because (a) the 2019-2024 D002 editions have not been
downloaded and their internal consistency on jurisdiction-year public funding breakdowns
is unverified, (b) GFI alt-protein funding figures aggregate cultivated meat with
plant-based and fermentation categories, so a cultivated-meat-specific public funding
variable may not be separately extractable, and (c) coding jurisdictions without reported
funding as zero conflates genuine zero-funding with missing data — a source of attenuation
bias if missingness is non-random.

---

## fda_consultation_complete

**Design use:** US federal-level treatment milestone in O1 (robustness check) and
event annotation in O_floor; contributes one data point to O3 US synthetic control
treatment series.

**Unit:** US jurisdiction × calendar year binary indicator.

This variable flags the years in which FDA issues no-questions letters completing
pre-market consultations for cultivated-meat products. It captures the US federal
regulatory signal distinct from state-level ban variation. The FDA Cultured Animal Cells
Pre-Market Consultation Database (D003) is a public web catalogue with two confirmed
completions through early 2026: UPSIDE Foods (November 16 2022) and GOOD Meat
(March 21 2023).

Constructibility is `yes` because the event dates are publicly confirmed in D003, the
FDA database URL is verified, and the N is small enough (two events) that manual
extraction requires no automated pipeline. The validity concern is not constructibility
but statistical power and conceptual scope: two events in the US over a two-year window
cannot support a standalone regression analysis. This variable functions best as a
supplementary event marker for descriptive plots, a robustness check in O1 (do results
change when the federal consultation year is controlled?), and a milestone timestamp for
the O3 US synthetic control. Researchers should not treat it as a primary treatment
variable in any causal specification.

---

## state_gdp_food_manuf

**Design use:** Time-varying covariate in O1 (covariate-augmented DiD, Sant'Anna-Zhao
doubly robust estimator) for controlling incumbent food-industry economic confounders
correlated with state ban adoption (F06 threat).

**Unit:** US state × calendar year, millions of chained 2017 USD.

State-level food manufacturing GDP (NAICS 311) is the primary observable proxy for
incumbent conventional food-industry economic weight in O1's F06 response strategy.
Design O1 explicitly identifies "annual beef output" and "state GDP" as covariates
needed for the doubly robust DiD estimator. BEA state GDP by industry (D022) provides
the most systematic and complete source: bulk CSV downloads from the BEA Regional Data
portal cover all 50 states for 1997-2025 at the industry level, and the portal is
confirmed accessible with no subscription requirement (API key is free).

Constructibility is `yes` because D022's access is confirmed, the data structure is
documented, and the merge key (state × year) is straightforward. The main caveat is
precision: NAICS 311 is broader than livestock slaughter (NAICS 3116), which would be
a tighter proxy for the conventional beef and pork industry that F06 implicates. If
BEA's state-level tables do not report NAICS 3116 separately, the researcher should
supplement with USDA NASS livestock value-added data or use D016 (federal lobbying
expenditures by NCBA/NCC/NPPC) as an alternative proxy that more directly captures
incumbent-industry political mobilization.

---

## regulatory_quality_index

**Design use:** Country-level predictor variable in O3 synthetic control donor-weight
optimization; robustness control to rule out the alternative hypothesis that investment
differences across jurisdictions reflect general regulatory environment quality rather
than cultivated-meat-specific policy.

**Unit:** Country × calendar year continuous score (approximately -2.5 to +2.5).

The World Bank Worldwide Governance Indicators regulatory quality subscale (RQ.EST) is
the most widely used cross-national regulatory environment measure in empirical regulatory
economics. For O3, it serves two roles: as a matching predictor in the synthetic control
donor-weight computation (so that Singapore's synthetic counterfactual draws on countries
with similar regulatory capacity, not just similar investment trajectories) and as a
robustness control in cross-jurisdiction regressions testing whether WGI regulatory
quality mediates the investment effects estimated elsewhere.

Constructibility is `yes` because the WDI API is publicly documented, requires no
registration, and provides data for all key jurisdictions through at least 2023. The
validity concern is the mismatch between WGI's broad regulatory quality concept and
the narrow food-safety regulatory process relevant to cultivated meat specifically:
a high WGI regulatory quality score reflects a general business-friendly regulatory
environment, not specifically a fast or permissive novel-food approval pathway. Researchers
should consider pairing this variable with D005 (EU Novel Food application processing
duration) or D003/D006 (approval timeline days) for a domain-specific regulatory-process
quality proxy when the O3 mechanism argument requires it.

---

## lobbying_expenditure

**Design use:** Time-varying control in O1 (covariate-augmented DiD) and O4 (regulatory
uncertainty panel regression) for testing and absorbing the Stigler (1971) regulatory
capture mechanism (F01); required as an explicit control in design options O1 and O4
candidate data tables.

**Unit:** US federal annual total, in USD (same value applied to all states in each year).

Federal lobbying expenditures by the three major US conventional-meat industry trade
associations — NCBA, NPPC, and NCC — proxy the political mobilization capacity of the
incumbent industry predicted by Stigler's capture theory to precede and explain state
ban adoption. If lobbying expenditure by these organizations rises in years just before
state ban enactment, and if states where these organizations lobby most heavily are more
likely to enact bans, the pattern is consistent with the F01 capture mechanism rather
than a food-safety motivation.

OpenSecrets (D016) provides federal lobbying disclosure records compiled from FARA and
LDA filings. Bulk data CSV downloads are available at no cost after free account
registration, confirmed accessible. The construction is straightforward: filter to three
named client organizations across 2018–2026, sum annual amounts, and merge with the
state-ban panel as a federal-year control.

Constructibility is `yes` because D016's bulk access is confirmed, the target organizations
(NCBA, NPPC, NCC) are identifiable by name in the client field, and the aggregation
is simple arithmetic. The binding limitation is that federal lobbying is a single
time-series without state-level variation, so it cannot explain which states adopted
bans earlier than others within a legislative wave — only whether incumbent pressure
was nationally rising. For state-specific variation, researchers should investigate
state-level lobbying disclosure databases, though these vary widely in availability
and electronic accessibility across the 50 states.

---

## regulatory_uncertainty_index

**Design use:** Primary exposure variable in O4 (Regulatory-uncertainty index and
investment panel); secondary covariate in O1 supplementary specifications testing
whether pre-ban legislative activity predicts investment declines before formal enactment.

**Unit:** Jurisdiction × calendar quarter count index (lagged one quarter in regressions).

The regulatory uncertainty index operationalizes the Dixit-Pindyck (1994) real-options
prediction (F03) that periods of heightened regulatory ambiguity should suppress
irreversible firm investment. Construction requires merging three event streams: Federal
Register notices from FDA CFSAN and USDA-FSIS (D012), state bill introduction and
committee hearing dates from LegiScan (D007), and cross-jurisdiction policy events
from GFI Global Policy Report (D002). Each event is assigned to a jurisdiction-quarter
cell and the counts are aggregated to form the index.

Constructibility is `uncertain` for compounding reasons. First, the index spans three
distinct data sources, each requiring its own access and extraction pipeline; all three
must be operational simultaneously before construction can begin. Second, the aggregation
method involves arbitrary choices — whether to weight event types by severity, how to
define the jurisdiction boundary for federal events that apply nationally, and how to
handle events in the same jurisdiction-quarter that cut in opposite directions (e.g.,
a bill introduction raising uncertainty in the same quarter as a regulatory guidance
reducing it). Third, the Federal Register API is the most reliable of the three sources
(free, well-documented, no rate-limit barriers for reasonable query volumes), but D007
full-text access for bill hearing dates may face the same GAITS subscription constraint
as noted under `bill_text_similarity`. Fourth, and most important for claim level: the
index is endogenous to the investment environment. Legislators scrutinize sectors that
attract large capital inflows; FDA review timelines respond to firm application activity;
both are driven by the same underlying forces as private investment. The associational
max_claim for O4 is therefore a hard ceiling regardless of how carefully the index is
constructed.
