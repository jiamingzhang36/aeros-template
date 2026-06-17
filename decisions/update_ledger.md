# AEROS Update Ledger

Purpose: track every meaningful AEROS template update against the project north star so drift is visible early.

North star:

```text
AEROS should automate low-risk research progress, preserve artifact lineage, enforce claim boundaries, and keep human judgment at high-risk exits.
```

How to read this ledger:

- `Alignment`: why the update moves AEROS toward the north star.
- `Non-goal`: what the update explicitly does not claim to solve.
- `Drift risk`: how this could become overbuilt, bureaucratic, or misleading.
- `Next check`: what should be watched in the next real project run.

## 2026-06-16

### 2026-06-16 — Kernel / Research CI

**Commit(s)**: `9ac6cfe`

**Action**: Added the formal research CI kernel, data-first layer, action receipts, global state view, event replay scaffolding, and adversarial kernel tests.

**Alignment**: Moves AEROS away from trusting agent self-reports and toward artifact/event/receipt-grounded progress.

**Non-goal**: Does not prove research conclusions are true or automate all empirical judgment.

**Drift risk**: Kernel could creep into a central scientific judge if future rules mix process legality with epistemic truth.

**Next check**: Keep kernel enforcement mechanical; put judgment in compilers, reviewers, and human gates.

### 2026-06-16 — Event Sourcing / Scope Discipline

**Commit(s)**: `bc0791f`

**Action**: Tightened event sourcing with hash-chain fields, replay checks, constitutional invariants, and scope calculus.

**Alignment**: Makes progress append-only and makes scope inflation visible before claims leave the system.

**Non-goal**: Does not yet fully derive every materialized view from events.

**Drift risk**: Scope calculus could become too heavy if every exploratory note must be fully scoped.

**Next check**: Keep scope enforcement strict at claim release, light during exploration.

### 2026-06-16 — Paper CI Phase 0

**Commit(s)**: `bc95c57`

**Action**: Added result-born provenance via `aeros.paper_ci.result_registry`, adapter contract, result registry check, and result record template.

**Alignment**: Moves paper CI boundary from manuscript scanning to estimation-call registration, so numbers receive birth certificates at creation.

**Non-goal**: Does not certify estimates, identification, paper-code consistency, or claim support.

**Drift risk**: Adapter contracts could splinter into bespoke plugins unless kept to one shared schema with tool-specific adapters.

**Next check**: Instrument one real estimation path and verify registry fields come from fitted objects or wrapper-controlled metadata, not prose.

### 2026-06-16 — Template Wiring / Paper CI Integration

**Commit(s)**: `18df986`

**Action**: Wired Paper CI and scope rules into AGENTS, templates, harness runner, manifest, architecture docs, revision log, and sync script.

**Alignment**: Makes the new integrity rules visible to agents and runnable by the default harness.

**Non-goal**: Does not run Phase 0 on a real SNAP or economics paper yet.

**Drift risk**: More template wiring can feel like complexity unless real projects exercise it and retire unused paths.

**Next check**: Use a real project fixture to see whether data-first and result registry reduce confusion rather than add paperwork.

### 2026-06-16 — Validation Project Gate Approval

**Commit(s)**: `9eeb698`

**Action**: Recorded MAHA validation project G11 design approval in the AEROS template history.

**Alignment**: Uses a real validation project to pressure-test human-gated progression rather than only adding template machinery.

**Non-goal**: Does not add a new AEROS capability or prove the template generalizes to all projects.

**Drift risk**: Validation-project commits can blur template evolution with project-specific decisions if not labeled clearly.

**Next check**: Keep validation project approvals clearly separated from reusable template changes in future update entries.

### 2026-06-16 — Update Ledger / Drift Tracking

**Commit(s)**: `pending`

**Action**: Added a human-readable update ledger, reusable entry template, and mechanical check requiring recent meaningful commits to be traceable.

**Alignment**: Helps detect whether AEROS evolution is drifting away from data-first automation, lineage, claim boundaries, and high-risk human gates.

**Non-goal**: Does not judge whether an update was good; it only makes the update rationale and drift risk visible.

**Drift risk**: The ledger itself could become paperwork if entries are verbose or detached from real project pressure tests.

**Next check**: Keep entries short and require each future capability update to name a real project validation path.

### 2026-06-16 — Paper CI Phase 0: implement adapter + de-risk sync

**Commit(s)**: `pending`

**Action**: Turned the result-registry from contract-only into working automation. Implemented the `python_statsmodels` adapter (`aeros/paper_ci/adapters.py`) that introspects a fitted object for estimator/formula/fixed-effects/cluster/values instead of hand-transcribed prose; made `sync-result-index` non-destructive (preserves curated columns and rows, backs up before overwrite) to remove a data-loss footgun; added a missing-artifact warning to `event append`; labeled paper-ci maturity honestly in the adapter contract.

**Alignment**: Directly serves the north star — automates a low-risk, mechanical step (numbers born with spec provenance) and removes a path that could silently destroy a hand-curated index.

**Non-goal**: Does not prove identification, does not approve claims, and is still not validated on a live project pipeline (CMPD vendors an older aeros without paper-ci; install/sync is required first).

**Drift risk**: Per-library bespoke adapters could re-complicate things; keep them behind the single adapter contract. The feature still has zero real-project validation, so it must not be presented as a finished capability.

**Next check**: Run Phase 0 end to end on one real CMPD estimate (after unifying the aeros install) and confirm the registered number round-trips into result_index without losing curated metadata.

### 2026-06-16 — Framework propagation discipline

**Commit(s)**: `pending`

**Action**: Added a "Framework Propagation Discipline" section to AGENTS.md: propagate framework code to vendored project copies only via `tools/sync_aeros_latest.zsh` (forward-only, non-destructive), commit target WIP before syncing, and never hand-copy framework files or relocate project-owned files out of `aeros/`.

**Alignment**: Attacks the actual root cause of recent drift — projects running divergent, hand-synced copies of aeros — by making one mechanism authoritative. Serves the north star by keeping every project on current, verifiable framework code.

**Non-goal**: Does not itself run the sync or reconcile already-diverged projects; it only sets the rule so divergence stops accumulating.

**Drift risk**: A rule no one runs is paperwork. This must be paired with actually running the sync after template changes — verified by projects not falling behind on framework code, not by the rule's existence.

**Next check**: After the next template change, confirm CMPD and other targets were brought current via the sync tool (not by hand) and that their framework code matches this template.

### 2026-06-17 — Fix eligibility over-claim found in live validation

**Commit(s)**: `pending`

**Action**: Fixed `infer_claim_type_eligibility` substring matching that labeled an associational OLS as `quasi_experimental_suggestive` because design marker "rd" was a substring of the variable name "hardness". Now formula markers match whole tokens; only controlled estimator class-name substrings (IV2SLS/IVGMM) are used. Found by the first real Phase 0 run on CMPD.

**Alignment**: Restores the north star — claims must stay within evidence. The bug did the opposite: it silently inflated an associational result to quasi-experimental.

**Non-goal**: Eligibility inference is still a conservative heuristic, not an identification verdict; the identification gate and human gate remain authoritative.

**Drift risk**: Marker lists can rot; keep them small and prefer estimator class names over fuzzy formula parsing.

**Next check**: Eligibility classifications on real project results should be spot-checked against the actual research design, not trusted blindly.

### 2026-06-17 — Paper CI Phase 0 validated on a real project

**Commit(s)**: `pending`

**Action**: Marked the result adapter contract `validated_on_real_project: true`. The first real Phase 0 run executed on CMPD: a clustered OLS extracted by the statsmodels adapter, registered and synced non-destructively, with the eligibility bug fixed in the same pass.

**Alignment**: Closes the long-standing "not yet validated on a real project" gap that recurred across earlier ledger entries; the mechanism is now evidence-backed, not just wired.

**Non-goal**: Validates the python_statsmodels path only. linearmodels and fixest adapters remain contract-only.

**Drift risk**: One real run is not a guarantee of generality; other estimators and projects can still surface adapter gaps.

**Next check**: Validate the linearmodels/fixest adapters on a real panel or IV project before marking them implemented.

### 2026-06-17 — Paper CI emits provenance on sync (resolves IMPROVE-003)

**Commit(s)**: `pending` (follows `2e24e9e` which logged the gap)

**Action**: `paper-ci sync-result-index` now also runs `sync_provenance`, writing `outputs/.provenance/<id>.json` for each registered result whose artifact exists (opt out with `--no-provenance`). Resolves AEROS-IMPROVE-003: a registered result no longer trips check_provenance / check_gate_exit (G6/G9) for a missing provenance JSON.

**Alignment**: Closes the parallel-track gap so result-born numbers feed the existing provenance subsystem instead of contradicting it — registration and provenance now move together.

**Non-goal**: Does not build research-graph derived edges (still a separate `aeros graph build`), and does not write provenance for results whose artifact is absent.

**Drift risk**: Two systems writing provenance could diverge; sync_provenance recomputes sha256 from real bytes and only writes for existing artifacts, so it stays grounded.

**Next check**: After a real register+sync, confirm check_provenance and check_gate_exit pass without a manual `aeros provenance` step.

### 2026-06-17 — Scope template-only checks out of downstream projects (resolves IMPROVE-004)

**Commit(s)**: `pending` (follows `b9f3c25`)

**Action**: Added `harness/check_scope.yml` (`template_only_checks`) and made `run_harness_checks.py` skip those checks unless run inside the template (detected via `tools/sync_aeros_latest.zsh`). Scopes out `check_update_ledger` so a vendored project no longer fails a template-evolution check it can never satisfy.

**Alignment**: Stops the harness from manufacturing failures in real projects, which was eroding trust in the check suite — a direct anti-drift fix.

**Non-goal**: Does not reclassify other checks; the list is deliberately minimal (one entry) and must stay justified.

**Drift risk**: The list could grow into a way to silence inconvenient checks. Each entry must be a check that can never pass in a normal project, not merely an unused one.

**Next check**: After syncing to a project, confirm check_update_ledger reports SKIP (not FAIL) and the remaining failures are real project state.

### 2026-06-17 — Correct backlog status for IMPROVE-003/004

**Commit(s)**: `pending` (follows `03a1b2c`)

**Action**: Set `status: resolved` on AEROS-IMPROVE-003 and 004, which had `resolved_at` filled but were still marked `open`.

**Alignment**: Keeps the backlog truthful — resolved items must read as resolved.

**Non-goal**: No behavior change; metadata correction only.

**Drift risk**: None.

**Next check**: Spot-check that resolved backlog items carry both status and resolved_at.
