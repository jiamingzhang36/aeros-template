# Campaign Circuit Breaker (the direction governor)

**Purpose.** Stop an autonomous loop from grinding a repeated same-lane task at
the *execution entrypoint* — not just detect that it should stop. This is the
propulsion-side counterpart to the gate/claim guards: gates stop unsafe *claims*;
the campaign breaker stops unproductive *effort*. It is deterministic and
advisory about direction; it never approves claims, gates, or releases.

Code: `aeros/runtime/campaign.py` (logic), `aeros/runtime/task_preflight.py`
(enforcement), `aeros/runtime/completion.py` (progress recording),
`aeros/cli.py` (`aeros campaign …`). Tests: `checks/check_campaign_contract.py`
(units) and `checks/check_campaign_e2e.py` (full lifecycle).

## Lifecycle

```
aeros campaign new                     # scaffold campaigns/active_campaign.yml
   → task completion (completion.py)   # auto-records one evidence-anchored progress row
   → task preflight (task_preflight)   # calls assess_campaign, scoped to the task's campaign
   → any breaker trips → status BLOCKED + needs_human_decision + escalation packet
   → aeros run enforces the block before doing work
   → aeros campaign continue|stop      # human's answer, consumed by assess_campaign
```

## Contract (`campaigns/active_campaign.yml`)

| field | meaning |
|---|---|
| `campaign_id`, `work_lane` | identity + lane the campaign owns |
| `objective_metric`, `binding_constraint` | what is being grown; the one constraint tasks must target |
| `task_budget`, `expected_yield_per_task`, `marginal_yield_window` | budget + the yield floor over a sliding window |
| `objective_markers` | owner phrases that mark same-campaign intent |
| `objective_outputs`, `objective_task_types` | phrasing-independent scope: output path classes / task modes the campaign owns |
| `convergence_window`, `convergence_epsilon` | FREEZE: window + tolerance for a "results stable" plateau |
| `stop_condition`, `stop_condition_met` | the decision-relevant win condition |

## Breakers (`assess_campaign`)

Stall signals (block, "reconsider"): `low_marginal_yield`, `task_budget_exhausted`,
`binding_constraint_drift`, `batch_source_unused`, `collecting_without_testing`.

Convergence signal (block, "finalize"): **`convergence_freeze`** — the objective
metric held within `convergence_epsilon` across the last `convergence_window`
tasks (with enough tasks run). The positive counterpart: stop *expanding* and
request a human finalize decision, rather than grinding.

## Scope matching — why rewording cannot dodge a stopped campaign

`match_campaign_scope` decides whether an *undeclared* task is really the same
campaign work. A task in the campaign's lane is in scope if **any** of:

1. **markers** — intent/goal contains an `objective_marker`;
2. **outputs** — the task writes into an `objective_outputs` class;
3. **task type** — the task's mode is an `objective_task_types` member;
4. **inferred outputs** — `infer_campaign_output_classes` learns the campaign's
   real output footprint from the contracts of tasks that already recorded
   progress (excluding generic scaffolding dirs), so it works even when nothing
   was declared.

In preflight this yields `UNDECLARED_CAMPAIGN_SCOPE` (omitted `campaign_id`) or
`CAMPAIGN_SCOPE_COLLISION` (a different `campaign_id`, same lane/scope) → BLOCKED.
Genuinely unrelated lanes/outputs stay `TASK_NOT_IN_CAMPAIGN` (no over-block).
**Residual (by design):** a fully reworded task writing to a novel output class
the campaign has never used can still pass — closing that needs semantic intent
understanding, which is out of scope for a deterministic guard.

## Human release valve (`campaigns/campaign_decisions.yml`)

The escalation is the *question*; a recorded decision is the *answer*, consumed
by `assess_campaign`:

- **`aeros campaign continue --breaker <id|all> --for-tasks N --reason …`**
  releases the named breaker for the next `N` tasks, then it **re-arms** so the
  human must re-review. Bounded, not a permanent override.
- **`aeros campaign stop --reason …`** halts the campaign (`human_stop` breaker,
  `campaign_halted: true`).

Never hand-edit `stop_condition_met`/`task_budget` to "continue" — that
misstates semantics; use the decision record.

## Metric integrity (`record_campaign_progress`)

Metrics are task-declared but anchored: `metric_evidence_path` must exist and be
inside the task's `allowed_outputs`. **Anti-inflation:** a claimed positive
integer gain must be backed by at least that many data rows in the evidence file
(a task cannot report +100 while pointing at a 2-row file). A **zero-gain task**
("found nothing new") is legitimate — it is the diminishing-returns signal the
breakers need — and records with empty/header-only evidence. (This exact case was
missed by unit fixtures and caught by `check_campaign_e2e.py`; keep that test.)

## Boundaries (does not prove)

Convergence/yield thresholds are not scientifically validated; a fractional/rate
metric is only checked for non-emptiness; a recorded human decision is not
guaranteed wise; scope inference is incomplete when task contracts are archived.
The breaker governs *direction and effort*, never scientific validity, claim
support, or gate approval.
