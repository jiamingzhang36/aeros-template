# Design Proposal: Claim Falsification Engine

**Status: DESIGN PROPOSAL — NOT IMPLEMENTED.** This changes claim-ceiling semantics
(high-risk), so it is a proposal for human review, not a built feature. Do not cite
it as an AEROS capability until implemented and validated.

## Motivation

- **Borrowed from AIGS (arXiv 2411.11910, full-text card L2):** falsification (Popper)
  should be an *active engine*, not a passive checklist. AIGS runs a FalsificationAgent
  (ablation-driven) that attacks hypotheses.
- **Proven manually this session:** the 2026-06-20 referee pressure-test (R1–R7 on
  CMPD's C1/C2) was a hand-run version. It attacked the headline claims and found the
  real caveats (R5 timing split, R6 multiple comparison) that the existing *passive*
  `T006_referee_panel` (wording-only, never opened the data) missed.
- **Gap:** AEROS already has the *parts* (negative_result_ledger, placebo skill,
  robustness_suite, spec_run_index) but they are passive and not claim-targeted, and
  nothing feeds "how hard was this claim attacked" into the claim ceiling.

## Core idea

Given a registered `claim_id`, the engine (1) derives a **claim-type-aware attack
battery**, (2) runs each attack as a registered spec run reusing the project's own
estimation code, (3) computes an **attack-survival profile**, and (4) emits a
**claim-ceiling recommendation** + registered artifacts. It never edits the protected
claim registry — a human gate applies any ceiling change.

```
claim_id ──> attack plan ──> spec runs (all registered) ──> survival profile ──> ceiling RECOMMENDATION
                                   │                                                  │
                            result_index / negative_result_ledger             human gate applies (or not)
```

## Lane & placement

- **Runs in the `analysis` lane** (it executes estimations), **feeds the `claim`
  lane** (ceiling recommendation).
- New task type **`FALSIFY <claim_id>`**; gate **G7/G8** (claim audit / referee).
- `automation_class: auto_rerunnable` for local-data attacks; **any ceiling RAISE or
  claim release stays `approval_required` (human gate)**.
- **Supersedes the empirical half of `T006_referee_panel`** (which stays for
  wording/scope discipline).

## Attack battery by claim type (the typed core)

| claim type | attacks the engine runs |
|---|---|
| descriptive | recount under alt definitions; coverage/missingness sensitivity; denominator checks |
| associational | leave-one-cluster-out; alt controls + Oster δ on the **focal** var; few-cluster wild bootstrap; permutation/randomization; multiverse/spec curve; temporal & outcome placebo |
| causal | all associational attacks + parallel-trends/pre-trends, exclusion-restriction probes, sensitivity (Oster/Rosenbaum), alternative identification, anticipation/spillover checks |
| mechanism | mediation robustness; alternative-channel horse races; placebo mechanism |

The battery is derived from the claim's **type + scope vector** (geography/time/unit/
population), reusing `claim_toulmin_schema.yml`, `estimand_card.yml`, and
`identification_gate.yml`. (CMPD C1 already exercised the associational row by hand:
LOO=R_REAL_029, Oster/year-FE=R_REAL_027, wild-bootstrap=R_REAL_028.)

## Reuse map (build ON existing, don't duplicate)

| need | existing AEROS piece |
|---|---|
| register every attack run (incl. survived & failed) | `analysis/spec_run_index.csv` |
| register each attack's output as an artifact | `evidence/result_index.csv` (+ provenance + graph) |
| record attacks that overturn/weaken | `templates/negative_result_ledger.csv` |
| compute the ceiling | `harness/claim_toulmin_schema.yml`, `admissibility_matrix.yml`, `scope_calculus.yml` |
| separate attacker from author | critic protocol (critic ≠ worker) |
| record the run honestly | action receipt |
| seed implementation | `code/27_referee_robustness.py` (CMPD prototype) |

## Attack-survival → ceiling (the new logic)

Per attack, define **survival** (e.g., sign-stable AND p<.05; magnitude within band).
Aggregate to a profile, then a typed rule, e.g.:
- survives all → ceiling holds; "strongest/robust" language admissible.
- survives most, fails k → ceiling **forced down** within type (e.g. "strongest
  correlate" → "most consistently signed"), with the failing attacks named.
- overturned by a core attack → claim flagged `unsupported/ambiguous`; result → negative
  ledger.

Output is a **recommendation with the full attack denominator attached**, not a single
score. The human gate decides.

## Anti-Goodhart safeguards (borrowed warning, L4 creativity survey)

L4 (full-text, lines 813–816): automated evaluators get **reward-hacked** — optimizing
toward an auto-reviewer yields "high-scoring but wrong." Therefore:
1. The engine's output is **registered negative/robustness artifacts + a ceiling
   recommendation**, never a pass/fail score the worker optimizes toward.
2. **Full attack denominator is registered** (spec_run_index requires *all* runs) — no
   cherry-picking which attacks to report.
3. Attacker ≠ the worker that produced the claim.
4. Any ceiling **raise** or claim release still needs the **human gate** — the engine
   can only *lower or hold* autonomously; raising is human.

## What is genuinely new vs activating existing

- **New:** claim-targeted *active* attack generation; attack-survival → ceiling rule;
  the engine as a task type.
- **Activating existing (passive→active):** robustness_suite, placebo, negative ledger,
  spec_run_index already exist but are invoked ad hoc; this orchestrates and claim-binds
  them.

## Self-metric (ties to the "AEROS has no metric" gap, HLER borrow)

The engine naturally yields AEROS's first real self-metrics: **claim-survival rate**
(% of registered claims whose ceiling held under attack), **attack denominator per
claim**, **overturn rate**. Track these in a `harness/falsification_metrics.csv`.

## Phased implementation (if approved)

1. **P0 (low risk):** generalize `27_referee_robustness.py` into a `falsify <claim_id>`
   runner for the *associational* battery; register runs + emit a report; recommend
   only (no ceiling change). Validate on CMPD C1/C2.
2. **P1:** wire survival profile into the claim-ceiling compiler as a *recommendation*
   input; negative-ledger integration; metrics file.
3. **P2:** causal/mechanism batteries; identification-gate coupling; promote into the
   kernel as a transition input (not a new parallel layer — Kernel Anti-Creep).

## Risks / non-goals

- **Not** a truth oracle; surviving attacks ≠ true (L2 AIGS is itself "baby-step").
- Could ossify into a fixed battery that claims learn to pass — mitigated by keeping
  the battery typed/extensible and the human gate for raises.
- Does not replace human judgment, identification gates, or peer review.

## Relation to T006_referee_panel

T006 stays for *wording/scope/ceiling-discipline* (the defensive half). This engine
takes over the *empirical attack* half that T006 never actually ran.
