---
status: filled
task_id: T006_referee_panel
gate: G8
reviewed_at: 2026-06-15
claim_ids_covered:
  - C001
  - C002
  - C003
  - C004
---
# Referee Panel Report

## Scope

This report simulates adversarial objections after the design, result-validation,
and claim-audit gates. It does not rewrite the manuscript, change claims, alter
methods, or accept/reject objections on behalf of the author.

## Panel Verdict

The wrapper's active claims C001--C004 are defensible only as bounded
descriptive/associational claims. The strongest version remains a policy-rule
measurement and ex-ante exposure paper, not a causal approval, demand, welfare,
or health-effects paper.

## Referee 1: Methods / Identification

### Objection M1: C002 could be read as causal federal selection.

Concern: The approval-risk concentration claim may invite readers to interpret
governor party as an exogenous treatment.

Why it matters: State demand, request timing, proposal quality, federal
priorities, and coalition alignment are jointly selected.

Current defense: The claim registry labels C002 associational and states that
governor party and covariates are benchmark partitions, not exogenous
treatments.

Response option: Keep exact approval concentration as descriptive evidence.
Avoid causal language such as "caused approval" or "USDA favored Republican
governors." Use "concentrated among" or "associated with."

Claim coverage: C002.

### Objection M2: C003 exposure could be mistaken for a purchase response.

Concern: Ex-ante exposure shares may be interpreted as expected consumption
reductions.

Why it matters: The current NielsenIQ window is pre-policy and lacks actual
SNAP/EBT tender.

Current defense: C003 explicitly says exposure is over low-income proxy
purchases, not actual SNAP/EBT transactions or post-policy responses.

Response option: Continue to state "would cover" and "pre-policy exposure";
reserve "effect," "response," and "elasticity" for future post-implementation
designs.

Claim coverage: C003.

## Referee 2: Data / Measurement

### Objection D1: C001 rests on author-coded policy taxonomy.

Concern: Policy-rule measurement can be attacked as subjective if second-coder
reliability is missing.

Why it matters: The taxonomy is a central contribution; measurement error could
alter design ranks and downstream exposure interpretation.

Current defense: Result R001 is document-linked, deterministic at the wrapper
level, and bounded as descriptive measurement.

Response option: Treat MG human second-coder reliability as a submission-grade
blocker for strong taxonomy claims. LLM/source-review validation can remain
auxiliary only.

Claim coverage: C001.

### Objection D2: C003 depends on scanner-category mapping and Nielsen coverage.

Concern: Broad/taxable/residual categories and missing Hawaii could alter
approved-state exposure statements.

Why it matters: Hidden category choices can shift headline exposure, especially
for broad processed/taxable food language.

Current defense: C003 states Hawaii is excluded from current approved-state
Nielsen claims and that exposure is aggregate/proxy based.

Response option: Retain strict/broad bounds, explicit 21/22 coverage, and no
actual SNAP/EBT language. Report controlled-DuckDB uncertainty intervals when
available.

Claim coverage: C003.

## Referee 3: Policy / Institutional Fit

### Objection P1: Approval is not implementation.

Concern: Readers may treat public USDA approval as realized checkout/POS
restriction.

Why it matters: Target implementation, retailer readiness, modification, and
litigation are separate administrative margins.

Current defense: C004 exists specifically to preserve target-implementation,
SNAP/EBT, and ambiguity boundaries.

Response option: Keep "target/planned implementation" wording unless actual
rollout is verified. Do not infer realized retailer compliance from approval.

Claim coverage: C004.

### Objection P2: The paper may look like a policy-description report rather
than economics.

Concern: Descriptive measurement can be seen as insufficient if not tied to
economic objects.

Why it matters: Journal fit depends on whether policy heterogeneity and exposure
are framed as in-kind transfer design and incidence/bindingness objects.

Current defense: The method card frames the paper around a linked measurement
object: policy rules, approval-risk progression, and ex-ante purchase-basket
exposure.

Response option: Keep the economic framing around in-kind benefit design,
administrative selection, and ex-ante incidence; do not overcorrect by adding an
unsupported demand model.

Claim coverage: C001, C003, C004.

## Referee 4: Skeptical Editor

### Objection E1: The paper may overstate readiness despite remaining blockers.

Concern: G7 claim discipline does not close MG reliability, controlled Nielsen
uncertainty intervals, journal formatting, or restricted-data release language.

Why it matters: Gate approval could be misunderstood as journal readiness.

Current defense: The claim registry and method card are bounded, and this
wrapper has not changed the canonical manuscript or empirical outputs.

Response option: State that AEROS G7 approval would approve claim boundaries
only, not the final submission package.

Claim coverage: C001, C002, C003, C004.

### Objection E2: The wrapper has no full paper draft under `paper/`.

Concern: AEROS validates wrapper claims/provenance, not the canonical MAHA
manuscript text.

Why it matters: Text-level overclaim risks can still exist outside the wrapper
unless the canonical manuscript is audited separately.

Current defense: The wrapper records that it is smoke/provenance validation and
does not alter the source manuscript.

Response option: Before submission, run a paper-package or pre-submission audit
against the canonical manuscript files in the MAHA source repository.

Claim coverage: C001, C002, C003, C004.

## Summary of Highest-Risk Remaining Issues

1. MG human second-coder reliability remains the largest submission-grade
   measurement blocker for C001.
2. Controlled NielsenIQ household-cluster uncertainty intervals remain open for
   precise C003 exposure estimates.
3. The wrapper validates claim/provenance boundaries, not the final canonical
   manuscript wording.
4. C002 must remain associational and federal-side endogenous.

## Recommended Response Strategy

Proceed with G8 only if the human reviewer accepts this adversarial framing.
Approval should mean "the current objection set is documented," not "the paper
is submission-ready."
