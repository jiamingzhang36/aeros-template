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

## 2026-06-19

### 2026-06-19 - Work lane router for separated research surfaces

**Commit(s)**: `pending`

**Action**: Added the AEROS work-lane router. Introduced `aeros.runtime.work_lane`, `harness/work_lane_policy.yml`, and `checks/check_work_lanes.py`; added `--lane` to `aeros iterate`; surfaced lane labels in iterate plans; wired lane validation into the default harness, project manifest, init scaffold, sync script, AGENTS rules, and run-report template.

**Alignment**: Directly addresses a live usability/automation failure: data, literature, analysis, claim, writing, compliance, and harness work were all available inside one "continue" loop, allowing agents to drift from blocked data work into easier paperwork or literature cleanup. The lane router keeps automation focused on the active work surface.

**Non-goal**: Does not judge the quality of data, literature, analysis, or writing. It only prevents cross-lane substitution and makes lane switches explicit.

**Drift risk**: Lane inference is conservative and may misclassify future bespoke tasks. Prefer explicit `work_lane` in new task contracts when the inferred lane is unclear.

**Next check**: In a real project, run `aeros iterate --lane data --dry-run` and confirm it plans only data/source/probe work; if blocked, the agent should stop with a data blocker instead of switching to literature, writing, or harness cleanup.

### 2026-06-19 - Side-effect-free harness smoke checks

**Commit(s)**: `04f3925`, `ebaecaa`

**Action**: Made two harness smoke checks avoid unnecessary writes: `build_agent_runs_index.py` now leaves `agent_runs/INDEX.csv` untouched when rendered content is unchanged, and `check_pipeline_runs.py` compiles the master script in memory instead of invoking `py_compile` and writing `__pycache__`.

**Alignment**: Reduces empty churn in checks themselves. Verification should observe project state and fail honestly; it should not manufacture file changes or pycache artifacts just to prove nothing changed.

**Non-goal**: Does not change the meaning of agent-run index validation or pipeline smoke validation; it only removes incidental writes during validation.

**Drift risk**: In-memory syntax compilation could miss packaging-time issues that `py_compile` would surface, but this check's contract is only syntax smoke, not bytecode-cache health.

**Next check**: Full harness should pass in a restricted workspace without needing to write `agent_runs/INDEX.csv` or `code/__pycache__`.

### 2026-06-19 - Goal-mode data progress honesty gate

**Commit(s)**: `c9953b1`

**Action**: Added a goal/continue-mode data-progress guard. Data-oriented action receipts that claim `substantive_research_progress` now require a real data/source/probe artifact, not only task files, scripts, run reports, receipts, README/Makefile edits, checks, or ledger entries. Added `harness/goal_mode_policy.yml`, `checks/check_goal_mode_data_progress.py`, a `source_discovery_attempt` progress label, run-report prompts, manifest/harness wiring, and sync/init-project propagation.

**Alignment**: Addresses the live failure mode where an agent searched for official data, found no usable source, then generated Txxx scaffolding and reports that looked like progress. This preserves AEROS's north star: automate low-risk progress, but do not let process artifacts masquerade as data acquisition.

**Non-goal**: Does not guarantee that a retrieved data source is scientifically adequate, official, legal to use, or complete. It only enforces the narrower process claim: if the run says data progressed, a concrete data/source/probe artifact must exist; otherwise the run must be reported as blocked or source discovery.

**Drift risk**: The check could become over-strict if future projects have legitimate data evidence outside the allowed path set. Keep the path allowlist small but update it when a real project introduces a new durable source-snapshot location.

**Next check**: In the next project run, ask for data collection in goal/continue mode and confirm the agent either writes a raw/source/probe artifact or stops with `source_discovery_attempt`/`blocked_queue_preparation`, without creating Txxx scaffolding as a substitute for data.

## 2026-06-18

### 2026-06-18 - Directory local data probes

**Commit(s)**: `2db9949`

**Action**: Updated `aeros.runtime.data_probe` so a local inventory path may be a directory, not only a single CSV/TSV/JSONL file. Directory probes now sample up to 25 supported files, write a sample manifest, union observed fields, and record linkage-key hints. The planner marks local paths runnable only when supported files exist.

**Alignment**: Fixes a real downstream run where `data probe plan` generated a runnable local probe for CMPD final CSVs but `data probe run` refused the directory. This keeps low-risk local-cache-safe data probing automated instead of forcing manual intervention.

**Non-goal**: Does not approve official-source/API/scraping probes and does not make probe evidence admissible for final claims.

**Drift risk**: Directory probes can produce many sample artifacts if left unbounded; the runner caps sampled files and keeps the output as feasibility evidence only.

**Next check**: After the next template sync, confirm a downstream project can run `aeros data probe run --source <local-directory-source>` and pass `check_data_probe.py`.

### 2026-06-18 - Revalidation skill waiver receipts

**Commit(s)**: `3e82d5e`

**Action**: Updated `aeros.runtime.kernel` so check-only revalidation of stale passed tasks writes explicit skill waivers when the task contract declares recommended or required skills. The waiver scope is limited to fingerprint refresh: existing outputs passed task checks, no external skill invocation occurred, and no skill-derived evidence is claimed.

**Alignment**: Fixes a real downstream G10 rerun where AEROS correctly avoided wasteful worker reruns but then produced empty skill invocation receipts. This preserves automation honesty while still allowing low-risk stale-task revalidation.

**Non-goal**: Does not turn recommended skills into optional decorations for real worker runs, and does not treat a waiver as evidence from the waived skill.

**Drift risk**: Automatic waivers could hide under-reviewed work if applied outside check-only revalidation. Keep the waiver scope narrow and visible in receipts.

**Next check**: On the CMPD project, rerun stale execution tasks and confirm `check_skill_invocations.py`, `check_noop_runs.py`, and the full harness pass after check-only revalidation.

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

**Commit(s)**: `1adbe31`

**Action**: Added a human-readable update ledger, reusable entry template, and mechanical check requiring recent meaningful commits to be traceable.

**Alignment**: Helps detect whether AEROS evolution is drifting away from data-first automation, lineage, claim boundaries, and high-risk human gates.

**Non-goal**: Does not judge whether an update was good; it only makes the update rationale and drift risk visible.

**Drift risk**: The ledger itself could become paperwork if entries are verbose or detached from real project pressure tests.

**Next check**: Keep entries short and require each future capability update to name a real project validation path.

### 2026-06-16 — Paper CI Phase 0: implement adapter + de-risk sync

**Commit(s)**: `6628ecf`

**Action**: Turned the result-registry from contract-only into working automation. Implemented the `python_statsmodels` adapter (`aeros/paper_ci/adapters.py`) that introspects a fitted object for estimator/formula/fixed-effects/cluster/values instead of hand-transcribed prose; made `sync-result-index` non-destructive (preserves curated columns and rows, backs up before overwrite) to remove a data-loss footgun; added a missing-artifact warning to `event append`; labeled paper-ci maturity honestly in the adapter contract.

**Alignment**: Directly serves the north star — automates a low-risk, mechanical step (numbers born with spec provenance) and removes a path that could silently destroy a hand-curated index.

**Non-goal**: Does not prove identification, does not approve claims, and is still not validated on a live project pipeline (CMPD vendors an older aeros without paper-ci; install/sync is required first).

**Drift risk**: Per-library bespoke adapters could re-complicate things; keep them behind the single adapter contract. The feature still has zero real-project validation, so it must not be presented as a finished capability.

**Next check**: Run Phase 0 end to end on one real CMPD estimate (after unifying the aeros install) and confirm the registered number round-trips into result_index without losing curated metadata.

### 2026-06-16 — Framework propagation discipline

**Commit(s)**: `b9e5fbb`

**Action**: Added a "Framework Propagation Discipline" section to AGENTS.md: propagate framework code to vendored project copies only via `tools/sync_aeros_latest.zsh` (forward-only, non-destructive), commit target WIP before syncing, and never hand-copy framework files or relocate project-owned files out of `aeros/`.

**Alignment**: Attacks the actual root cause of recent drift — projects running divergent, hand-synced copies of aeros — by making one mechanism authoritative. Serves the north star by keeping every project on current, verifiable framework code.

**Non-goal**: Does not itself run the sync or reconcile already-diverged projects; it only sets the rule so divergence stops accumulating.

**Drift risk**: A rule no one runs is paperwork. This must be paired with actually running the sync after template changes — verified by projects not falling behind on framework code, not by the rule's existence.

**Next check**: After the next template change, confirm CMPD and other targets were brought current via the sync tool (not by hand) and that their framework code matches this template.

### 2026-06-17 — Fix eligibility over-claim found in live validation

**Commit(s)**: `6405df5`

**Action**: Fixed `infer_claim_type_eligibility` substring matching that labeled an associational OLS as `quasi_experimental_suggestive` because design marker "rd" was a substring of the variable name "hardness". Now formula markers match whole tokens; only controlled estimator class-name substrings (IV2SLS/IVGMM) are used. Found by the first real Phase 0 run on CMPD.

**Alignment**: Restores the north star — claims must stay within evidence. The bug did the opposite: it silently inflated an associational result to quasi-experimental.

**Non-goal**: Eligibility inference is still a conservative heuristic, not an identification verdict; the identification gate and human gate remain authoritative.

**Drift risk**: Marker lists can rot; keep them small and prefer estimator class names over fuzzy formula parsing.

**Next check**: Eligibility classifications on real project results should be spot-checked against the actual research design, not trusted blindly.

### 2026-06-17 — Paper CI Phase 0 validated on a real project

**Commit(s)**: `de2cd98`

**Action**: Marked the result adapter contract `validated_on_real_project: true`. The first real Phase 0 run executed on CMPD: a clustered OLS extracted by the statsmodels adapter, registered and synced non-destructively, with the eligibility bug fixed in the same pass.

**Alignment**: Closes the long-standing "not yet validated on a real project" gap that recurred across earlier ledger entries; the mechanism is now evidence-backed, not just wired.

**Non-goal**: Validates the python_statsmodels path only. linearmodels and fixest adapters remain contract-only.

**Drift risk**: One real run is not a guarantee of generality; other estimators and projects can still surface adapter gaps.

**Next check**: Validate the linearmodels/fixest adapters on a real panel or IV project before marking them implemented.

### 2026-06-17 — Paper CI emits provenance on sync (resolves IMPROVE-003)

**Commit(s)**: `b9f3c25` (gap logged in `2e24e9e`)

**Action**: `paper-ci sync-result-index` now also runs `sync_provenance`, writing `outputs/.provenance/<id>.json` for each registered result whose artifact exists (opt out with `--no-provenance`). Resolves AEROS-IMPROVE-003: a registered result no longer trips check_provenance / check_gate_exit (G6/G9) for a missing provenance JSON.

**Alignment**: Closes the parallel-track gap so result-born numbers feed the existing provenance subsystem instead of contradicting it — registration and provenance now move together.

**Non-goal**: Does not build research-graph derived edges (still a separate `aeros graph build`), and does not write provenance for results whose artifact is absent.

**Drift risk**: Two systems writing provenance could diverge; sync_provenance recomputes sha256 from real bytes and only writes for existing artifacts, so it stays grounded.

**Next check**: After a real register+sync, confirm check_provenance and check_gate_exit pass without a manual `aeros provenance` step.

### 2026-06-17 — Scope template-only checks out of downstream projects (resolves IMPROVE-004)

**Commit(s)**: `03a1b2c` (follows `b9f3c25`)

**Action**: Added `harness/check_scope.yml` (`template_only_checks`) and made `run_harness_checks.py` skip those checks unless run inside the template (detected via `tools/sync_aeros_latest.zsh`). Scopes out `check_update_ledger` so a vendored project no longer fails a template-evolution check it can never satisfy.

**Alignment**: Stops the harness from manufacturing failures in real projects, which was eroding trust in the check suite — a direct anti-drift fix.

**Non-goal**: Does not reclassify other checks; the list is deliberately minimal (one entry) and must stay justified.

**Drift risk**: The list could grow into a way to silence inconvenient checks. Each entry must be a check that can never pass in a normal project, not merely an unused one.

**Next check**: After syncing to a project, confirm check_update_ledger reports SKIP (not FAIL) and the remaining failures are real project state.

### 2026-06-17 — Correct backlog status for IMPROVE-003/004

**Commit(s)**: `8ed35a9` (follows `03a1b2c`)

**Action**: Set `status: resolved` on AEROS-IMPROVE-003 and 004, which had `resolved_at` filled but were still marked `open`.

**Alignment**: Keeps the backlog truthful — resolved items must read as resolved.

**Non-goal**: No behavior change; metadata correction only.

**Drift risk**: None.

**Next check**: Spot-check that resolved backlog items carry both status and resolved_at.

### 2026-06-17 — Make the review verification gate a hard check

**Commit(s)**: `a0908f5` (follows `8ed35a9`)

**Action**: Added `checks/check_review_verification.py` and wired it into the
harness. It fails any review report under `audits/skill_runs/` where a HIGH/MED
finding that mentions a data-dependent concept (missingness, convergence,
separation, collinearity, overlap, merge match) lacks a verification marker
(`(checked)`, a number, `UNVERIFIED`, or `NOT RUN`). Turns the soft SKILL.md gate
into a mechanical one.

**Alignment**: Directly enforces "no data-dependent severity without a number" —
the discipline whose absence let an associational OLS be graded HIGH from code
alone. On first run it caught two real ungrounded findings in this session's own
reviews (a moot merge MED, a falsified imputation MED), both then verified/fixed.

**Non-goal**: It enforces a labeling format, not the correctness of the number;
it is keyword-based and will miss novel phrasings. It is a gate, not a guarantee.

**Drift risk**: Keyword leakage (false negatives) and possible false positives on
unusual prose. Keep the keyword list tied to the gate's data-dependent classes.

**Next check**: Spot-check that flagged findings are genuinely data-dependent and
that the gate is not being satisfied by hollow `(checked)` tags without numbers.

### 2026-06-18 - Literature full-text execution boundary

**Commit(s)**: `e312bc1`

**Action**: Split literature bookkeeping from substantive literature review execution. Added `check_literature_fulltext_execution.py`, `harness/literature_fulltext_policy.yml`, full-text extraction card fields, function-specific synthesis placeholders, and LIT-FULL/LIT-SYNTH/LIT-PAPER task contracts.

**Alignment**: Prevents dashboard/card repair from being reported as completed literature review. Keeps AEROS honest: source-bound cards can fix the ledger, but only full-text extraction can support synthesis or paper positioning.

**Non-goal**: Does not perform a real full-text literature review for any project and does not certify that existing source-bound cards are substantive evidence.

**Drift risk**: The new LIT-FULL tasks could become paperwork if agents fill templates without opening sources. The hard check therefore requires opened source/date, extraction depth, direct evidence notes, and support/cannot-support boundaries.

**Next check**: Run one real project literature queue through LIT-FULL-001 and confirm source-bound cards fail if cited in synthesis, while verified full-text cards pass.
