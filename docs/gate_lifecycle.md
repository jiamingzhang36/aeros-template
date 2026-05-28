# Gate-Based Empirical Research Lifecycle

Each gate has inputs, allowed actions, forbidden actions, required checks, outputs, and a human decision when research judgment is affected.

## G0 Project Intake

Clarify project type, contribution type, current phase, missing files, and safest next task.

## G1 Data Readiness

Audit data sources, units, keys, missingness, duplicates, coverage, and measurement feasibility.

## G2 Measurement / Variable Construction

Audit coding protocols, variable construction, schemas, validation samples, and measurement reliability.

## G3 Research Design

Audit whether the research question, estimand, data, assumptions, and supportable claim type align.

## G4 Main Estimation

Run or audit the preferred model against `docs/method_card.md` and `docs/protected_definitions.yml`.

## G5 Robustness

Run only robustness checks listed in `docs/robustness_checklist.md`; do not promote robustness results to the main model without human approval.

## G6 Result Validation

Check manuscript numbers, signs, units, standard errors, sample sizes, table notes, and figure labels against outputs.

## G7 Claim Audit

Check every major claim against `evidence/claim_registry.md`, `docs/language_constraints.md`, and the evidence ledger.

## G8 Referee Simulation

Generate structured objections from methods, domain, policy, and skeptical-editor perspectives.

## G9 Replication Package

Verify data instructions, environment, code, outputs, paper links, and replication README.
