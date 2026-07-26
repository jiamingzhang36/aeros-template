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

## 2026-07-03

### 2026-07-03 - Repair adapter-layer ledger and preflight authority drift

**Commit(s)**: `7a3bc70`

**Action**: Fixed the adapter layer after review found three correctness risks: neutral tasks defaulted to `claim_audit`, which removed `evidence/claim_registry.md` from `must_not_touch`; route keyword inference overwrote a pending route decision instead of surfacing it as a suggestion; and sync doctor did not cover route-gate/workflow-preset surfaces. Added `general_guardrail`, kept claim registry protected by default, changed preflight to report `route=pending` plus `route_suggestion`, expanded sync doctor capabilities, removed the hardcoded template fallback, and ignored the local `validation_projects/light-meal/` scratch project.

**Alignment**: Keeps AEROS advisory packets honest: preflight should reduce drift, not grant accidental authority. The sync doctor should reveal stale project surfaces before judging downstream behavior.

**Non-goal**: Does not make keyword classification semantic understanding, approve routes, fetch data, admit evidence, edit claims, approve gates, or sync any downstream project.

**Drift risk**: Keyword classifiers remain brittle (`metadata`/`preflight`-style accidental matches are possible). Mitigation: `general_guardrail` is conservative, route inference is suggestion-only, and preflight outputs explicit `does_not_prove` boundaries.

**Next check**: Run on one real source-capture project and confirm neutral cleanup keeps `claim_registry` protected, route-sensitive work stops at pending route decisions, and sync doctor flags route/workflow capability drift.

### 2026-07-03 - Source capture permission tiers

**Commit(s)**: `29f1e09`

**Action**: Added `source_capture_permission` tiers so low-risk public/local staging capture can proceed without repeated human approval, while Chrome/browser/portal/batch capture requires bounded route-level approval and credentials/API keys/paid/private/ToS/`data/raw`/canonical/claim/paper/release work remains human-required.

**Alignment**: Reduces unnecessary human pushes for safe staging work while preserving the core boundary: staging capture is not canonical evidence, claim support, paper readiness, or release approval.

**Non-goal**: Does not fetch sources, validate source identity, admit evidence, write canonical data, modify protected files, approve gates, or waive legal/privacy/IRB/source terms.

**Drift risk**: Green-tier capture could be mistaken for permission to promote evidence. Mitigation: preflight requires staging/probe/audit outputs only and records promotion as a separate controlled step.

**Next check**: In a real public-source project, verify `aeros task preflight` returns `none_for_staging_public_capture` for official/public staging snapshots and `route_level` for browser/portal batches.

### 2026-07-03 - Task preflight and sync doctor adapters

**Commit(s)**: `a7f261f`

**Action**: Added `aeros task preflight` to emit the short task-start operating envelope (`task_mode`, route, skill obligations, output intents, allowed paths, must-not-touch paths) and `aeros sync doctor` to compare downstream projects against current template capabilities. Tightened skill receipts so required/recommended skill work must either record `skills_used` or an explicit waiver.

**Alignment**: Converts repeated chat instructions into deterministic adapter-layer packets that make the next step, boundaries, and sync drift visible before work starts.

**Non-goal**: Does not execute tasks, approve routes, invoke skills, certify skill output, approve gates, admit evidence, or decide the scientific quality of a workflow.

**Drift risk**: Preflight could be over-trusted as an authority envelope and sync doctor could be treated as scientific validation. Mitigation: both are advisory and carry explicit non-goal boundaries; preflight now keeps protected surfaces protected unless a true contract/human route allows them.

**Next check**: Run preflight and sync doctor in SNAP/CMPD before the next source/data task and confirm stale template surfaces are reported before judging project behavior.

### 2026-07-03 - Task mode, output intent, route gate, and improve harvest controls

**Commit(s)**: `ecee50d`

**Action**: Added task-mode classification, output-intent declarations, route early gate checks, and `aeros improve harvest` so AEROS can distinguish source capture, data repair, claim audit, writing sync, submission readiness, and route recovery without treating staging as canonical evidence.

**Alignment**: Moves AEROS toward a lighter cockpit and better project adaptation: tasks get the smallest useful guardrail rather than one heavy governance shell for every action.

**Non-goal**: Does not make keyword classifiers semantic reasoning, fetch data, complete literature review, promote staging artifacts, approve routes, approve gates, or upgrade claims.

**Drift risk**: Keyword-based task classification can be brittle and should not be treated as scientific understanding. Mitigation: checks validate only structural honesty; route and output intent remain advisory until supported by receipts/provenance/human review.

**Next check**: On a real project, compare preflight/task-mode recommendations against the actual task and record any misclassification as an improvement harvest item.

## 2026-07-01

### 2026-07-01 - Sync route-decision scaffold to downstream projects

**Commit(s)**: `0f41180`

**Action**: Updated `tools/sync_aeros_latest.zsh` so `discovery/route_decision.yml` is seeded into downstream projects and wired into `project_manifest.yml` required files. This fixes the first SNAP rollout finding where the new check synced but its required scaffold did not.

**Alignment**: Keeps framework sync self-contained: a check introduced by the template must bring its required template artifact along, otherwise downstream projects get false red harness failures.

**Non-goal**: Does not decide a project's route, overwrite an existing project-specific `route_decision.yml`, or make any data/source collection progress.

**Drift risk**: Low; this is seed-only and preserves existing downstream route decisions. The risk is forgetting future check dependencies in sync, so route-decision becomes a regression example.

**Next check**: Re-sync SNAP and confirm `check_discovery_route_decision.py` no longer fails due to a missing scaffold.

### 2026-07-01 - Add workflow presets and staging evidence semantics (AEROS-IMPROVE-032)

**Commit(s)**: `f435106`

**Action**: Added session workflow presets (`recapture_source_pool`, `claim_audit`, `writing_guardrail`, `chrome_assisted_review`, `source_promotion_queue`) so project-specific intermediate work can be declared without hand-extending lane prefixes. Added `discovery/route_decision.yml` plus a route-decision check for early data strategy selection, including `negative_seed_first` for scam/fraud/enforcement-style projects. Extended completion receipts with `staging_artifact_paths` and `substantive_evidence_paths` so staging work can be `ROUTE_READY` without being laundered into substantive evidence.

**Alignment**: Reduces false AUTHORITY_DRIFT/SCOPE_DRIFT in real projects while preserving AEROS's authority boundary. It lets recapture/source-review/Chrome/OCR/queue preparation count as legitimate route progress, but not as final data, result, claim support, or gate approval.

**Non-goal**: Does not loosen claim authority, approve gates, certify source validity, promote staging artifacts into canonical evidence, fetch data/full text, or decide the scientifically correct discovery route.

**Drift risk**: Workflow presets could become a broad bypass if they grow into catch-all allowlists. Mitigation: presets remain named, narrow, audited by `check_session_scope.py`, and completion receipts still separate staging from substantive evidence.

**Next check**: Sync into SNAP and run `aeros session start --lane data --workflow recapture_source_pool --dry-run` plus a session audit fixture to confirm expected staging paths no longer trip AUTHORITY_DRIFT while forbidden authority surfaces still do.

## 2026-06-25

### 2026-06-25 - Fix sync manifest-wiring indentation bug (AEROS-IMPROVE-032)

**Commit(s)**: `3025c69`

**Action**: `tools/sync_aeros_latest.zsh` ensure_manifest_wiring inserted new required_files items at a hardcoded key-indent+2, ignoring the existing list's indentation. A project whose required_files items sit at the key's own indent (MAHA) got a mismatched insert that broke `project_manifest.yml`, cascading into 8+ harness failures (cockpit/context/stale/graph all parse the manifest). Fixed to detect and match the existing list-item indentation (fallback key+2 for empty lists). Verified on 4-space/6-space/empty fixtures; the old logic reproduced the exact "while parsing a block mapping" error.

**Alignment**: Forward-only sync must never corrupt a downstream project's manifest. Found when a sync into MAHA broke it (and inflated MAHA from 7 to 20 fails).

**Non-goal**: Only changes insertion indentation, not which files are wired. The analogous `checks:` insertion is lower-risk (column-0 convention) and left as-is.

**Drift risk**: Low; purely structural.

**Next check**: On the next real sync into a project, confirm project_manifest.yml stays valid YAML.

### 2026-06-25 - Scope ledger check to framework commits (AEROS-IMPROVE-031)

**Commit(s)**: `16bd7ed`

**Action**: `check_update_ledger` now only requires a narrative ledger entry for commits that change the framework itself (`aeros/ checks/ harness/ templates/ tools/`). Bookkeeping, validation-project, docs, and project-artifact commits are exempt. Added `_commit_touches_framework`; non-framework commits are skipped instead of flagged.

**Alignment**: Kills the recurring false-red harness failure (a validation-project gate approval `b12222e`, backfill commits, etc. tripped the check though they touch no framework code) WITHOUT weakening rationale enforcement -- real framework changes still require a narrative entry.

**Non-goal**: Not the full "generate the ledger from RunRecord+git" projection; that remains deferred. This is the minimal correct scoping that removes the brittleness at no integrity cost.

**Drift risk**: If framework code were committed under a path outside FRAMEWORK_PREFIXES it would escape the requirement; mitigated by the prefixes covering all framework dirs, and unknown-commit inspection failing conservative (require entry).

**Next check**: Confirm a framework-only commit still must be referenced, and a validation-project/bookkeeping commit no longer trips the check.

### 2026-06-25 - Bind gate approval to integrity checks (AEROS-IMPROVE-030)

**Commit(s)**: `68fc121`

**Action**: Added `checks/check_approval_integrity.py`, wired into run_harness_checks and the sync CHECKS map. When any `decisions/approvals/G*.md` exists, the integrity-critical checks (noop_runs, completion_receipts, skill_invocations, estimand_data_contract) must pass; otherwise the harness fails with one pointed "gate approval is not integrity-backed" signal naming the gate and failing checks. Surfaced by the 2026-06-25 MAHA validation, where a G10 approval was committed on a project failing 7 integrity checks with nothing tying the approval to them. (That approval was committed as `b12222e`, which this check now flags as not integrity-backed.)

**Alignment**: Makes the authority boundary executable -- "approved" can no longer silently coexist with red integrity. Serves "declared completion must correspond to a qualified product."

**Non-goal**: AEROS does not block a human git commit, auto-fix the work, or auto-withdraw the approval; it converts an unbacked approval into a blocking, legible harness failure. The human repairs the work or withdraws the approval.

**Drift risk**: The integrity-critical set is fixed (4 checks); too broad could over-block. Mitigation: the set is the unambiguous "claimed-done-but-isn't" signals; the FAIL lists exactly which fired.

**Next check**: On MAHA, after the work is completed or G10 withdrawn, confirm PASS; on a green approved project (CMPD) confirm no false positive.

## 2026-06-23

### 2026-06-23 - AgentEnvelope audit mode

**Commit(s)**: `a2bc1ef`

**Action**: Add AgentEnvelope audit mode for provider-backed agent tasks. The
runtime snapshots project writes around each agent call and blocks task
acceptance when denied or undeclared writes are observed, writing an audit record
under `agent_runs/agent_envelope_audits/` on violation.

**Alignment**: Makes LLM/provider task side effects visible and fail-closed
without pretending that provider agents are fully sandboxed.

**Non-goal**: Does not provide full LLM-agent sandboxing, safe network/provider
behavior, claim support, gate approval, or automatic rollback.

**Drift risk**: Audit mode can be mistaken for confinement. Mitigation: policy,
freeze doc, and check all state that this is audit/visibility, not full sandbox.

**Next check**: Run on a real provider-backed project task in audit mode and
confirm allowed outputs pass while denied/undeclared writes escalate.

### 2026-06-23 - Real-project acid-test repairs

**Commit(s)**: `6eb91a5`

**Action**: Fix two CMPD acid-test findings: allow controller-safe
`aeros recover <task> --check` commands so stale free revalidation can actually
run, and make readiness surface literature full-text blockers instead of marking
a project `fulltext_verified` when only some registry rows have extraction cards.

**Alignment**: Reduces human pushes and false readiness by making the deterministic
next action executable and preserving unresolved literature blockers in the
paper-readiness report.

**Non-goal**: Does not fetch missing full text, write extraction cards, upgrade
claims, approve gates, or mark the paper ready.

**Drift risk**: Controller-safe recover could grow too broad. Mitigation: only
`recover --check` is allowed; recover without checks remains refused.

**Next check**: Re-run CMPD `aeros run --until no-progress --dry-run --lane data`
and paper-readiness JSON to confirm recover is no longer refused and literature
blockers appear.

### 2026-06-23 - ExecutionEnvelope deterministic `aeros run` enforcement

**Commit(s)**: `41aec3c`

**Action**: Route deterministic `aeros run` commands (`run.command` with
`max_agent_calls: 0`) through isolated-worktree ExecutionEnvelope enforcement,
copying back only declared `allowed_outputs` and blocking denied/undeclared
writes. Extend `check_execution_envelope.py` with a real `aeros run` fixture.

**Alignment**: Turns the ActionSpec/ExecutionEnvelope boundary from a declaration
into an enforced runtime constraint for the safest class of task execution.

**Non-goal**: Does not claim full LLM-agent sandboxing, scientific validity,
claim support, gate approval, or safe provider/network behavior.

**Drift risk**: Users may read "run envelope" as full sandbox coverage. Mitigation:
policy and freeze doc split deterministic local runs from provider-backed agent
tasks.

**Next check**: Sync to CMPD and run a deterministic smoke task to confirm declared
outputs are accepted while denied roots remain protected.

### 2026-06-23 - Paper-readiness report-only packet

**Commit(s)**: `7ed4027`

**Action**: Add `aeros paper-readiness report` to aggregate the derived readiness
vector into a human review packet with `authority_status=report_only` and
`paper_ready_verdict=not_asserted`.

**Alignment**: Converts scattered paper/package readiness signals into an
actionable human review packet without granting the runtime authority to declare
submission readiness.

**Non-goal**: Does not mark paper-ready, approve release, modify paper text,
upgrade claims, or approve gates.

**Drift risk**: Users may confuse a readiness report with an approval. Mitigation:
policy/check/CLI require `not_asserted`, `report_only`, and `required_human_gate`.

**Next check**: Run on CMPD after sync and confirm it identifies true blockers
without changing paper, claim registry, decision log, or runtime state.

### 2026-06-23 - Human-gated claim-upgrade recommendation

**Commit(s)**: `a4ed72e`

**Action**: Add `aeros claim-upgrade review` to generate a recommendation-only review
from ClaimVector inputs, optionally writing a decision packet under
`decisions/claim_upgrade/`, while checks verify `evidence/claim_registry.md` is not
modified.

**Alignment**: Automates the boring review step while preserving the authority boundary
that claim upgrades require human gate approval.

**Non-goal**: Does not automatically upgrade claims, modify the claim registry, approve
gates, certify scientific truth, or mark paper-ready.

**Drift risk**: Users may confuse recommendation packets with approval. Mitigation:
the policy/check/CLI emit `recommendation_only` and require human gate.

**Next check**: Run this on one real ambiguous CMPD claim and confirm it creates only a
review packet, not a registry mutation.

### 2026-06-23 - SQLite journal as derived index

**Commit(s)**: `1b02dbc`

**Action**: Add `aeros journal build` and a SQLite journal runtime that projects
artifacts, results, provenance, EvidenceUnit/ResultAdmission records, and events into
`outputs/journal/aeros_journal.sqlite`. The journal marks `authority=derived_index_only`
and can be dry-run without writing.

**Alignment**: Adds query efficiency without creating a second truth source. Git files
remain authoritative; SQLite is disposable and rebuildable.

**Non-goal**: Does not migrate runtime state to SQLite, certify claims, approve gates,
or replace project files.

**Drift risk**: Users may treat the database as authoritative. Mitigation:
policy/check enforce derived-index-only metadata and source-file immutability during
build.

**Next check**: In a real project, build the journal after reconcile and verify the
database can be deleted/rebuilt without changing source files or claim status.

### 2026-06-23 - Preserve project update ledgers during framework sync

**Commit(s)**: `e06f2c7`

**Action**: Fix `tools/sync_aeros_latest.zsh` so downstream projects keep their own
`decisions/update_ledger.md` once it exists. Template sync still seeds the file for
new projects, but it no longer overwrites project-specific commit tracking.

**Alignment**: Prevents framework rollout from erasing the very audit trail that
guards against drift and fake completion.

**Non-goal**: Does not merge template and project ledgers automatically or repair old
project ledger gaps by itself.

**Drift risk**: Existing projects may miss new template ledger examples. Mitigation:
ledger structure is enforced by `check_update_ledger.py`; framework changes remain in
git history and revision logs.

**Next check**: Re-sync CMPD and confirm its project-specific ledger entry survives
while smoke remains green.

### 2026-06-23 - ClaimVector advisory compiler and envelope coverage v2

**Commit(s)**: `66c2e43`

**Action**: Add a ClaimVector v1 compiler that emits advisory allowed/forbidden
claim language and human-review recommendations without writing the claim registry.
Extend ExecutionEnvelope coverage with an ActionSpec-level executor path and a real
read-only `aeros next --json` envelope check.

**Alignment**: Advances the deferred claim-boundary and runtime-confinement work
without granting machines new authority: ClaimVector constrains language, and
ExecutionEnvelope broadens safe command coverage.

**Non-goal**: Does not automatically upgrade claims, certify paper readiness, replace
human gates, introduce SQLite as truth, or route all `aeros run` actions through the
envelope.

**Drift risk**: ClaimVector could be mistaken for claim adjudication. Mitigation:
policy/check/CLI all emit `advisory_only`, require human gate, and verify the claim
registry is not modified.

**Next check**: On a real project, run `aeros claim-vector compile` for one ambiguous
claim and confirm it changes only the recommended language boundary, not claim status.

### 2026-06-23 - Evidence admission boundary and parser false-fulltext fixtures

**Commit(s)**: `459264c`

**Action**: Deepen the first deferred architecture slice without expanding authority:
upgrade `check_evidence_units.py` from optional-directory validation to an executable
EvidenceUnit/ResultAdmission fixture check, add policy/templates for the machine-fact
vs human-admission split, add false-fulltext parser fixtures for Cloudflare/security
and SPA-shell pages, and extend ExecutionEnvelope to run a real read-only check action
without declared writes.

**Alignment**: Tightens the path from parsed artifact to admitted evidence while
preserving the central AEROS rule: machine facts can be generated and checked, but
human admission and claim upgrades remain separate authority events.

**Non-goal**: Does not certify parser quality, admit any real project evidence,
upgrade claims, create a SQLite truth source, or make all `aeros run` actions use
ExecutionEnvelope.

**Drift risk**: EvidenceUnit could become a new registry burden or parser benchmark
could be mistaken for full-text review. Mitigation: fixtures are explicit smoke
tests; ResultAdmission is required before claim use; false-fulltext cases are negative
boundary tests only.

**Next check**: Sync to one real project and confirm literature/data lanes can produce
candidate EvidenceUnit records without changing claim status or gate status.

### 2026-06-23 - Architecture freeze baseline

**Commit(s)**: `b0aa2e7`

**Action**: Add `docs/design/architecture_freeze_v1.md` and a narrow freeze-doc
check so AEROS has a named freeze baseline before further runtime hardening. The
document fixes the 5-layer authority model, feature-admission rule, do-not-expand
list, and sequencing constraints for ExecutionEnvelope, ClaimVector, and
ResultRecord/ResultAdmission separation.

**Alignment**: Turns "stop adding surface area" into an auditable architecture
contract rather than a chat preference.

**Non-goal**: Does not remove existing lanes, checks, gates, registries, or project
artifacts. It freezes expansion policy; it does not certify research quality.

**Drift risk**: Freeze docs can become decorative if not checked. Mitigation:
`check_architecture_freeze.py` enforces the required clauses and smoke profile runs it.

**Next check**: During the next requested feature, verify it explicitly satisfies the
feature-admission rule before implementation.

### 2026-06-23 - Orthogonal progress-domain semantics

**Commit(s)**: `6bb6bb4`

**Action**: Add `progress_domain: research|runtime|governance` beside the existing
`progress_class`, introduce the user-facing `DECISION_RECORDED` label, and update
completion policies/templates so runtime engineering, research routing, and governance
decisions no longer collapse into one "substantive progress" bucket.

**Alignment**: Reduces fake-progress confusion: a framework artifact can be
runtime/substantive, a data contract can be research/routing, and an approval can be
governance/decision without pretending any of them produced research evidence.

**Non-goal**: Does not automatically reclassify old project receipts or certify that
human decisions were scientifically correct.

**Drift risk**: More labels can become bureaucracy. Mitigation: keep the domain
three-way and require checks to validate only the orthogonal semantics, not create new
lane systems.

**Next check**: On the next real project rollout, confirm completion receipts with
framework sync, route packet, and human decision examples render distinct labels.

### 2026-06-23 - ExecutionEnvelope isolated-worktree slice

**Commit(s)**: `2032081`

**Action**: Add a minimal `ExecutionEnvelope` runtime and adversarial check that runs a
safe local action in an isolated git worktree, copies back only declared outputs, and
fails if an action writes denied or undeclared paths.

**Alignment**: Makes ActionSpec boundaries enforceable for one vertical slice instead
of leaving read/write authority as YAML-only intent.

**Non-goal**: Does not route all `aeros run` actions through envelopes, sandbox
network/API access, or certify scientific validity of outputs.

**Drift risk**: A partial envelope could be mistaken for universal sandboxing.
Mitigation: the check and freeze doc call it a v1 safe/local slice only; broader
admission requires explicit runtime profiles.

**Next check**: After downstream projects sync, pick one low-risk local action and
route it through the envelope path before broadening executor coverage.

## 2026-06-22

### 2026-06-22 - Make controller stop on literature full-text blockers (IMPROVE-015)

**Commit(s)**: `0c380a0`

**Action**: CMPD validation showed that the new bounded controller stopped after one
no-progress dry-run step, but the literature lane route still preferred a stale
D001b framework-search preview over explicit P013/P016/P030 full-text blockers.
The same sync revealed lane-specific next-action drift for data/claim requests.
Added deterministic blocked-fulltext detection from `discovery/literature/search_log.csv`,
restored lane-scoped fallback, and expanded `check_next_action` so blocked full-text
records must produce a blocked literature next-action that names the paper IDs.

**Alignment**: Keeps controller automation bounded around the real lane blocker
instead of manufacturing progress through stale previews.

**Non-goal**: Does not fetch PDFs, bypass publisher controls, write extraction cards,
or resolve the blocked papers. It only routes the controller honestly.

**Drift risk**: Over-prioritizing blockers could hide useful synthesis work from
already-extracted papers. Mitigation: the blocker is explicit and requires human
resolution/waiver before the lane proceeds.

**Next check**: On CMPD or another adopted project, rerun
`python3 -m aeros.cli run --until no-progress --dry-run --lane literature` after a
manual/Zotero full-text blocker is resolved and confirm the lane advances to the next
bounded literature step.

### 2026-06-22 - Record CMPD first-sync drift; defer full framework upgrade (IMPROVE-012)

**Commit(s)**: `8f32bb6`

**Action**: Attempted to sync stale-triage v3 into CMPD. The forward-only sync brings
the whole recent feature family (next_action/cockpit/context_bundle/stale_triage) and
its stricter checks; 6 harness checks failed in CMPD — sync-induced drift (newer checks
vs CMPD's older literature/compliance artifacts), NOT the v3 fix. A clean "v3-only"
landing is impossible (stale_triage interlocks with cli `stale`/`next` + next_action).
Owner chose the surgical path: reverted CMPD to its clean, green pre-sync state
(literature fulltext_cache WIP untouched, no collision with the parallel agent) and
logged AEROS-IMPROVE-012 for the deliberate full upgrade. v3 stays in the template,
validated read-only against CMPD's real data.

**Alignment**: Honors forward-only-whole-version propagation — refuses a frankenversion
partial sync — and keeps the running project green. The drift is now a tracked,
informed task rather than a surprise.

**Non-goal**: Does not land v3 live in CMPD; that needs the full upgrade (artifact
migration + check scoping), coordinated with the literature agent.

**Drift risk**: The longer CMPD lags the template, the larger the eventual upgrade.
Mitigation noted in IMPROVE-012: extend check_scope.yml so a first sync degrades
gracefully (AEROS-IMPROVE-004 family).

**Next check**: On the CMPD full upgrade, migrate search_log/citation_audit schemas and
satisfy next_action/compliance/skill-receipt before syncing the whole framework.

### 2026-06-22 - Fix suppressed stale-triage command to a clean no-op sentinel

**Commit(s)**: `7321492`

**Action**: Surfaced by the first sync of the v2/v3 stale-triage into CMPD: real
suppressed stale items made `check_stale_triage` fail because `_classify` emitted a
full explanatory sentence as the `command` for `suppress_as_irrelevant`, while the
check (correctly) expects a no-op sentinel `"No action"`. Changed the suppress
branch to return `"No action"` (the explanation already lives in `rationale`) and
added a `_classify` suppress-branch test so this is caught in the template, which has
no real suppressed items.

**Alignment**: Keeps the deterministic triage contract honest — a suppressed item's
command must be a verifiable no-op, not prose that could be mistaken for an action.

**Non-goal**: No behavior change to bucketing/impact; purely the command-field
sentinel + a regression test.

**Drift risk**: Low. The rationale still carries the full suppression explanation.

**Next check**: Template checks only exercise 0-item triage; this test now covers
the suppress branch directly so the gap (only visible on a project with suppressed
items) cannot recur silently.

### 2026-06-22 - Implement Phase 2 of graph-propagated claim impact (depth-1 propagation + cap)

**Commit(s)**: `6ac6748`, `f1508c9` (IMPROVE-011 resolution_commit backfill)

**Action**: Implemented Phase 2 of the v3 design. Added
`_propagate_descendant_claims` (a stale task whose own outputs resolve to `none`
inherits claim impact from its **depth-1** dependents that resolve to
`specific_claims`) and `_cap_propagated_impact` (if propagation would cover every
active claim, report broad `registry_unknown` instead of a falsely specific list),
wired into `triage_stale_tasks`, surfaced via a new `impact_propagated_from`
field/line. Added five `check_stale_triage.py` cases. Validated read-only on CMPD:
`T003b_pipeline_instantiation` inherits from `T004_main_execution` and downgrades
to broad `registry_unknown`; all other ancestors stay `none` (one edge fired, no
cascade); paper task unchanged. Closes AEROS-IMPROVE-011.

**Alignment**: Completes the impact-localization story — a stale upstream task now
reflects the claims its direct downstream producer puts at risk, without the
"everything is high" flood, so the human reviews the right tasks.

**Non-goal**: Not full transitive-cone propagation (deliberately depth-1). Does not
change buckets/suppression, is not an LLM judgment, and never fabricates specific
claim IDs when the inherited set is broad (cap downgrades to registry_unknown).

**Drift risk**: Depth-1 could miss a multi-hop production chain (an indirect
producer two hops down). Accepted: missing a far edge yields a conservative `none`/
own-scope, never a false high; widening to bounded multi-hop would need a new cap
study before enabling. The all-active downgrade prevents fake precision.

**Next check**: On a project where a direct dependent produces a *subset* of claims
(CMPD's T004 produces all), confirm the parent inherits exactly that subset as
`specific_claims` with `impact_propagated_from` populated.

### 2026-06-21 - Implement Phase 1 of graph-propagated claim impact (registrar edge)

**Commit(s)**: `0c0ac5a`

**Action**: Implemented Phase 1 of the v3 design in
`aeros/runtime/stale_triage.py::_output_claim_impact`: a task that writes a
result/evidence registry (`result_index.csv`, `result_registry.csv`,
`evidence_ledger.csv`) now resolves its impacted claims to the concrete claim IDs
those registries link, instead of collapsing to an unscoped `registry_unknown`.
Added two `check_stale_triage.py` cases (registrar resolves linked claims;
empty registry stays `registry_unknown`). Validated read-only on CMPD:
`T004_main_execution` now resolves to `specific_claims [C1,C2,C3,C4]`; paper/audit/
pipeline tasks unchanged. Phase 2 (transitive descendant propagation) deferred.

**Alignment**: Closes the validated gap from the 2026-06-21 acid test — the sharp
claim attribution we built is no longer dormant for projects whose task outputs are
coarser than per-result paths. Tighter "which claims are at risk" without inventing
impact.

**Non-goal**: Not Phase 2. Does not propagate through the dependency graph to a
task's ancestors/descendants (the over-attribution risk), does not change buckets/
suppression, and is not an LLM judgment. Keeps the conservative `registry_unknown`
fallback when the registry links no claims.

**Drift risk**: The registrar edge attributes *all* registry-linked claims to the
registry writer. For a task that genuinely produces the whole index (CMPD T004)
this is correct; if a project splits "compute" and "register" into different tasks,
it labels the register-writer, not the compute task. Acceptable for an *impact*
(claims-at-risk) signal, not a rerun-target signal — re-check if Phase 2 lands.

**Next check**: When Phase 2 (descendant propagation) is built, enforce the cap +
frontier-band restriction and re-run the CMPD acid test to confirm ancestors of
T004 do not flood to high.

### 2026-06-21 - Design proposal: Graph-Propagated Claim Impact (stale-triage v3)

**Commit(s)**: `528810e`

**Action**: Wrote `docs/design/graph_propagated_claim_impact.md` (DESIGN, not
implemented) + backlog AEROS-IMPROVE-011, prompted by a read-only acid test of the
v2 stale-triage on CMPD's real G10 state: it discriminated correctly (1/18 high,
paper task de-escalated to `paper_global_review`) but no task hit `specific_claims`
— result-producing tasks fell back to `registry_unknown` because CMPD task outputs
are coarser than the result CSV paths. v3 resolves a task's claims via results it
(transitively) produces (research_graph + result_index), not only own-output string
match.

**Alignment**: Sharpens the impact ranking so a stale upstream task is attributed to
the *specific* claims its results feed — directly serving "claims stay within
evidence" and reducing both false-high noise and missed claim-bound risk.

**Non-goal**: Design only. Does not change buckets/suppression/volatile handling,
does not make impact an LLM judgment, and keeps the conservative `registry_unknown`
fallback when production mapping is ambiguous.

**Drift risk**: Graph propagation can over-attribute (a foundational task feeds
everything). Mitigation: direct production first, cap transitive propagation to the
frontier band, downgrade to `registry_unknown` past a claim count threshold.

**Next check**: After implementation, re-run the CMPD read-only acid test and
confirm result-producing tasks resolve to specific claims (C1/C2/C4) with no
regression to everything-high.

## 2026-06-20

### 2026-06-22 — Tighten bounded controller stop semantics

**Commit(s)**: `8690197`

**Action**: Tightened the bounded controller mental model. Renamed the misleading
`--until budget` stop to `--until max-steps`, clarified that this is a step-count
guard rather than a dollar budget guard, and split controller records into
`artifact_changed` and `substantive_changed` so real artifact movement under a
non-substantive label does not get counted as pure no-progress.

**Alignment**: Keeps `aeros run --until` conservative while making the control
surface say exactly what it does.

**Non-goal**: Does not implement real dollar-budget accounting, provider-cost
stopping, or broader autonomous task execution.

**Drift risk**: Existing notes or scripts using `--until budget` need to switch
to `--until max-steps`.

**Next check**: Run controller dry-runs and full harness; later wire real dollar
budget stops to provider/cost accounting if needed.

### 2026-06-22 — Add bounded deterministic controller loop

**Commit(s)**: `5b37c42`

**Action**: Added `aeros run --until human-gate|blocked|no-progress|max-steps`
as a bounded controller over the existing deterministic `aeros next`
projection. The loop executes only allowlisted safe preview/check commands by
default, refuses placeholders and shell syntax, stops at blockers/human
authority/no-progress/max-steps, and requires explicit `--allow-task-runs` before
turning iterate dry-runs into real task runs.

**Alignment**: Implements the new north star: AEROS may autonomously move until
it encounters authority, but it must not manufacture a paper or silently cross
human judgment boundaries.

**Non-goal**: Does not create an LLM planner, approve gates, upgrade claims,
certify identification, release artifacts, spend provider/API budget by default,
or turn route readiness into substantive progress.

**Drift risk**: The first version is intentionally conservative and may stop too
early when the next action contains placeholders or non-allowlisted commands.
That is preferable to silent cost, authority, or lane drift.

**Next check**: Run on CMPD in dry-run mode, then try one non-substantive
no-progress loop and confirm it stops instead of continuing to repair dashboards
or write packets indefinitely.

### 2026-06-22 — Add literature full-text candidate verification semantics

**Commit(s)**: `bb0db72`

**Action**: Added deterministic route/blocker semantics for candidate full-text
sources. OpenAlex/manual PDF URLs now enter the full-text queue as
`candidate_url_unverified` with `needs_verification` rather than being treated
as readable full text. Added content verification helpers for common false
positives such as Cloudflare/security challenge pages, login/CAPTCHA pages,
short SPA shells, non-PDF responses, and title/DOI mismatches. Expanded adapter
checks and literature policy so local cache/OA metadata cannot certify full-text
execution.

**Alignment**: Turns the CMPD retrieval failure into a template-level guardrail:
AEROS may find routes, but it must not confuse a route with target-paper text.

**Non-goal**: Does not bypass publisher access, fetch protected pages, OCR PDFs,
write extraction cards, certify citation faithfulness, synthesize literature,
support claims, or approve gates.

**Drift risk**: More candidates may remain in `needs_verification` or
`missing_fulltext` instead of appearing ready. This is intentional; it prevents
registry green lights without readable target-paper evidence.

**Next check**: Re-run on CMPD and confirm P013/P016/P030 are classified as
blocked or needs-verification without creating extraction cards or claim support.

### 2026-06-22 — Tighten Zotero full-text availability semantics

**Commit(s)**: `5fe6eb8`

**Action**: Refined the Zotero literature adapter so
`paper_registry.full_text_available=yes` is reserved for locally indexed/readable
text (`indexed_fulltext_chars > 0`). Zotero PDF attachments without indexed text
remain actionable in `fulltext_ready_queue.csv` as `pdf_attachment_only`, but do
not become registry-level full text. Added deterministic parser fixtures for
non-ISO dates, creator normalization, and attachment/fulltext classification.

**Alignment**: Keeps AEROS honest about literature execution: having a PDF is a
route to reading, not evidence that the paper text is readable or extracted.

**Non-goal**: Does not parse PDFs, OCR scanned attachments, write extraction
cards, produce synthesis, certify citation faithfulness, or support claims.

**Drift risk**: The stricter meaning may leave more rows at `full_text_available=no`
even when a PDF exists. That is intentional; the ready queue preserves the action
path without overstating evidence.

**Next check**: On a real project with Zotero PDFs, confirm indexed PDFs enter
`full_text_available=yes`, while scanned/PDF-only attachments remain
`pdf_attachment_only` until parsed/OCRed.

### 2026-06-22 — Add Zotero literature full-text queues

**Commit(s)**: `170b042`

**Action**: Added `zotero` as a local-library literature adapter. A Zotero search
can now register candidate papers, inspect local PDF/fulltext attachment
availability, route items with Zotero PDFs/indexed full text into
`discovery/literature/fulltext_ready_queue.csv`, and route items without detected
PDF attachments into `discovery/literature/missing_fulltext_queue.csv`.

**Alignment**: Connects the literature lane to the user's real library while
preserving AEROS's evidence boundary: local full-text availability becomes the
next executable route to extraction, not a completed literature review.

**Non-goal**: Does not bypass publisher access, OCR scanned PDFs, write
substantive extraction cards, certify citation faithfulness, produce synthesis,
support claims, or approve gates.

**Drift risk**: Agents could confuse "PDF found" with "paper read." The queues,
registry status, and checks keep Zotero output at ROUTE_READY until a real
full-text extraction card is written.

**Next check**: Run `aeros literature search --source zotero --query <topic>
--dry-run` on a real project, then import a small batch and confirm ready/missing
queues match actual Zotero attachments.

### 2026-06-21 — Tighten stale impact scopes

**Commit(s)**: `196f37a`

**Action**: Refined deterministic stale triage so paper/claim-registry outputs no
longer expand to all active claims unless a concrete result/evidence/graph path
localizes the affected claim IDs. Added `impact_scope` values
(`specific_claims`, `claim_registry_unknown`, `registry_unknown`,
`paper_global_review`, `none`), routed volatile-only output changes to
`recover --check`, and added synthetic checks for paper-localized impact,
unknown claim-registry impact, and volatile-output free revalidation.

**Alignment**: Preserves AEROS's conservative stale handling while preventing
"everything is high impact" noise. Claim-bound paths stay high when derived;
unknown registry changes stay high-risk but honest; paper changes without a
deterministic claim link become review-needed rather than fabricated claim impact.

**Non-goal**: Does not infer scientific importance, read paper prose, decide
which claims are true, mutate runtime state, downgrade claims, or approve gates.

**Drift risk**: Scope labels could be mistaken for proof of no impact. They are
only deterministic navigation aids; if a link cannot be localized, the system must
surface `unknown` rather than suppress.

**Next check**: On the next paper-stage project, create or observe a stale paper
artifact with one linked claim and verify triage lists only that claim, not every
active claim.

### 2026-06-20 - Design proposal: Claim Falsification Engine

**Commit(s)**: `6aeb40e`

**Action**: Wrote `docs/design/falsification_engine.md` (DESIGN, not implemented) and
backlog item AEROS-IMPROVE-005. Borrows AIGS's falsification-as-engine (L2 card): a
`FALSIFY <claim_id>` task in the analysis lane that runs a claim-type-aware attack
battery as registered spec runs, computes an attack-survival profile, and emits a
claim-ceiling *recommendation* — reusing spec_run_index, result_index/provenance,
negative_result_ledger, and the claim-ceiling compiler rather than new layers. Seeded
by `code/27_referee_robustness.py`; proven manually as this session's R1–R7 pressure
test, which found caveats the passive `T006_referee_panel` missed.

**Alignment**: Turns AEROS's passive robustness parts into an active, claim-targeted
falsifier and makes the claim ceiling a function of attack survival — directly serving
"claims stay within evidence." Also yields AEROS's first self-metric (claim-survival
rate), attacking its "no measured value" gap.

**Non-goal**: A *design*, not a feature — must not be cited as built. The engine may
lower/hold a ceiling autonomously but a raise or claim release stays human-gated; it
is not a truth oracle (surviving attacks ≠ true).

**Drift risk**: A fixed battery could be gamed (L4 reward-hacking warning) — mitigated
by a typed/extensible battery, registering the full attack denominator, and keeping
raises human-gated. Must enter via the kernel as a transition input, not a parallel
layer (Kernel Anti-Creep).

**Next check**: If approved, P0 = generalize 27_referee_robustness into a `falsify`
runner for the associational battery on CMPD C1/C2 (recommend-only), then validate.


### 2026-06-20 - Full-text extraction cards for AEROS related work (L1/L2/L4)

**Commit(s)**: `45bb195`

**Action**: Upgraded the related-work positioning from provisional to full-text:
extracted the real PDFs (pdftotext) of HLER (L1), AIGS (L2), and the creativity
survey (L4) and read them directly; wrote `docs/related_work_cards/L1_HLER.md`,
`L2_AIGS.md`, `L4_creativity_survey.md` with section/line-anchored evidence, and
updated the registry/synthesis to full_text depth.

**Alignment**: Demonstrates AEROS's literature rule paying off: real extraction
*corrected* two errors the machine summaries/snippets introduced — HLER's actual
human gates are "question selection + publication approval" (not the invented
"approval of novel theoretical claims"), and the creativity survey's verified risk
is "verifier reward-hacking / superficially-persuasive-without-being-correct" (not
the snippet's "plausible pseudo-science"). Abstract-level confidence would have
carried both errors forward.

**Non-goal**: Three full-text papers is a positioning sketch, not a systematic
review; L3/L5 stay at snippet level. Does not establish that any system (incl.
AEROS) produces *valid* findings — HLER metrics are feasibility/score, AIGS is a
self-described "baby-step" below human researchers.

**Drift risk**: Related-work can ossify into self-justification; keep it evidence-
anchored and re-open if it starts being cited as proof AEROS works.

**Next check**: If positioning goes into a paper/grant, run a pre-specified
systematic search rather than this opportunistic five-paper pass.


### 2026-06-20 - Related-work positioning of AEROS (provisional)

**Commit(s)**: `f5157f3`

**Action**: Ran the AEROS literature workflow (search → registry → extraction →
synthesis) on the autonomous-/LLM-research literature to locate AEROS's niche;
wrote `docs/related_work_autonomous_research.md`. Finding: the field already
imitates the staged research workflow (AI Scientist, Agent Laboratory, FARS), but
the literature's own consensus is that the bottleneck is *validation, not
generation* (the "plausible pseudo-science" risk), and few systems make an
integrity/admissibility layer first-class. Closest analogs: HLER (human-in-the-loop
econ) and AIGS (falsification-as-engine).

**Alignment**: Grounds AEROS's design bet (claim ceiling + evidence admissibility +
human gates) in external literature instead of self-assertion, and names concretely
what AEROS can borrow (AIGS falsification engine; HLER stage decomposition).

**Non-goal**: Not a systematic review; extraction stayed below AEROS's full-text
bar (2 of 5 fetched, machine-summarized). It is a positioning hypothesis, not a
verified gap claim — honestly graded as such in the doc.

**Drift risk**: A related-work doc could ossify into self-justification. Keep it
provisional and re-extract at full-text depth before it supports any formal claim.

**Next check**: If AEROS's positioning matters for a paper/grant, promote L1/L2/L4
to real full-text extraction cards and re-verify the table.


### 2026-06-20 - Framework failure-paths validated on CMPD

**Commit(s)**: `3818122`

**Action**: Closed two prior "Next check" items by exercising the *failure* paths
on the live CMPD project (not just synthetic/PASS paths). (1) **Large-file guard**:
staged a 101 MB tracked file → `check_no_large_files` and `check_git_guardrails`
both FAIL naming the file; unstaged, tree clean. (2) **v2 completion attestation**:
ran `aeros recover` on a throwaway task whose declared output cannot exist → the
contract's checks PASS but the v2 receipt is verdict=fail ("no substantive allowed
output artifact exists"), `recover` refuses, the task is NOT marked passed, and no
green receipt is issued. Throwaway fully removed; CMPD harness green afterward.

**Alignment**: Confirms the guardrails actually *block* the bad case on a real
project, which is what the prior entries promised but had only synthetic/PASS
evidence for. Completion stays honest: no real output → no pass.

**Non-goal**: One project, two paths; does not exhaustively fuzz every check.

**Drift risk**: None added; this is validation, not new capability.

**Next check**: Keep using CMPD (the designated validation project) to exercise new
guardrails' failure paths before declaring them validated.

### 2026-06-20 - Guard against unpushable large files (check_no_large_files)

**Commit(s)**: `fcd2fa5`

**Action**: Added `checks/check_no_large_files.py` and wired it into
`check_git_guardrails.py` (already in the harness runner). It fails if any
git-tracked file exceeds GitHub's 100 MiB hard limit, surfacing the problem in the
harness instead of at push time. Default threshold = 100 MiB (only fires on
genuinely unpushable files → zero false positives; LIMIT_MB is lowered easily for
stricter hygiene). Motivated by a real CMPD blocker: an autonomous run committed a
162 MB backup tarball that rejected the whole push and required a history rewrite.

**Alignment**: Keeps repos pushable and lean, and stops an autonomous run from
silently wedging a project's remote. A path-based `.gitignore` only helps if the
path matches; this check catches an oversized tracked file anywhere.

**Non-goal**: Does not scan deep history (only the current tracked tree), does not
auto-remove or LFS-migrate offenders, and does not replace `.gitignore` hygiene.

**Drift risk**: The 100 MiB default could let 50–100 MB files accumulate; projects
that care can lower LIMIT_MB. Keep it a size gate, not a data-policy engine.

**Next check**: After syncing a project, confirm a deliberately oversized tracked
file fails the harness and a normal tree passes.

### 2026-06-20 - Sync script takes project args (no hardcoded project list)

**Commit(s)**: `4ab2046`

**Action**: Rewrote `tools/sync_aeros_latest.zsh` to accept project paths as
arguments (`sync_aeros_latest.zsh <path> [<path>...]`) instead of three hardcoded
TARGETS lists (one bash + two python). No project list is baked in, so it works
for any current or future project. Targets without `project_manifest.yml` are
skipped with a warning; with no args it prints usage and exits 2. The single
hardcoded special case (preserve a project's custom AGENTS.md) is generalized to a
`.aeros_sync_keep_agents` sentinel file. The two python post-processors now read
the resolved targets from the `AEROS_SYNC_TARGETS` env var.

**Alignment**: Removes a maintenance trap and a footgun — the old list went stale
as projects were added, and "run the script" silently synced 10 projects at once
(risking clobbering uncommitted WIP in projects the user wasn't thinking about).
Per-project invocation makes propagation deliberate and safe.

**Non-goal**: Does not auto-discover projects (deliberate — explicit paths only,
so a sync never surprises a project with WIP). Does not change what is synced.

**Drift risk**: Per-project syncing could let some projects fall behind if the
user forgets them. Mitigation: the user owns propagation timing; falling behind is
visible via a framework `diff -rq` against the template.

**Next check**: On the next framework change, sync one project by path and confirm
only that project changes and its harness stays green.

### 2026-06-20 - Reconcile framework drift: port CMPD improvements up

**Commit(s)**: `0c5fdce`

**Action**: Closed bidirectional drift between the template and the CMPD vendored
copy. Ported two CMPD-only framework improvements *up* to the template before
syncing down: (1) `aeros/runtime/skill_receipt.py` auto-writes a
`mechanical_revalidation` skill waiver when a task declares recommended skills but
the receipt is a check-only revalidation with no skills used; (2)
`checks/build_agent_runs_index.py` uses `lineterminator="\n"` + byte-exact compare
for deterministic index writing. The remaining diverged files (skill_router,
skill_registry/invocation/menu, check_skill_layer) were template-ahead and go down
via the forward-only sync.

**Alignment**: Restores the single-source-of-truth invariant — the framework lives
in the template and projects vendor it. CMPD had drifted *ahead* on skill_receipt
(the auto-waiver used during its v2 receipt migration), which a naive sync would
have destroyed; porting up first prevents that loss.

**Non-goal**: Does not relocate project-owned files that live under `aeros/`
(project_contract.yml, task_registry.csv, state/, and CMPD-specific gate_map /
replication_guardrails / status_board) — per Framework Propagation Discipline the
sync tolerates these and they must not be moved.

**Drift risk**: Bidirectional drift recurs whenever framework code is hand-edited
inside a project. Mitigation is procedural: develop framework changes in the
template, propagate only via `tools/sync_aeros_latest.zsh`.

**Next check**: After syncing CMPD, confirm `diff -rq` of aeros/checks/harness
(excluding project-owned files) is clean and both harnesses stay green.


### 2026-06-20 - Completion attestation v2 validated on a real project

**Commit(s)**: `30dd9fb` (template ledger note); rollout landed in CMPD as `f69fcdd3` + `275c85ee`

**Action**: Ran the v2 completion-attestation feature end to end on a real project (CMPD). Confirmed the migration path: 17 legacy v1 receipts were regenerated to v2 via `aeros recover <task> --check` (each task's own checks re-run and passed), and `recover` auto-wrote `mechanical_revalidation` skill waivers for tasks declaring recommended skills. Final state: 18/18 v2 receipts, full harness green.

**Alignment**: Closes the prior entry's "Next check". The v2 layer is now evidence-backed on a live project, not just wired and template-tested. Concretely demonstrated both halves: a passed task writes a valid v2 receipt, and a legacy v1 receipt fails cleanly with `legacy version <2`.

**Non-goal**: Validates the `recover`/revalidation migration path on one project; does not certify CMPD's research conclusions, and does not prove the path generalizes to projects whose task checks fail under v2 (those correctly will not recover).

**Drift risk**: Two real gotchas surfaced and should be watched on the next rollout: (1) introducing v2 turns every downstream project's existing v1 receipts red until migrated — sync must be paired with a `recover` pass; (2) a stale `.pyc` left a skill waiver empty on first recover, so a clean run (or pyc clear) may be needed.

**Next check**: On a project where some task's checks legitimately fail under v2, confirm `recover` refuses it and the task stays non-passed with an honest status rather than getting a green receipt.

## 2026-06-19

### 2026-06-19 - Lightweight completion attestation

**Commit(s)**: `203f9c0`

**Action**: Upgraded task completion from a generic receipt into a version-2 minimal attestation. New receipts record active lane, declared outcome, substantive allowed outputs, file hashes when applicable, check commands, exit codes, and explicit boundaries for what completion does not prove. Added a compact completion attestation policy/template and wired it into AGENTS, run-report guidance, project manifest, sync, and init scaffolding.

**Alignment**: Prevents agents from claiming "complete" from a filled run report or vague check summary, while keeping the rule small and mechanical. Completion proves process evidence, not scientific truth.

**Non-goal**: Does not decide whether results are true, identification is strong, claims are supported, or gates are approved.

**Drift risk**: Completion receipts could become paperwork if fields expand beyond mechanical evidence. Keep this layer limited to outputs, hashes, commands, exit codes, and boundaries.

**Next check**: On the next real task recovery, confirm a passed task writes a version-2 receipt and that legacy or output-free completions fail cleanly.

### 2026-06-19 - External economics tool registry and replication alignment

**Commit(s)**: `99937bd`

**Action**: Added an external economics tool registry and advisory boundaries for OpenAlex, CitEc/RePEc, pyBiblioNet, PreprintResolver, AEA Data Editor guidance, OpenSourceEconomics, Econstellar, Econometrics-Agent, Causal-Copilot, and CausalAgent. Added econ literature discovery adapter policy, AEA replication alignment policy/template/check, external-tool registry check, and optional Econstellar-style reproducibility metadata in the result registry.

**Alignment**: Lets AEROS borrow strong economics-specific infrastructure without turning external tools into truth sources. Literature adapters generate candidates, AEA guidance aligns replication packaging, endpoint metadata improves result reproducibility, and causal/econometrics agents remain advisory.

**Non-goal**: Does not implement live API adapters, certify AEA acceptance, certify identification, upgrade claims, or replace full-text extraction, result provenance, human gates, or AEROS checks.

**Drift risk**: The registry could become an ever-growing tool catalog. Keep tools registered only when they map to a lane, output artifact, and explicit forbidden uses.

**Next check**: In the next economics project, use OpenAlex/CitEc/PreprintResolver only to produce candidate literature artifacts, and use AEA alignment only as a package checklist before human release review.

### 2026-06-19 - Unified evidence delta ledger

**Commit(s)**: `8559333`

**Action**: Added the thin evidence-delta ledger: one shared `evidence/delta_log.jsonl` across all lanes, `aeros delta append/list`, `templates/evidence_delta_record.json`, and `checks/check_evidence_delta_log.py`. Wired it into AGENTS, the run-report template, default harness, project manifest, init scaffold, sync script, and derived-vs-asserted audit.

**Alignment**: Captures the insight that literature and data grow incrementally rather than becoming "done" in one pass. Each lane run can now record what evidence changed, what coverage moved, what gaps remain, and the next best increment, without spawning per-lane ledgers.

**Non-goal**: Does not approve gates, support claims by itself, or replace provenance, the research graph, result registry, or action receipts. It is a progress trace, not empirical evidence.

**Drift risk**: Delta logging could become paperwork if agents append vague records without artifacts or next increments. The check requires concrete fields and artifact references for non-blocked/non-insufficient deltas.

**Next check**: In the next real data or literature lane run, append one delta and confirm it helps explain the increment without creating separate data/literature ledger files.

### 2026-06-19 - Work lane router for separated research surfaces

**Commit(s)**: `18c2e34`

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

### 2026-06-21 — Add fast profiles, stale context, and cockpit view

**Commit(s)**: `a6da765`

**Action**: Added `harness/check_profiles.yml`, runner `--profile`, `aeros check --profile`, context stale detection, lightweight `outputs/context/context_graph.yml`, and `aeros cockpit` as the one-command daily dashboard over context + next + fast-check guidance. Also aligned `check_update_ledger.py` with AGENTS by allowing `pending` only while the worktree is dirty, and scoped paper/compliance hard gates out of root template mode while preserving them for real projects; fixed the econ literature discovery policy YAML so full harness can parse the literature adapter policy; removed the remaining hardcoded local Python path from next-action fallback and made controller iterate recommendations default to --dry-run so `aeros next` stays advisory.

**Alignment**: Keeps AEROS's rigorous internal guardrails while lowering day-to-day cognitive load. This follows the north star from recent validation: agents need deterministic context and next-action projection, not more free-form memory or a paper-factory loop.

**Non-goal**: Does not remove any full harness check, approve gates, certify claims, or turn route/readiness output into substantive research progress.

**Drift risk**: A profile could be misread as a complete validation. AGENTS now states profiles are latency controls only; full harness remains required for release/internal-control checkpoints.

**Next check**: Use `aeros cockpit --lane data`, `aeros check --profile smoke`, and at least one real-project lane profile to confirm the light cockpit helps agents stop at the right blocker instead of empty-running.

### 2026-06-21 — Add deterministic stale impact triage

**Commit(s)**: `a6da765`

**Action**: Added `aeros stale triage --dry-run` plus a runtime triage module and check. `aeros next` now consumes triage so stale tasks are classified into `rerun_required`, `revalidate_free`, or `suppress_as_irrelevant` before recommending a command.

**Alignment**: Keeps NEXT_ACTION deterministic and cheap-first. Stale no longer automatically means provider/API rerun; unchanged outputs route to `recover --check`, claim-bound paths are highlighted, and irrelevant stale noise is suppressed only when graph/DAG/fingerprint evidence proves it is unrelated.

**Non-goal**: Does not use LLM ranking, certify scientific importance, change runtime state, mark tasks stale, downgrade claims, approve gates, or replace full harness/research graph checks.

**Drift risk**: Suppression can become dangerous if the proof rule weakens. Keep the rule conservative: if no proof of irrelevance, surface the stale item.

**Next check**: Run on CMPD and one newer data-heavy project to confirm stale upstream tasks route to `recover --check` when outputs are unchanged and still high-light claim-bound stale paths.

### 2026-06-22 — Add typed ActionSpec v0 for next-action control

**Commit(s)**: `1376748`

**Action**: Added a typed `ActionSpec` runtime model and wired it into `aeros next`, `aeros run --until`, `checks/check_next_action.py`, templates, and AGENTS. `aeros next` still renders a command for human convenience, but the typed ActionSpec now records the action kind, effect class, capabilities, decision requirement, expected outputs, acceptance checks, and zero-cost/resource boundary.

**Alignment**: Shrinks the controller authority surface. The command string is no longer the implicit truth of the next action; it is a compatibility preview behind a typed, deterministic control record and the existing allowlist executor.

**Non-goal**: Does not migrate project state to SQLite, remove existing CLI commands, approve gates, run real tasks without `--allow-task-runs`, certify identification, upgrade claims, or replace human decisions.

**Drift risk**: ActionSpec can become decorative if future code ignores it and executes rendered command strings directly. Keep `check_next_action.py` enforcing ActionSpec presence/consistency and keep bounded controllers validating the spec before command parsing.

**Next check**: Run `python3 checks/check_next_action.py`, `python3 -m aeros.cli next`, and `python3 -m aeros.cli run --until no-progress --dry-run --json` after this edit to confirm controller records carry ActionSpec and stop on decisions/placeholders.

### 2026-06-22 — Tighten controller budgets, semantic progress, and completion fields

**Commit(s)**: `1376748`

**Action**: Extended the bounded controller with always-on resource/safety accounting: max actions, wall-time seconds, provider-call budget, cost budget, semantic state hashes, frontier hashes, action signatures, cycle detection, semantic progress flags, and `primary_stop_reason`. Updated completion receipts to write orthogonal fields: `outcome_kind`, `contract_status`, `verification_level`, `progress_class`, and `authority_status`. Renamed the preferred substantive outcome label from `SUBSTANTIVE_DONE` to `SUBSTANTIVE_PRODUCED` while preserving `SUBSTANTIVE_DONE` as a deprecated compatibility alias in runtime/check code.

**Alignment**: Moves AEROS away from "file changed therefore progress" and toward deterministic semantic control state. Completion now separates what happened, whether the contract passed, how it was verified, whether substance was produced, and whether authority was involved.

**Non-goal**: Does not migrate state to SQLite, make scientific validity judgments, execute provider calls by default, approve gates, upgrade claims, or mark old v2 receipts invalid.

**Drift risk**: Semantic hashes can become too coarse or too broad. Keep them focused on state/frontier/blocker/registry surfaces, not volatile logs. Keep `SUBSTANTIVE_DONE` only as a compatibility alias, not a new primary label.

**Next check**: Run `python3 checks/check_next_action.py`, `python3 checks/check_completion_receipts.py`, and `python3 -m aeros.cli run --until no-progress --dry-run --json` to confirm controller records expose semantic/cycle fields and template receipts remain compatible.

### 2026-06-22 — Mark ActionSpec as Phase 1 shim and add direct invariants check

**Commit(s)**: `1376748`

**Action**: Added `checks/check_action_spec.py` and wired it into the harness/profile/manifest control plane. Corrected completion `progress_class` so it is a category (`substantive`) rather than the rendered label (`SUBSTANTIVE_PRODUCED`), while adding `progress_label` for display. Added `docs/design/action_spec_inversion_plan.md` and AEROS-IMPROVE-018 to make the Phase 2 inversion explicit.

**Alignment**: Keeps the ActionSpec work honest. Phase 1 is a useful safety shim, but not the final inversion: command strings still render first and specs are inferred. The backlog now tracks the required next step so `_infer_kind` does not become the resting architecture.

**Non-goal**: Does not invert all next-action producers yet, does not remove command rendering, does not sync to CMPD, and does not make ActionSpec a gate/claim authority.

**Drift risk**: If future work treats Phase 1 as complete, AEROS keeps two string parsers and preserves command-string fragility. Close AEROS-IMPROVE-018 only after producers construct typed ActionSpecs directly and commands become renderings.

**Next check**: Run `python3 checks/check_action_spec.py` and full harness after this edit. Then commit in template before syncing to active projects.

### 2026-06-22 — Implement ActionSpec Phase 2 producer inversion

**Commit(s)**: `1376748`

**Action**: Inverted `aeros.runtime.next_action` producers so internal next-action branches construct declared ActionSpecs directly (`producer_mode: declared`) instead of deriving kind/effect from rendered command substrings. `check_next_action.py` now fails if computed next actions use inferred compatibility specs. `action_spec_from_next()` remains only for old/bare NextAction compatibility and marks those specs as `producer_mode: inferred_compat`.

**Alignment**: Removes command-string authority from the next-action producer layer. Commands still render for compatibility, but the typed control semantics now originate in the branch that knows the lane, kind, effect class, and authority boundary.

**Non-goal**: Does not remove command rendering, does not remove the executor allowlist, does not migrate state to SQLite, and does not sync real projects automatically.

**Drift risk**: Future branches could bypass `_next_action()` and construct bare NextAction objects. `check_next_action.py` now protects computed actions, but code review should keep producer declarations mandatory.

**Next check**: Run `python3 checks/check_action_spec.py`, `python3 checks/check_next_action.py`, and full harness; then commit template before syncing CMPD.

### 2026-06-22 — Add ActionSpec inferred-compat retirement trigger

**Commit(s)**: `aff9ec9`

**Action**: Added AEROS-IMPROVE-020 and documented the retirement trigger for `action_spec_from_next()` / `_infer_kind()`. The inferred compatibility path remains allowed only for old/bare NextAction callers and should be removed once template and active downstream projects report `producer_mode: declared` in normal next-action and bounded-controller output.

**Alignment**: Prevents the old command-string parser from becoming permanent architecture after producer inversion. This keeps Phase 2 honest without forcing a risky immediate deletion while downstream projects are still syncing.

**Non-goal**: Does not remove `_infer_kind()` today, does not change executor dispatch, and does not sync CMPD or other projects.

**Drift risk**: If no retirement trigger is enforced, inferred_compat may remain dormant-but-maintained debt. The trigger should be checked after downstream projects are green on declared specs.

**Next check**: After each framework sync, confirm `check_next_action.py` and `aeros run --until no-progress --dry-run --json` report `producer_mode: declared` in normal controller output.

### 2026-06-22 — Add post-pipeline reconciliation command and runtime-aware pipeline check

**Commit(s)**: `aff9ec9`

**Action**: Added `aeros reconcile` as a deterministic, low-authority post-pipeline
sync command. It can refresh result-index/provenance/research-graph/global-state
projections and write an `outputs/logs/aeros_reconcile_*.md` report that states
what reconciliation does not prove. Updated `check_pipeline_runs.py` so delegated
pipeline run mode honors `automation.pipeline.command` and
`automation.pipeline.runtime.python` (or `AEROS_PIPELINE_PYTHON`) instead of
silently falling back to the current interpreter/master-script path.

**Alignment**: Turns the real CMPD friction into a repeatable control-plane step:
pipeline output changes trigger derived-index sync through one auditable command
instead of three remembered manual commands, while keeping claim/gate authority
separate.

**Non-goal**: Does not run the research pipeline, recover stale tasks, approve gates,
upgrade claims, validate scientific correctness, install dependencies, or guarantee
cross-machine environment reproducibility.

**Drift risk**: Reconcile could be mistaken for evidence validation. Mitigation:
the command/report/check all label `does_not_prove`, and AGENTS.md says reconcile is
a projection refresh only.

**Next check**: On CMPD after the next real pipeline run, run `python3 -m aeros.cli
reconcile`, then full harness, and confirm no manual provenance/graph/state sync is
needed.

### 2026-06-22 — Add session scope guard for chat-driven lane drift

**Commit(s)**: `849632f`

**Action**: Added `aeros session start/status/audit`, `SESSION_CONTRACT.yml`
template, `harness/session_scope.yml`, and `check_session_scope.py`. A session
declares one active lane/objective, max actions, allowed prefixes, forbidden
prefixes, and stop conditions. `aeros session audit` compares the current diff to
that scope and reports `SCOPE_DRIFT` for off-lane edits.

**Alignment**: Turns the recurring chat problem ("I asked for data, the agent
wandered into literature/harness/writing") into a mechanical, reviewable boundary
without adding another research authority layer.

**Non-goal**: Does not execute work, approve gates, revert files automatically,
certify research substance, or make cross-lane work impossible when explicitly
approved by the human.

**Drift risk**: File allowlists can become either too strict or too broad. Keep the
guard as advisory/auditable scope control and refine lane prefixes only after real
project audits show false positives/negatives.

**Next check**: In CMPD or the next active project, start a data session, make one
allowed data edit and one intentionally off-scope paper edit, then confirm
`aeros session audit` reports only the paper edit as `SCOPE_DRIFT`.

### 2026-06-22 — Consolidate runtime contracts with ExecutionProfile and semantic scope audit

**Commit(s)**: `e783c77`

**Action**: Added `ExecutionProfile` v1 and wired pipeline checks to resolve a
named profile from `project_manifest.yml`. Extended ActionSpec with runtime profile,
authority boundary, semantic progress predicates, post-run hooks, and reversal
policy. Successful delegated pipeline runs and controller task-run hooks can now
run low-authority reconcile automatically. Session scope audit now emits semantic
artifact classifications and verdicts (`SCOPE_DRIFT`, `CLAIM_SCOPE_DRIFT`,
`AUTHORITY_DRIFT`) rather than only a path allowlist pass/fail.

**Alignment**: Moves AEROS from "more commands to remember" toward contract-bound
runtime semantics. Reconcile and session guard remain user-callable repair/debug
tools, but normal execution can attach them as hooks to typed actions/profiles.

**Non-goal**: Does not migrate canonical state to SQLite, add new lanes, introduce
parser adapters, run external providers, approve gates, upgrade claims, or certify
scientific validity.

**Drift risk**: Post-run hooks could be mistaken for evidence validation, and semantic
scope labels can become too broad. Mitigation: hooks are low-authority, `does_not_prove`
boundaries remain explicit, and session verdicts distinguish authority drift from
ordinary support changes.

**Next check**: In a real project, run one pipeline through an ExecutionProfile with
`post_run_hooks: [reconcile]`, then start a data session and confirm a paper/claim edit
is labeled `CLAIM_SCOPE_DRIFT` or `AUTHORITY_DRIFT`.

### 2026-06-22 — Add second-batch research contract scaffolds

**Commit(s)**: `e783c77`

**Action**: Added lightweight scaffolds and checks for EstimandDataContract,
EvidenceUnit, parser benchmark, adversarial benchmark, and readiness vector.
Added `aeros readiness` as a derived cockpit projection and wired the new checks
into the manifest and relevant check profiles.

**Alignment**: Implements the second batch as contract/projection infrastructure,
not another authority layer. EstimandDataContract constrains data feasibility
questions, EvidenceUnit makes literature evidence addressable, benchmarks test
known failure modes, and readiness gives a compact lane-level view.

**Non-goal**: Does not certify data availability, identification quality,
full-text synthesis, parser correctness outside fixtures, absence of unknown
failure modes, claim support, gate approval, paper readiness, or public release.

**Drift risk**: These concepts can become bureaucratic if treated as required
paperwork before they are needed. Keep them minimal, derived/advisory by default,
and promote only project-specific workflows that prove useful in real projects.

**Next check**: Run the five new checks plus `python3 -m aeros.cli readiness` on
the template, then pressure-test on one real project before expanding their
schemas.

### 2026-06-22 — Expose ActionSpec through `aeros next --json`

**Commit(s)**: `e783c77`

**Action**: Added `--json` to `aeros next` so the primary next-action producer
emits the full `NextAction.to_dict()` payload, including the declared
`ActionSpec`. Added `action_spec_producer_mode` to the human text view and
extended `check_next_action.py` to exercise `aeros next --json` through the CLI.

**Alignment**: Keeps ActionSpec as the machine-consumable control object instead
of hiding it behind a rendered command string. This closes the inconsistency
where `aeros run --json` exposed typed contracts but `aeros next` did not.

**Non-goal**: Does not change execution dispatch, approve gates, run tasks,
remove inferred compatibility for old callers, or certify the scientific value
of the recommended action.

**Drift risk**: Future output fields could diverge between human and JSON views.
Keep `check_next_action.py` exercising the CLI JSON path directly.

**Next check**: Run `python3 checks/check_next_action.py` and
`python3 -m aeros.cli next --json`.

### 2026-06-22 — Add first executable adversarial benchmark slice

**Commit(s)**: `3b16b2d`

**Action**: Converted `exit_zero_no_output` from a named adversarial scenario
into an executable fixture. The benchmark now runs a script that exits 0 without
creating its declared output, builds a temporary project state that falsely marks
the task passed, and requires `check_noop_runs.py` to detect the false
completion. Also labeled draft EstimandDataContract and parser benchmark checks
as `scaffold_only` when no real evidence/parser fixtures are active.

**Alignment**: Moves the second-batch benchmark layer from pure schema validation
toward real detection-rate evidence, while keeping the scope intentionally small.
This directly addresses the scaffold-green risk without adding a seventh
horizontal module.

**Non-goal**: Does not execute all adversarial scenarios, prove absence of unknown
failures, validate parser quality, certify data availability, bind CMPD C1 to an
estimand contract, approve gates, or certify claim support.

**Drift risk**: One fixture can be mistaken for a complete adversarial benchmark.
Keep remaining scenarios visibly scaffold-only until each has an executable
fixture and detection assertion.

**Next check**: Run `python3 checks/check_adversarial_benchmark.py` and smoke
profile; then add a real EstimandDataContract vertical slice in a project before
expanding more scaffolds.

### 2026-06-23 — Add stale-registry and session-scope adversarial fixtures

**Commit(s)**: `ff63b77`

**Action**: Added an executable `stale_registry` fixture that mutates a registered
result artifact after provenance is recorded and requires `check_provenance.py`
to detect the sha256 mismatch. Extended `check_session_scope.py` with semantic
fixtures that create temporary git projects, start a data session, modify
`paper/draft.md` and `evidence/claim_registry.md`, and require
`CLAIM_SCOPE_DRIFT` / `AUTHORITY_DRIFT` verdicts.

**Alignment**: Continues the vertical-slice correction: adversarial scenarios now
prove concrete detector behavior rather than merely listing failure names. It
also proves the session guard's semantic drift labels are behavioral, not just
taxonomy strings.

**Non-goal**: Does not implement all adversarial scenarios, sync real projects,
prove absence of unknown failures, decide claim validity, or replace human gate
judgment.

**Drift risk**: Fixture checks can become brittle if they rely on incidental git
output or broad path rules. Keep each fixture small, deterministic, and tied to
one expected detector.

**Next check**: Run `python3 checks/check_session_scope.py`,
`python3 checks/check_adversarial_benchmark.py`, and smoke profile; then add
`false_fulltext` as the next executable fixture.

### 2026-06-23 — Keep next-action smoke checks fast in instantiated projects

**Commit(s)**: `f20331f`

**Action**: Adjusted `check_next_action.py` so the expensive lane-matrix
traversal still runs in the root template but is skipped in instantiated
projects. Instantiated projects still validate the default next action, CLI JSON
ActionSpec, producer mode, and bounded-controller safety records.

**Alignment**: Keeps smoke profiles useful as a fast cockpit check in real
projects. The check remains a contract-surface guard instead of becoming a
full-lane planning benchmark on every project.

**Non-goal**: Does not change `aeros next` recommendations, weaken ActionSpec
validation, skip controller safety checks, or certify scientific progress.

**Drift risk**: Project-specific lane bugs could be missed by smoke. Use lane
profiles or full harness when changing lane routing; keep smoke focused on fast
control-plane health.

**Next check**: Re-sync CMPD and rerun `python -m aeros.cli check --profile smoke
--timeout 20`.

### 2026-06-23 — Execute remaining adversarial/parser benchmark slices

**Commit(s)**: `c5db397`

**Action**: Converted `false_fulltext`, `claim_ceiling_escape`, and
`stale_human_approval` from named adversarial scenarios into executable fixtures.
Added `check_approval_freshness.py` as a narrow opt-in guard for artifact-bound
human approvals, and changed the parser benchmark from scaffold-only to a local
HTML working-paper fixture that must recover title, DOI, and table text.

**Alignment**: Finishes the first adversarial-benchmark vertical slice set without
adding a broad new lane. Each fixture has a concrete detector: fake full text is
blocked by the literature verifier, over-claiming is caught by the claim-ceiling
check, stale approvals are caught by artifact hash binding, stale registry is
caught by provenance, and parser quality is no longer an empty schema check.

**Non-goal**: Does not prove full parser quality, run external PDF/OCR adapters,
approve human gates, certify claim truth, validate scientific identification, or
guarantee that unknown adversarial failures are detected.

**Drift risk**: Synthetic fixtures can become too easy. Keep future benchmark
growth tied to real-project failures such as false full-text pages, stale
registered outputs, and stale approval reuse.

**Next check**: Run adversarial/parser/approval checks in the template, sync into
CMPD, run CMPD smoke, and add a real CMPD C1 EstimandDataContract vertical slice.

### 2026-06-23 — Make sync postprocessors use the configured project Python

**Commit(s)**: `a264cfe`

**Action**: Updated `tools/sync_aeros_latest.zsh` so post-sync YAML/Python
postprocessors run with `AEROS_SYNC_PYTHON`, defaulting to the local Anaconda
Python when available before falling back to `python3`.

**Alignment**: Fixes a real CMPD rollout failure where system `python3` lacked
PyYAML. This keeps template-to-project sync deterministic across the same local
runtime used by AEROS checks.

**Non-goal**: Does not install dependencies, change project research artifacts,
approve gates, run pipelines, or certify downstream project health.

**Drift risk**: Projects with a different Python layout may need to set
`AEROS_SYNC_PYTHON` explicitly. The script remains a sync helper, not a package
manager.

**Next check**: Re-run sync on a real project and then run its smoke profile.

### 2026-06-23 — Sync parser benchmark fixtures into projects

**Commit(s)**: `ebe5d8e`

**Action**: Updated `tools/sync_aeros_latest.zsh` to create and copy
`tests/parser/` alongside `tests/adversarial/` so parser benchmark fixtures added
in the template are available in instantiated projects.

**Alignment**: Closes the CMPD rollout gap where the parser benchmark contract was
synced but its local HTML fixture was not, causing a project-side targeted check
failure despite template smoke passing.

**Non-goal**: Does not run parser adapters, certify parser quality, change project
research content, approve gates, or weaken project checks.

**Drift risk**: Any future fixture directory must be added to sync deliberately;
otherwise checks can reference template-only files.

**Next check**: Re-sync CMPD and rerun `checks/check_parser_benchmark.py`.

### 2026-07-02 — Right-size execution mode and canonical staging controls

**Commit(s)**: `35d9830`

**Action**: Added an advisory `aeros mode recommend` selector for smoke/probe/source/release/API/waiting modes, a source-id consistency check across data contract/inventory/provenance/result registry surfaces, and `aeros artifact stage --canonical --exclude-raw-staging` to separate canonical outputs from raw/staging captures before commits.

**Alignment**: Reduces chat-driven overgovernance and empty running by making the next governance shell explicit, catches source-id drift before data gaps become misleading, and keeps project commits from mixing canonical outputs with raw captures.

**Non-goal**: Does not approve gates, certify claim support, decide scientific validity, run source capture, or make raw staging files safe for public release.

**Drift risk**: Execution modes could become another policy surface if used as authority instead of advice. The artifact selector must stay a conservative staging helper, not a replacement for human review before commit.

**Next check**: Sync into SNAP or another active project and verify that smoke-test work stays light while source-capture/staging work is not mislabeled as substantive evidence.

### 2026-07-02 — Add Skill Obligation Layer

**Commit(s)**: `b5c18dc`

**Action**: Added a skill obligation policy, runtime helper, and `check_skill_coverage.py` so skill-eligible tasks must either declare relevant skills, mark a required skill class, or record an explicit waiver/blocker. Runtime skill receipts now record obligations and waivers instead of silently treating empty skill use as sufficient.

**Alignment**: Turns skills from optional suggestions into auditable professional inputs while preserving AEROS authority boundaries: skills may assist, but they do not approve gates, certify claims, or prove scientific validity.

**Non-goal**: Does not force every task to invoke an external skill, does not run skills automatically, does not certify skill output quality, and does not convert skill use into substantive research progress.

**Drift risk**: If obligation inference becomes too broad, it can create bureaucratic false positives. Keep inference conservative: tasks with explicit skill declarations, required classes, or waivers should not receive extra inferred obligations.

**Next check**: Sync into a real active project and verify that data/source/literature/writing tasks either use the relevant skill path or carry an explicit waiver, without making smoke-test work heavy.

### 2026-07-03 — Add harness-observed receipts and protected-path commit guard

**Commit(s)**: `66be934`

**Action**: Added a harness-generated observed receipt path for
`checks/run_harness_checks.py` plus a protected-path pre-commit hook template and
installer. The observed receipt records check exit codes, output tails, key
source-file hashes, and explicit `does_not_prove` boundaries. The hook blocks
protected staged files by default and requires an explicit human override
environment variable for approved protected commits.

**Alignment**: Reduces reliance on agent self-attestation for mechanical check
evidence and upgrades the highest-risk `must_not_touch` paths from advisory
text to an opt-in local enforcement layer.

**Non-goal**: Does not certify scientific validity, data truth, claim support,
paper readiness, gate approval, or the correctness of protected edits. The hook
is not auto-installed by sync/init and does not replace human gate review.

**Drift risk**: Observed receipts can become local clutter if treated as
committed artifacts by default, so generated receipt JSON is ignored unless a
project deliberately promotes it. The hook can be bypassed by a human override;
that is intentional but should be paired with an approval record.

**Next check**: Run the new receipt and hook checks, then smoke/full harness.
If committed, backfill this pending entry with the framework commit hash.

### 2026-07-03 — Add ledger hash-chain, evidence sufficiency audit, and AEA 2026 alignment refresh

**Commit(s)**: `66be934`

**Action**: Added a local update-ledger hash-chain policy/check, an evidence
sufficiency audit policy/template/check covering the eight governance dimensions
(`actor`, `authority`, `action`, `policy`, `decision_basis`,
`resource_access`, `lifecycle`, `verification_strength`), and refreshed the AEA
replication policy/template/check against the February 2026 AEA Data and Code
Availability Policy plus the 2026 Papers & Proceedings replication-package
guidance.

**Alignment**: Reduces ledger drift risk, makes governance evidence explain what
kind of basis it actually records, and keeps AEROS replication readiness aligned
with the current AEA-style external standard without confusing schema alignment
with journal acceptance.

**Non-goal**: Does not provide a signed transparency log, prevent a malicious
actor from rewriting both ledger and chain, certify scientific validity, certify
claim support, approve gates, prove evidence sufficiency for a conclusion, or
certify AEA/Data Editor acceptance.

**Drift risk**: The hash-chain is local and must be regenerated whenever the
ledger changes. Evidence sufficiency dimensions can become checklist theater if
used as proof of truth rather than proof of record completeness. AEA policy
references need periodic source review as external guidance changes.

**Next check**: Run hash-chain, evidence sufficiency, AEA alignment, smoke, and
full harness checks. If committed, backfill this pending entry and refresh the
chain record against the final ledger hash.

### 2026-07-03 — Tighten sync-doctor and governance-enforcement meta checks

**Commit(s)**: `80671d7`

**Action**: Added a sync-doctor meta-check requiring every check in
`harness/check_profiles.yml` to appear in sync-doctor `CAPABILITIES` or an
explicit exemption list, added the newly introduced governance capabilities to
sync doctor, made the protected-path hook check warn when the hook is not
installed in the current repo, checked protected-path policy strings against the
hook script, and tightened the ledger hash-chain check to require append-only
growth relative to `HEAD`.

**Alignment**: Addresses the repeated class of omissions where new template
capabilities are added but not exposed through sync doctor, keeps hook policy
and implementation from silently drifting, and makes ledger-chain history harder
to rewrite accidentally.

**Non-goal**: Does not auto-install hooks into downstream projects, force every
profile check to become a sync-doctor capability, create a signed transparency
log, or prove scientific validity, claim support, gate approval, or evidence
sufficiency.

**Drift risk**: The explicit sync-doctor exemption list can become stale or too
broad if maintainers use it as a shortcut. Hook installation remains opt-in, so
projects still need a human to install the local pre-commit guard when desired.

**Next check**: Run sync doctor, protected hook, ledger hash-chain, improvement
backlog, smoke, and full harness checks. If committed, backfill this pending
entry and append a new hash-chain record.

### 2026-07-03 — Add broad-capture low-audit lead mode

**Commit(s)**: `8237be8`

**Action**: Added `broad_capture` as a low-governance execution/task mode for
early lead sweeps, added `lead_queue` and `candidate_queue` output intents,
added a `broad_capture_leads` workflow preset, and introduced a
`check_broad_capture_firewall.py` fixture that allows writes to isolated
lead/candidate queue surfaces while rejecting `data/raw`, `data/intermediate`,
`data/processed`, claim registry, paper, release, approval, and replication
surfaces.

**Alignment**: Implements the "wide in/wide out, strict on promotion" rule:
capture/search is not treated as evidence, canonical data, or claim support by
construction. This reduces repeated approval/report overhead for harmless lead
collection while keeping promotion into canonical/research-facing artifacts
strict.

**Non-goal**: Does not fetch sources, admit evidence, validate data, approve
routes, promote candidates, support claims, update papers, or waive source
terms, privacy, IRB, or release review.

**Drift risk**: Keyword-based broad-capture detection is advisory and can
misclassify unusual tasks. The firewall must remain narrow so lead queues do
not become an unreviewed back door into processed/canonical or claim-facing
surfaces.

**Next check**: Run broad-capture firewall, execution/task/output/source
permission checks, sync doctor, smoke, and full harness. If committed, backfill
this pending entry and append a new hash-chain record.

### 2026-07-03 — Freeze runtime expansion and add compiled mode/lead metrics

**Commit(s)**: `d2aa48e`

**Action**: Added `docs/design/runtime_phase1_freeze.md` as the phase-1 freeze
memo, added a read-only compiled mode projection over existing task/execution
presets, exposed it through `aeros mode compiled`, and extended broad-capture
lead queues with required schema fields, TTL/stale detection, and promotion
metrics.

**Alignment**: Moves AEROS from horizontal policy expansion toward consolidation.
Existing user-facing presets now have a five-field projection
(`artifact_level`, `effect_class`, `authority_surface`, `execution_budget`,
`verification_strength`) without changing runtime behavior. Broad-capture lead
queues now have hygiene metrics so wide search does not become fake progress or
a lead swamp.

**Non-goal**: Does not change gate authority, approve routes, admit evidence,
promote leads, certify claims, certify papers, add a new lane, add a new gate,
or make the compiled map authoritative over ActionSpec/ExecutionEnvelope.

**Drift risk**: The compiled map is a projection and can become misleading if
presets change without updating the compiler. Lead metrics are lightweight and
should not be mistaken for evidence quality or source relevance.

**Next check**: Run compiled-mode, broad-capture, smoke, and full harness checks.
If committed, backfill this pending entry and append a final hash-chain record.

### 2026-07-03 — Add control-tax dashboard projection

**Commit(s)**: `2672e72`

**Action**: Added a derived control-tax dashboard that separates control actions,
substantive actions, route actions, human decisions, and accepted artifacts;
embedded the summary into `aeros cockpit`; added a dedicated check; and exposed
the capability through sync doctor so downstream projects can detect whether the
view is available.

**Alignment**: Supports the runtime phase-1 freeze direction by measuring
control burden rather than adding another authority surface. The dashboard is a
projection over existing receipts, decisions, deltas, and admissions; it does
not execute work or certify research quality.

**Non-goal**: Does not approve gates, judge scientific validity, certify claims,
make papers release-ready, or prove that lower control tax is always better.

**Drift risk**: Bucket assignment is intentionally coarse and depends on existing
receipt semantics. Use it to spot over-governance and fake-progress risk, not as
a research-quality score.

**Next check**: Run control-tax, cockpit, sync doctor, smoke, and full harness.
If committed, backfill this pending entry and append a final hash-chain record.

### 2026-07-03 — Add observed writes audit

**Commit(s)**: `11ba058`

**Action**: Added `aeros writes audit --since HEAD` as a dry-run observed-write
audit that compares git-observed writes with declared write roots and protected
path policy, with optional `--strict`, `--json`, `--write`, and repeated
`--declared-write` roots. Added a fixture check and exposed the capability
through smoke/full harness, project manifest, and sync doctor.

**Alignment**: Completes the Day 8 runtime-freeze item by turning protected hook
and envelope write-boundary mechanics into an operator-facing audit. The audit
observes what changed; it does not execute, revert, approve, or certify research
substance.

**Non-goal**: Does not prove scientific validity, claim support, gate approval,
paper readiness, or absence of off-repo side effects. Does not replace
ExecutionEnvelope, AgentEnvelope, or protected-path pre-commit enforcement.

**Drift risk**: Session-derived declared writes are broad allowed prefixes, not
precise semantic permissions. Use `--declared-write` for narrower task-specific
audits when needed.

**Next check**: Run write-audit, sync doctor, smoke, and full harness. If
committed, backfill this pending entry and append a final hash-chain record.
### 2026-07-03 — Close framework freeze tail items

**Commit(s)**: `d09012a`

**Scope:** template framework only.

**Changed**
- Tightened update-ledger hash-chain discipline: named the single writer, documented append-only correction policy, and added recent-commit rewrite detection with the one reviewed historical exception (`5736fad`).
- Expanded compiled mode map from a two-surface projection into a cross-checked view over task mode, execution mode, output intent, source-capture permission, and check profiles.
- Added an AEA check profile and policy wiring for AEA-style replication alignment without certifying submission readiness.
- Normalized skill tiers to `core` / `optional` / `reference` while keeping skill use advisory and waiver-based.
- Added explicit route hypotheses, falsification probes, and promotion conditions to the discovery route-decision scaffold and preflight packet.

**Validation**
- `python3 checks/check_update_ledger_hash_chain.py`
- `python3 checks/check_execution_mode.py`
- `python3 checks/check_aea_replication_alignment.py`
- `python3 checks/check_skill_layer.py`
- `python3 checks/check_skill_coverage.py`
- `python3 checks/check_discovery_route_decision.py`
- `python3 checks/check_task_preflight.py`
- `python3 checks/check_harness_profiles.py`
- `python3 checks/check_sync_doctor.py`

**Does not prove**
- scientific validity
- CMPD rollout success
- AEA acceptance
- route correctness
- skill output correctness
### 2026-07-03 — Harden CMPD rollout sync path

**Commit(s)**: `0965d6c`

**Scope:** template framework only.

**Changed**
- Treated `discovery/route_decision.yml` and `decisions/update_ledger_chain.jsonl` as project-owned rollout artifacts instead of byte-identical template files in sync doctor.
- Updated `tools/sync_aeros_latest.zsh` to merge route-decision scaffold additions while preserving project decisions.
- Updated sync to initialize or re-anchor project-local update-ledger hash chains instead of copying the template chain.
- Fixed `check_improve_harvest.py` fixture so downstream projects do not have to masquerade as the template root.
- Added `framework_rollout` workflow preset and expanded writing guardrail to cover CMPD poster/TeX paths.

**Validation**
- Template: `python3 checks/check_improve_harvest.py`
- Template: `python3 checks/check_sync_doctor.py`
- Template: `python3 checks/check_session_scope.py`
- Template: `python3 checks/run_harness_checks.py --profile smoke --timeout 20`
- CMPD rollout: sync doctor PASS after sync
- CMPD rollout: smoke harness PASS after framework sync and writing session reset

**Does not prove**
- CMPD bibliography gate completion
- AEA acceptance
- scientific validity
- claim support
- paper readiness

### 2026-07-03 — Add bibliography verifier DOI fallback

**Commit(s)**: `5525b94`

**Scope:** template framework only.

**Action**: Hardened `checks/verify_bib_online.py` so bibliography verification does not collapse into all-REVIEW when OpenAlex or the local Python TLS certificate store fails. The verifier now tries OpenAlex first, then DOI/Crossref metadata, then Crossref title search, and labels unrecoverable failures as `network_error` rather than implying the citation itself is suspect.

**Alignment**: Reduces false bibliography-review noise while preserving the human-signed verification gate. DOI/Crossref fallback helps active projects distinguish network/tooling failures from citation-integrity problems.

**Non-goal**: Does not certify paper substance, claim support, full-text availability, publisher-page accessibility, or that Crossref/OpenAlex metadata are complete. It remains an advisory artifact generator; signed `audits/bib_verification_report.md` remains the hard gate.

**Drift risk**: Crossref and OpenAlex metadata can disagree on dates, titles, or working-paper/published-version records. REVIEW rows still require human resolution. Automatic TLS fallback is limited to advisory metadata retrieval and must not be treated as source-content verification.

**Next check**: Run verifier py_compile, protected hook check, smoke/full harness, then backfill this pending entry and append a final hash-chain record.
### 2026-07-04 — Add context compiler communication budget

**Commit(s)**: `1641f44`

**Scope:** template framework only.

**North star:** AEROS should reduce the cost of truthful research progress by keeping agent context short, source-anchored, and aligned with the current objective.

**Action**: Added a Context Compiler / communication-budget layer that separates Goal, State, Evidence, Decision, Noise, Next Action, Attention Contract, and Communication Budget. The new dense-communication policy compresses status updates, summaries, context briefs, and review comments while preserving code, commands, errors, paths/URLs/DOIs, claim/evidence/result IDs, hashes, direct quotes, source evidence, methodological caveats, human gate decisions, and compliance boundaries.

**Alignment**: Borrows the useful lesson from output-compression tools such as Caveman--shorter agent communication can reduce reading cost--without compressing source-of-truth evidence or research artifacts. This keeps AEROS aligned with the principle that context is active attention allocation, not storage, evidence, or authority.

**Non-goal**: Does not install an external communication-style plugin, rewrite source-of-truth policy files into compressed style, certify claim support, prove paper readiness, approve gates, or reduce provider billing.

**Drift risk**: Dense output can hide uncertainty if applied to caveats, evidence, or human decisions. The policy therefore keeps compression output-only and requires exact preservation of identifiers, commands, hashes, quotes, and source-evidence boundaries.

**Validation**
- `python3 checks/check_context_governance.py`
- `python3 checks/check_context_bundle.py`
- `python3 checks/check_sync_doctor.py`
- `python3 checks/check_harness_profiles.py`
- `python3 -m aeros.cli context audit --lane project`
- `python3 -m aeros.cli context compile --lane project`
- `python3 checks/run_harness_checks.py --timeout 30`

**Does not prove**
- scientific validity
- source evidence correctness
- claim support
- paper readiness
- gate approval
- external token/cost savings

**Next check**: If committed, backfill this pending entry and append a final hash-chain record.
### 2026-07-04 — Revert context compiler communication budget during runtime freeze

**Commit(s)**: `afadb19`

**Scope:** template framework only.

**North star:** During the runtime freeze, new framework surfaces must be admitted only when they unblock rollout, reduce measured control tax, harden an existing authority boundary, or satisfy an already-declared benchmark need.

**Action**: Reverted the freeze-breaking Context Compiler / communication-budget feature introduced in `1641f44` and recorded the idea as `AEROS-IMPROVE-034` for later reconsideration. The correction removes the new runtime module, context-governance check, context-governance policy file, context brief templates, profile wiring, manifest wiring, sync-doctor capability, and AGENTS dense-communication rule while preserving append-only update-ledger history.

**Alignment**: Restores the architecture/runtime freeze discipline: useful ideas are backlogged unless rollout data or control-tax evidence shows they are needed now. This keeps attention on CMPD rollout and measured friction instead of adding another advisory surface.

**Non-goal**: Does not claim that dense communication is a bad idea, does not rewrite pushed git history, does not remove historical ledger-chain records, and does not change AEROS evidence, claim, gate, or execution semantics.

**Drift risk**: Reverting the feature preserves freeze discipline but may lose a short-term readability improvement. Reconsider only after control_tax or real-project rollout data identifies communication verbosity as a measurable bottleneck.

**Validation**
- `python3 checks/check_update_ledger.py`
- `python3 checks/check_update_ledger_hash_chain.py`
- `python3 checks/check_improvement_backlog.py`
- `python3 checks/run_harness_checks.py --profile smoke --timeout 20`

**Does not prove**
- scientific validity
- CMPD rollout success
- external token/cost savings
- communication verbosity is or is not a bottleneck
- dense communication should never be implemented

**Next check**: If committed, backfill this pending entry and append a final hash-chain record.

### 2026-07-04 — Add submission research driver citation grounding

**Commit(s)**: `7e379c8`

**Scope:** template framework only.

**North star:** AEROS should actively surface the highest paper-submission research risk before stale bookkeeping when a manuscript exists.

**Action**: Added a submission research driver that checks manuscript citation faithfulness and wrapper/source-project literature evidence visibility. The new driver exposes `aeros driver submission`, adds `check_manuscript_citation_faithfulness.py` and `check_literature_wrapper_sync.py`, wires them into literature/writing/compliance profiles, and lets `aeros next` prioritize unsupported cited sentences or wrapper literature mismatches before mechanical stale revalidation.

**Alignment**: This turns the cultured-meat/MAHA lesson into a deterministic driver rule: final manuscript truth and literature visibility are project-management risks, not just registry-shape checks. The driver remains advisory and traceability-focused; it does not decide whether a paper is good or whether a citation interpretation is scientifically correct.

**Non-goal**: Does not certify literature completeness, extraction-card quality, scientific truth, paper readiness, journal acceptance, claim support, gate approval, or public release.

**Drift risk**: Citation parsing is intentionally conservative and may miss nonstandard prose citations or flag weak cards that are substantively adequate. Wrapper sync uses configured source-project paths only and must not blindly import source artifacts without review.

**Validation**
- `python3 checks/check_manuscript_citation_faithfulness.py`
- `python3 checks/check_literature_wrapper_sync.py`
- `python3 -m aeros.cli driver submission`
- `python3 checks/check_literature_tools.py`
- `python3 checks/check_sync_doctor.py`
- `python3 checks/run_harness_checks.py --profile smoke --timeout 20`

**Does not prove**
- literature completeness
- citation interpretation correctness
- claim support
- paper readiness
- gate approval

**Next check**: Backfill this pending entry after commit and append the corresponding update-ledger hash-chain record.

## 2026-07-04 — Add manuscript citation interpretation records

- **Commit(s)**: `7e379c8`
- **Change type**: framework / submission driver / literature grounding
- **Action**: Added a sentence-level literature interpretation record layer for manuscript citations. Each cited manuscript sentence must now map to a registry paper, full-text extraction support, and a human-approved interpretation record with source passage, support relation, scope match, claim-strength match, limitations/contradictory-evidence checks, and review verdict.
- **Why**: Existing tools and recent citation-verification work show that bibliography existence and extraction-card presence are not enough; hallucination prevention requires claim-source alignment at the sentence/passage level.
- **Validation**: pending targeted checks: `check_manuscript_citation_interpretation.py`, `check_manuscript_citation_faithfulness.py`, `check_literature_tools.py`, `check_sync_doctor.py`, ledger checks, and smoke harness.
- **Does not prove**: cited sources are true; human interpretation is correct beyond the recorded evidence basis; every uncited sentence is grounded; final paper is submission-ready.

## 2026-07-04 — Make aeros init plug-and-play and sync MAHA

- **Commit(s)**: `d9b7417`
- **Change type**: framework / init / sync / rollout
- **Action**: Changed `aeros init` so a new project is immediately vendored with the current AEROS runtime/checks through the canonical sync script; removed hardcoded template-root assumptions from sync by deriving the template root from the script path and exporting `AEROS_TEMPLATE_ROOT`; repaired the global `aeros` console script by installing the template package in editable mode; vendored the current framework into `/Users/jiamingzhang/Desktop/MAHA` while preserving its project-local `AGENTS.md`.
- **Validation**: Global `aeros --help` works; scratch `aeros init` project contains `aeros/` and `checks/` and passes smoke harness; MAHA project root passes smoke harness.
- **Does not prove**: MAHA research claims are supported; MAHA literature citations are grounded; downstream projects are committed; protected git hooks are installed in every repo; full project-specific harnesses beyond smoke are green.
## 2026-07-04 — Compile modes, tier citation grounding, and mature broad-capture metrics

- **Commit(s)**: `cf2070c`
- **Change type**: framework / runtime compression / literature grounding / broad capture
- **Action**: Added a read-only `aeros inspect modes --compiled` alias and expanded the compiled mode map with `promotion_status`, making mode inspection project-manager-readable without changing runtime authority. Changed broad-capture progress semantics from `ROUTE_READY` to `CAPTURE_LOGGED`, added duplicate/staleness/saturation metrics to lead queues, and tightened broad-capture checks around the low-audit capture firewall. Tiered manuscript citation grounding into `tier_0_bibliographic`, `tier_1_interpretive`, and `tier_2_claim_bearing`; bibliographic citations are non-blocking when registry-mapped, interpretive citations surface non-blocking weaknesses, and claim-bearing citations remain blocking until extraction support and an approved interpretation record exist.
- **Why**: This implements the freeze-period compression principle: do not add a new governance surface when an existing five-field/control model can carry the distinction. Capture should be cheap and non-promotable; promotion and claim-bearing manuscript text should be expensive and grounded.
- **Validation**: `python3 -m py_compile aeros/runtime/mode_compiler.py aeros/runtime/broad_capture.py aeros/runtime/submission_driver.py aeros/cli.py checks/check_manuscript_citation_interpretation.py checks/check_execution_mode.py checks/check_broad_capture_firewall.py checks/check_progress_semantics.py`; `python3 -m aeros.cli inspect modes --compiled --json`; `python3 checks/check_execution_mode.py`; `python3 checks/check_broad_capture_firewall.py`; `python3 checks/check_progress_semantics.py`; `python3 checks/check_manuscript_citation_interpretation.py`; `python3 checks/check_manuscript_citation_faithfulness.py`; `python3 checks/check_literature_tools.py`; `python3 checks/run_harness_checks.py --profile smoke --timeout 20`.
- **Does not prove**: citation interpretations are scientifically correct; tier inference replaces human manuscript judgment; broad-capture leads are evidence; leads should be promoted; compiled modes are scientifically optimal; runtime behavior changed beyond the documented low-authority alias and policy semantics.
- **Next check**: Run full harness before commit; if committed, backfill this pending entry and append a follow-up hash-chain record if the commit hash changes the ledger subject.
## 2026-07-05 — Add AEROS Drive MVP usefulness entrypoint

- **Commit(s)**: `6aaa2c8`
- **Change type**: framework / product entrypoint / usefulness layer
- **Action**: Added `aeros drive` as a thin daily-use aggregator over existing deterministic AEROS signals: next action, task preflight, broad-capture summary, and submission citation/literature driver. The MVP chooses one objective, reports why it outranks alternatives, states expected artifacts and protected surfaces, and optionally executes only allowlisted read-only or dry-run commands. Added `check_drive.py`, smoke-profile coverage, and sync-doctor capability mapping.
- **Why**: Recent real use showed AEROS was strong at guard/prove but weak at propulsion. `drive` is intended to reduce the need for the user to ask “next step?” by turning scattered advisory commands into one project-manager packet while preserving authority boundaries.
- **Validation**: `python3 -m py_compile aeros/runtime/drive.py aeros/cli.py checks/check_drive.py aeros/runtime/sync_doctor.py`; `python3 -m aeros.cli drive --json`; `python3 -m aeros.cli drive --goal citation-risk --execute --json`; `python3 checks/check_drive.py`; `python3 checks/check_sync_doctor.py`; `python3 checks/run_harness_checks.py --profile smoke --timeout 20`.
- **Does not prove**: AEROS is now useful in real projects; external source capture ran; skill ROI improved; user intervention decreased; claim, paper, gate, or release authority is granted.
- **Next check**: Run `aeros drive` inside CMPD/MAHA/SNAP during the next real work session and compare whether it reduces human pushes per substantive artifact.

## 2026-07-05 — Make `aeros drive --goal citation-risk` actually read the manuscript

- **Commit(s)**: `7c16021`
- **Change type**: framework / drive execution engine / submission grounding
- **Action**: Added `aeros/runtime/citation_radar.py`, a read-only engine that parses a manuscript's narrative author-year citations (`Author (2025)`, `(A and B 2011; C et al. 2016)`, including line-wrapped groups), matches them to `discovery/literature/paper_registry.csv` by year + author-token overlap (handling institutional authors such as USDA/Institute), and ranks cited sources by grounding risk (unknown-source > ungrounded > grounded, claim-bearing escalated). Wired the `drive --goal citation-risk` objective to this engine and to a new read-only `checks/check_citation_risk_radar.py` (fixture-guarded, always advisory/exit 0), registered in the citation profiles. Fixed `MANUSCRIPT_GLOBS` in `submission_driver.py` to include `docs/manuscript/*.md|*.tex` — the prior globs only matched a `docs/manuscript.md` file and were silently blind to manuscripts stored inside a `docs/manuscript/` directory.
- **Why**: `drive --goal citation-risk` previously only recommended `check_manuscript_citation_interpretation.py`, which via the buggy glob could not see manuscripts under `docs/manuscript/` and only parsed pandoc `@key` citations. On a real narrative-cited manuscript it reported "0 citations, clean" — governance machinery that never touched the paper. The radar closes that gap: on a live manuscript it surfaces claim-bearing citations pinned to sources absent from the evidence base (e.g. a specific cost magnitude cited to an untracked survey).
- **Validation**: `python3 -m py_compile aeros/runtime/citation_radar.py aeros/runtime/drive.py aeros/runtime/submission_driver.py checks/check_citation_risk_radar.py`; `python3 checks/check_citation_risk_radar.py`; `python3 -m aeros.cli drive --goal citation-risk`; `python3 checks/check_harness_profiles.py`; `python3 checks/run_harness_checks.py --profile smoke --timeout 40`.
- **Does not prove**: cited sources are true or false; an "unknown-source" flag is a real error rather than a registry-coverage gap; author-year matching is exhaustive; claim-bearing keyword detection is complete; the paper is submission-ready; scientific validity; claim, gate, or release authority is granted.
- **Next check**: Sync into a real project (MAHA) and confirm the ranked risk list is trustworthy on the live manuscript; backfill this pending entry with the commit hash and a chain record.

## 2026-07-05 — Add campaign contract circuit breaker

- **Commit(s)**: `43e05f2`
- **Change type**: framework / controller / campaign breaker
- **Action**: Added `aeros campaign assess`, `aeros/runtime/campaign.py`, campaign contract/progress templates, and `check_campaign_contract.py`. The new advisory circuit breaker reads a campaign contract plus marginal-yield progress ledger and escalates when repeated same-lane work shows low marginal yield, task-budget exhaustion, binding-constraint drift, unused batch sources, or collecting without rerunning the decision metric.
- **Why**: Real autonomous loops repeatedly got stuck in local climbing: many tasks produced little yield, chased a non-binding constraint, or kept collecting without testing the decision metric. AEROS needed a deterministic way to ask whether continuing the campaign is still worth it, not only whether the latest artifact is well-formed.
- **Validation**: pending targeted checks: `python3 checks/check_campaign_contract.py`, `python3 checks/check_drive.py`, `python3 checks/check_sync_doctor.py`, `python3 checks/run_harness_checks.py --profile smoke --timeout 20`.
- **Does not prove**: scientific validity; campaign objective optimality; that a stopped campaign is useless; claim support; gate approval; paper readiness.
- **Next check**: Use in a real CMPD/MAHA/SNAP repeated data/literature campaign and verify it stops a low-yield loop before another batch of same-kind tasks.

## 2026-07-05 — Enforce structured owner decisions in task preflight

- **Commit(s)**: `ad46e3f`
- **Change type**: framework / owner decision enforcement / preflight bridge
- **Action**: Added deterministic owner-decision rule parsing from `decisions/decision_log.csv` structured `Follow-up` metadata. `do_not` patterns, binding constraints, stop conditions, campaign budgets, and supersession metadata are now machine-readable. `task preflight` reports `BLOCKED` when active owner `do_not` rules match the requested lane/task/intent, while surfacing non-blocking constraints for campaign/controller use.
- **Why**: Prior owner decisions were recorded and fingerprinted but not executed. This bridges the gap between human direction and autonomous loop behavior: recorded decisions can now prevent repeated direction drift before work starts.
- **Validation**: pending targeted checks: `python3 checks/check_owner_decisions.py`, `python3 checks/check_task_preflight.py`, `python3 checks/check_sync_doctor.py`, `python3 checks/run_harness_checks.py --profile smoke --timeout 20`.
- **Does not prove**: free-form rationale is understood; the owner decision is scientifically correct; blocked work is never useful; claim support; gate approval; paper readiness.
- **Next check**: Add a real project owner decision such as `do_not: [parcel-price]` in `Follow-up` JSON and confirm preflight blocks a matching task before another autonomous loop begins.

## 2026-07-06 — Upgrade manuscript citation faithfulness to sentence-level grounding

- **Commit(s)**: `5c7835e`
- **Change type**: framework / literature grounding / anti-hallucination
- **Action**: Added `aeros/runtime/citation_sentence_grounding.py` and upgraded `check_manuscript_citation_faithfulness.py` from shallow citation-asset presence toward sentence-level grounding. The checker now parses `.tex`/`.md` manuscript sentences, extracts citation keys, maps them to `paper_registry.csv`, links extraction cards, and blocks claim-bearing cited sentences unless they have source-bound extraction support plus an approved faithful interpretation record. Existing manuscript discovery was also extended to `tex/paper.tex` and `tex/*.tex`.
- **Why**: Recent project use showed a dangerous false sense of safety: a clean citation check could mean only that no encoded structural error fired, not that paper sentences were actually supported by cited sources. The upgraded check makes unsupported/overclaimed citation-bearing manuscript sentences visible before paper-readiness claims.
- **Validation**: pending targeted checks: `python3 checks/check_manuscript_citation_faithfulness.py`, `python3 checks/check_manuscript_citation_interpretation.py`, `python3 checks/check_citation_risk_radar.py`, `python3 checks/check_sync_doctor.py`, and smoke harness.
- **Does not prove**: cited sources are true; human interpretation is correct beyond recorded source passages; every uncited claim is grounded; author-year matching is exhaustive; paper readiness; claim support; gate approval.
- **Next check**: Run inside MAHA/CMPD on a real manuscript and confirm claim-bearing citation sentences produce actionable rows rather than an empty `{}`.
## 2026-07-06 — Add sci-download PDF retrieval skill bridge

- **Commit(s)**: `dcb1884`
- **Change type**: framework / literature skills / full-text retrieval
- **Action**: Added a local Codex `sci-download` skill wrapper and registered `Aut_Sci_Download` as an optional AEROS literature adapter candidate. Literature skill obligations now consider `sci-download` for DOI/PDF/full-text recovery, while the practical skill menu and external tool registry make the boundary explicit: retrieval can populate full-text queues and audits, but cannot create extraction cards, citation interpretations, claims, or gate approvals.
- **Why**: Recent manuscript-grounding work made full-text availability a bottleneck. AEROS needs a legal/open/user-authorized PDF retrieval skill path, but it must preserve the capture/promotion boundary so "found PDF" does not become "supported citation".
- **Validation**: pending targeted checks: `python3 checks/check_skill_layer.py`, `python3 checks/check_skill_coverage.py`, `python3 checks/check_sync_doctor.py`, and smoke harness.
- **Does not prove**: legal access for any specific source; successful PDF download; PDF readability; identity match to the target paper; extraction-card correctness; citation faithfulness; claim support; gate approval.
- **Next check**: Use on a real blocked full-text item and confirm it updates `fulltext_ready_queue.csv` or `missing_fulltext_queue.csv` without writing extraction cards or claims.
## 2026-07-06 — Add citation function requirements to manuscript grounding

- **Commit(s)**: `34e6711`
- **Change type**: framework / literature grounding / citation-function compiler
- **Action**: Added `harness/citation_function_requirements.yml` and upgraded sentence-level manuscript citation grounding so each cited sentence receives a `citation_function`, required/available evidence, source type, risk level, and citation-debt status. `check_manuscript_citation_faithfulness.py` now fixtures metadata/background citations, abstract-only result/number claims, and approved interpretation records. `aeros drive --goal citation-risk` now prioritizes sentence-level citation debt instead of only author-year registry risk.
- **Why**: Reference existence and full-text availability are insufficient. AEROS needs function-specific evidence requirements so bibliography can stay broad while claim-bearing manuscript citations must be source-passage grounded.
- **Validation**: pending targeted checks: `python3 checks/check_manuscript_citation_faithfulness.py`, `python3 checks/check_citation_risk_radar.py`, `python3 checks/check_sync_doctor.py`, and smoke harness.
- **Does not prove**: citation-function inference is perfect; cited sources are true; human interpretation records are correct beyond their source passages; every uncited sentence is grounded; paper readiness; claim support; gate approval.
- **Next check**: Run on a real manuscript and verify citation debt rows point to useful actions: recover full text, add extraction card, add interpretation record, weaken sentence, or replace citation.
## 2026-07-08 — Add risk-ranked research driver projection

- **Commit(s)**: `852146f`
- **Change type**: framework / research driver / risk-ranked next action
- **Action**: Added a deterministic `research_risk` compiler and wired it into `aeros drive` and `aeros next` so manuscript citation debt, wrapper-literature visibility, and broad-capture saturation can outrank routine stale revalidation. Extended drive/task-preflight checks to fixture citation debt priority, broad-capture defaulting, and strict promotion boundaries.
- **Why**: Recent real projects showed AEROS was good at guarding protected surfaces but weaker at proactively identifying the highest research risk. The driver should be light during capture, strict at promotion, and active at manuscript truth review.
- **Validation**: pending targeted checks: `python3 checks/check_drive.py`, `python3 checks/check_next_action.py`, `python3 checks/check_task_preflight.py`, `python3 checks/check_sync_doctor.py`, and smoke harness.
- **Does not prove**: the ranked risk is scientifically optimal; citation-function inference is perfect; full project rollout improves usefulness; claim support; paper readiness; gate approval.
- **Next check**: Run inside CMPD/MAHA/SNAP and verify the top recommendation matches the real PI/editor risk rather than a mechanical stale task.

## 2026-07-09 — Fix research-driver rollout semantics

- **Commit(s)**: `e2b898e`
- **Change type**: framework / research-driver rollout repair / citation grounding
- **Action**: Fixed the rollout issues surfaced by real MAHA and cultured-meat tests: read-only research-risk `ActionSpec` records no longer declare expected outputs; `aeros drive --execute` can report `blocked_found` when a truth check successfully surfaces a blocker; email addresses such as `name@msu.edu` are no longer parsed as manuscript citation keys; citation grounding now respects registry citation functions/source types so method/background/official-source routes are not over-promoted into core claim blockers; downstream `check_next_action.py` keeps expensive controller-loop fixtures scoped to the template.
- **Why**: The rollout test showed the new driver was conceptually right but had operational friction: useful blocker discovery looked like command failure, read-only specs violated their own invariant, email addresses caused false citation debt, and downstream smoke profiles paid template-level controller-test costs.
- **Validation**: `python3 checks/check_next_action.py` and `python3 checks/check_drive.py` in template; `python3 checks/check_manuscript_citation_faithfulness.py`, `python3 checks/check_manuscript_citation_interpretation.py`, `python3 -m aeros.cli drive --goal citation-risk --execute --json`, `python3 -m aeros.cli next --json`, and targeted `check_next_action.py`/`check_drive.py` in cultured meat; `python3 -m aeros.cli next --json` and `python3 checks/check_manuscript_citation_faithfulness.py` in MAHA.
- **Does not prove**: citation-function inference is perfect; weak/background citations are substantively correct; paper readiness; claim support; gate approval; real-project usefulness beyond the tested projects.
- **Next check**: After sync into active projects, monitor whether `aeros drive` reports `blocked_found` only for genuine action-worthy blockers and whether downstream smoke latency remains acceptable without hiding template-level controller invariants.

## 2026-07-09 — Enforce skill use-or-waive proof and current-work routing context

- **Commit(s)**: `103ffe6`
- **Change type**: framework / skill obligation enforcement / research-driver context
- **Action**: Added completion-level `skill_use_attestation` so skill-eligible tasks cannot pass without either a skill invocation receipt or explicit waiver. Extended task preflight with a `skill_use_contract` that lists required skill classes, candidate skills, waiver fields, and the pass rule. Added `CURRENT_WORK.yml` plus `aeros.runtime.current_work`, and wired current-work hints into `aeros next` and `aeros drive` so active writing/poster/submission work can outrank generic data-first or broad-capture fallback when no higher-priority red light exists. Registered both capabilities in sync doctor and harness profiles.
- **Why**: Recent project use showed two remaining frictions: skills had moved from optional recommendation to default consideration, but task completion still did not require a concrete use-or-waive proof; and the research driver could still route active poster/manuscript work toward generic data/broad-capture defaults when the current project context was not visible.
- **Validation**: `python3 checks/check_skill_use_attestation.py`; `python3 checks/check_current_work_context.py`; `python3 checks/check_sync_doctor.py`; `python3 checks/check_harness_profiles.py`; `python3 checks/check_drive.py`; `python3 checks/check_next_action.py`; `python3 checks/check_task_preflight.py`; `python3 checks/check_completion_receipts.py`.
- **Does not prove**: skill advice is correct; the agent actually followed every skill instruction perfectly; current-work hints identify the scientifically optimal next step; citation-function inference is perfect; claim support; paper readiness; gate approval.
- **Next check**: Sync into MAHA/CMPD/cultured-meat during real work and verify pass receipts now fail without skill use-or-waive evidence, while `aeros drive` respects active poster/manuscript context without hiding real submission-truth blockers.

## 2026-07-09 — Fix broad-capture routing and sentence-first citation grounding

- **Commit(s)**: `32884c2`
- **Change type**: framework / rollout bug fix / capture routing / citation grounding
- **Action**: Fixed three rollout blockers surfaced by active-project diagnostics: broad Chinese search phrases such as “广泛搜索/广泛抓取/先搜集/撒网” now route to `broad_capture`; negative claim-boundary phrases such as “不进入 claim / 不触碰 claim” no longer trigger `claim_audit`; `green_broad_capture` now correctly sets `allowed_without_human_approval: true`; and sentence-level citation function classification now treats registry `citation_function` as a default hint rather than overriding sentence-specific method/result/mechanism/number use. Added fixtures for Chinese broad-capture routing, approval-free broad lead capture, and registry-related-literature labels being overridden by claim/number-bearing sentences.
- **Why**: Real rollout diagnostics showed AEROS was still too heavy during early capture and too shallow during citation review: broad lead search could be misrouted into claim audit/route approval, and cultured-meat citation checks could pass because a registry-level `related_literature` label masked claim-bearing sentence use.
- **Validation**: `python3 checks/check_task_mode.py`; `python3 checks/check_source_capture_permission.py`; `python3 checks/check_manuscript_citation_faithfulness.py`; `python3 checks/check_citation_risk_radar.py`; `python3 checks/check_drive.py`; `python3 checks/check_task_preflight.py`; `python3 checks/check_sync_doctor.py`.
- **Does not prove**: citation-function inference is perfect; every cited sentence is substantively faithful; broad capture should ignore ToS/login/private-data risks; active-project rollout success; claim support; paper readiness; gate approval.
- **Next check**: Sync into active projects and verify broad lead-search prompts route green without human approval while claim/number/method-bearing manuscript sentences are not hidden by registry-level related-literature labels.


## 2026-07-09 — Repair sentence citation grounding route admissions

- **Commit(s)**: `8ef3704`
- **Change type**: framework / citation grounding / rollout bug fix
- **North star:** Reduce false citation debt while preserving sentence-level anti-hallucination boundaries.
- **Alignment:** Keeps manuscript citation truth as a P0 submission risk, but distinguishes true unsupported claims from bounded method/theory/data references and source-snapshot-backed facts already admitted by a final citation packet.
- **Action**: Hardened sentence citation-function inference by stripping citation commands before classification, using word-boundary matching for short method markers such as `iv`/`did`, prioritizing method markers over broad mechanism words, and incorporating registry `primary_function` for data-measurement and method-identification citations. Added `route_admission_ok` for source snapshots, bounded method/theory/data route notes, and full-text extraction routes admitted by a final citation packet. Extended fixtures so citation-key years, EPV/table-like method sentences, Shor--McCarty score citations, Manski reflection-hypothesis citations, and bounded method waivers are tested.
- **Why**: Cultured-meat rollout surfaced 53 blocking citation-debt rows, but many were false or already bounded by the 2026-07-06 final citation packet. The repair reduced the live manuscript from 53 blocking rows to 0 without granting claim support, paper readiness, or scientific truth.
- **Validation**: `python3 checks/check_manuscript_citation_faithfulness.py`; `python3 checks/check_citation_risk_radar.py`; `python3 checks/check_sync_doctor.py`; `python3 checks/run_harness_checks.py --profile smoke --timeout 20`; plus the same smoke checks in cultured meat after vendored sync.
- **Non-goal**: Do not certify cited sources as true; do not approve interpretation records; do not upgrade claims; do not declare the paper submission-ready; do not make every method citation require a full extraction card.
- **Does not prove**: citation-function inference is perfect; final citation packet judgments are scientifically correct; weak/background citations are sufficient for all future drafts; claim support; paper readiness; gate approval.
- **Drift risk**: Route admissions can become too permissive if projects add broad `support_route_note` text without a real final citation packet or bounded-use language. Future checks should keep admissions narrow and report the admitted route in citation-debt summaries.
- **Next check**: Roll this into the next project with a real manuscript citation debt surface and verify that unsupported result/number claims still block while bounded method/theory/data citations do not create noisy P0 debt.

## 2026-07-09 — Compile current-work priority into the drive objective

- **Commit(s)**: `986cf2f`
- **Change type**: framework / research driver / current-work routing repair
- **North star:** Reduce manual pushes by turning an operator-declared active priority into the next concrete, bounded recommendation.
- **Alignment:** Keeps hard process failures and nonzero research risks ahead of current-work hints, but prevents a generic lane fallback from replacing the first active project priority when no higher risk exists.
- **Action**: Added a deterministic `current_work_priority` drive objective. When `CURRENT_WORK.yml` is active, `priority_order` is nonempty, no explicit lane overrides it, and the research-risk compiler reports no nonzero top risk, `aeros drive` now selects `priority_order[0]` and renders a preflight-only command for that exact priority. Extended the current-work fixture to require the objective text, source path, and preflight boundary.
- **Why**: MAHA rollout showed that active writing context prevented a wrong broad-capture fallback but still degraded into generic claim readiness instead of the declared current-status validation task. The driver was using the lane hint but not the ordered work objective.
- **Validation**: pending targeted checks: `python3 checks/check_current_work_context.py`, `python3 checks/check_drive.py`, and smoke harness; then sync to MAHA and confirm the chosen objective is current-status validation.
- **Non-goal**: Do not infer priorities with an LLM; do not execute the research task; do not let current-work hints override hard failures, human gates, or nonzero research risks.
- **Does not prove**: the declared priority is scientifically optimal; the preflighted work has run; current-status sources are correct; claim support; paper readiness; gate approval.
- **Drift risk**: A stale `CURRENT_WORK.yml` can produce a stale recommendation. Projects must keep the file short, dated through version control, and update or remove it when the active deliverable changes.
- **Next check**: Use on MAHA and one non-writing project to verify that active priority routing reduces generic fallback without masking a real research-risk blocker.
## 2026-07-10 — Wire campaign breaker into task preflight; repair drifted registries

- **Commit(s)**: `7089827`
- **Change type**: framework / execution-gate enforcement / registry repair
- **Action**: (1) Wired the marginal-yield circuit breaker into the execution gate: `task_preflight.build_task_preflight` now calls `assess_campaign(root)` and forces `status=BLOCKED` (with `needs_human_decision` and a human-decision stop reason) whenever any campaign breaker trips — closing the gap where `campaign assess` could detect "should stop" but preflight still allowed the next local task. Backward-compatible: with no active campaign contract the breaker is inactive and preflight behaviour is unchanged. Added a `check_task_preflight.py` fixture that locks in "tripped breaker → BLOCKED". (2) Repaired two drifted registries that had been failing `full` harness: restored 6 external econ tools (`aea_data_editor`, `opensourceeconomics`, `econstellar`, `econometrics_agent`, `causal_copilot`, `causalagent`) into the `tools:` mapping of `external_tool_registry.yml`, and populated `skill_map_core.yml` with the 23 skills the example task contracts invoke but which were never registered (map 3 → 26, within the 32 cap).
- **Why**: The execution-gate wire is the propulsion-side enforcement the direction-governor needed. The registry repairs were surfaced because full harness had silently been red for several commits — the parallel loop commits on the `smoke` profile and never runs `full`, so map/registry drift accumulated. Root cause of both drifts: tool/skill blocks appended at column 0 escaped their YAML mapping, or were referenced by tasks/checks without ever being registered.
- **Validation**: `python3 checks/check_task_preflight.py`; `python3 checks/check_external_tool_registry.py`; `python3 checks/check_skill_invocations.py`; `python3 checks/check_skill_layer.py`; `python3 checks/run_harness_checks.py --profile full --timeout 90` (all pass).
- **Does not prove**: that any campaign breaker threshold is scientifically correct; that the 23 registered skills are useful or should be default; that the escaped-block YAML pattern will not recur; that scientific validity, claim support, or gate approval is granted.
- **Next check**: Consider enforcing `full` harness (or a drift check) at the loop's commit gate so registry drift cannot re-accumulate silently. Backfill this pending entry with the commit hash.
## 2026-07-10 — Add registry/skill drift guards to smoke profile

- **Commit(s)**: `f1f1d14`
- **Change type**: framework / harness profile / drift prevention
- **Action**: Added `check_external_tool_registry.py`, `check_skill_invocations.py`, and `check_skill_layer.py` to the `smoke` profile, and exempted them in `sync_doctor` CAPABILITY_EXEMPT_CHECKS (framework-owned registry invariants synced via `harness/`).
- **Why**: The external-tool and skill-map registries had silently drifted red for several commits because the autonomous loop commits on the `smoke` profile and never runs `full`. Putting the drift guards in `smoke` makes the loop catch registry/skill-map drift at its own commit gate instead of letting it accumulate — the framework-health analogue of wiring the campaign breaker into task preflight.
- **Validation**: `python3 checks/check_harness_profiles.py`; `python3 checks/check_sync_doctor.py`; `python3 checks/run_harness_checks.py --profile smoke --timeout 60`; `python3 checks/run_harness_checks.py --profile full --timeout 90` (all pass).
- **Does not prove**: that the loop will run smoke before every commit; that no other check is missing from smoke; scientific validity; claim/gate approval.
- **Next check**: Backfill this pending entry with the commit hash.

## 2026-07-10 — Scope campaign breakers to declared task identity and auto-record progress

- **Commit(s)**: `6337c3c`
- **Change type**: framework / campaign runtime enforcement / completion evidence
- **North star:** Stop autonomous local hill-climbing without letting one campaign's breaker block unrelated research work.
- **Alignment:** Makes campaign identity explicit in TaskContract and ActionSpec, evaluates only the matching active campaign at preflight, enforces the decision in the real runner, and records passed-task progress from the completion path rather than relying on a manually edited ledger.
- **Action**: Added `campaign_id` and campaign progress declarations to task contracts and typed ActionSpecs. `task preflight` now returns `TASK_NOT_IN_CAMPAIGN` or `CAMPAIGN_MISMATCH` without applying unrelated breakers, while matching campaigns remain fail-closed. `aeros run` now executes preflight before changing task status or invoking deterministic/provider work. Passed campaign tasks idempotently append one progress row containing computed marginal yield, an allowed-output evidence path and SHA-256, completion mode, receipt path, and timestamp; conflicting rewrites fail instead of replacing history. Completion receipts are version 7 and carry the campaign identity/progress result. Real fixtures prove same-campaign blocking, cross-campaign non-interference, runner non-bypass, and idempotent evidence-bound progress recording.
- **Validation**: `python3 checks/check_action_spec.py`; `python3 checks/check_campaign_contract.py`; `python3 checks/check_task_preflight.py`; `python3 checks/check_completion_receipts.py`; `python3 checks/check_next_action.py`; `python3 checks/check_task_contract.py`; `python3 checks/run_harness_checks.py --profile smoke --timeout 20` (56 checks pass); `python3 checks/run_harness_checks.py --timeout 30` (130 checks pass).
- **Non-goal**: Do not infer campaign membership from task prose; do not apply an active campaign globally; do not decide that the objective metric or threshold is scientifically optimal; do not execute a blocked task; do not auto-approve a gate or claim.
- **Does not prove**: declared metric values are substantively correct merely because their evidence file exists and hashes cleanly; campaign thresholds are optimal; a stopped campaign should never resume; unrelated work is scientifically worthwhile; claim support; paper readiness; gate approval.
- **Drift risk**: Legacy progress rows without `campaign_id` are temporarily treated as belonging to the active campaign for backward compatibility. Vendored projects should sync before starting a second campaign, and future migration should retire blank campaign identities after active projects have upgraded.
- **Next check**: Sync into land-grid, create a real `clean-official-numerator` campaign, and prove a low-yield matching task is blocked while a non-campaign task remains runnable.

## 2026-07-10 — Cache immutable skill policy inputs during validation

- **Commit(s)**: `c02fe65`
- **Change type**: framework / validation performance / no semantic change
- **North star:** Keep strict skill obligations usable on mature projects without paying repeated YAML parsing cost per task.
- **Action**: Added process-local bounded caches to `load_core_skill_map` and the skill-obligation policy loader. Every AEROS command still starts a fresh process and observes files anew; within one validation run, hundreds of contracts now share the same immutable parsed registry and policy.
- **Why**: Land-grid's 149 active contracts exposed a scaling defect: `check_skill_invocations.py` repeatedly parsed the 953-line skill map and terminated before producing a verdict. The same check completes in under four seconds after caching.
- **Validation**: `python3 checks/check_skill_invocations.py`; `python3 checks/check_skill_coverage.py`; land-grid smoke profile.
- **Non-goal**: Do not weaken skill obligations, skip receipts, waive legacy tasks, infer scientific quality, or persist cache state across commands.
- **Does not prove**: skill advice is correct; agents followed skills correctly; old project research is valid; claim support; gate approval.
- **Drift risk**: A single long-lived Python process that edits the policy after first access would need to clear the cache; normal AEROS CLI/check execution is one fresh process per command.
- **Next check**: Keep the skill checks in smoke and monitor runtime on another project with more than 100 task contracts.

## 2026-07-10 — Stabilize fast smoke and add real-project runtime canaries

- **Commit(s)**: `f4d8ac8`
- **Change type**: framework / performance / profile consolidation / rollout evidence
- **North star:** Reduce the cost of truthful research progress without weakening the full internal harness.
- **Action**: Added mtime/size-keyed process-local caches for task-preflight, task-mode, and source-capture policy YAML; reused the already loaded task contract within one preflight; moved isolated-worktree and agent-envelope executable fixtures out of smoke while retaining them in full; made the profile validator reject future leakage of heavy fixtures into smoke; removed obsolete sync-doctor exemptions; and recorded current-template read-only canaries on land-grid, cultured meat, and MAHA in `audits/runtime_rollout_validation_20260710.md`.
- **Why**: Smoke had become unstable at the documented 20–30 second per-check budget, and an empty template pass did not establish usefulness on real research state. Profiling showed repeated YAML parsing in preflight; live canaries also showed two bounded/aligned recommendations and one visible land-grid context gap.
- **Validation**: `check_task_preflight.py`, `check_next_action.py`, `check_drive.py`, `check_harness_profiles.py`, `check_sync_doctor.py`, smoke with `--timeout 20`, full harness, and current-template `drive --json` plus broad-capture preflight against three real projects.
- **Non-goal**: Do not remove envelope/adversarial checks from full, auto-sync downstream projects, execute canary recommendations, hide the land-grid context gap, approve gates, or upgrade claims.
- **Does not prove**: recommendation optimality; downstream version parity; research validity; claim support; paper readiness; gate approval.
- **Drift risk**: Long-lived processes that rewrite a policy file without changing mtime/size could theoretically retain a stale parse; normal CLI/check execution is process-bounded. Smoke remains a fast commit gate, not a release substitute for full.
- **Next check**: After downstream projects deliberately sync, repeat the canary using their vendored runtime and confirm land-grid has an explicit current-work priority before treating its driver recommendation as aligned.

## 2026-07-10 — Block undeclared same-campaign work after circuit-breaker escalation

- **Commit(s)**: `f6f669f`
- **Change type**: framework / campaign enforcement / anti-bypass guard
- **North star:** Make autonomous stopping rules enforceable without turning one campaign into a global lane lock.
- **Action**: Added owner-declared `objective_markers` to campaign contracts and a deterministic lane/marker scope matcher. When an active campaign has tripped breakers, an undeclared task that matches its lane and objective markers is now `BLOCKED` as `UNDECLARED_CAMPAIGN_SCOPE`; a task using a different campaign ID but the same stopped scope is `BLOCKED` as `CAMPAIGN_SCOPE_COLLISION`. Legacy active campaigns without markers fail closed for undeclared same-lane work. Different lanes and same-lane tasks with declared nonmatching objectives remain outside the campaign. The real runner enforces the same result before task execution.
- **Why**: Campaign scoping previously depended entirely on honest task metadata. An autonomous loop could omit `campaign_id` and continue the exact low-yield route that the breaker was designed to stop.
- **Validation**: Fixtures cover no active campaign, unrelated lane, same lane/different objective, undeclared same scope, mismatched ID/different objective, mismatched ID/same scope, declared matching scope, legacy missing markers, and real-runner non-bypass with absent output.
- **Non-goal**: Do not infer scientific equivalence with an LLM, auto-enroll tasks into campaigns, block unrelated work, choose campaign thresholds, approve continuation, or change claims/gates.
- **Does not prove**: objective markers are complete; differently worded same-objective work can never evade phrase matching; campaign thresholds are optimal; research validity; claim support; gate approval.
- **Drift risk**: Marker lists can be underspecified. Missing markers deliberately fail closed only for the active campaign lane after a breaker trips; owners should add concise stable phrases rather than broad words such as `data` or `source`.
- **Next check**: Sync into the next project with an active stopped campaign and verify one undeclared same-scope task blocks while one genuinely unrelated same-lane task remains advisory.
## 2026-07-10 — Add output-target and task-type dimensions to campaign scope guard

- **Commit(s)**: `76e0c78`
- **Change type**: framework / execution-gate enforcement / anti-evasion
- **Action**: Extended `match_campaign_scope` beyond objective-marker keyword matching to two phrasing-independent dimensions: `objective_outputs` (output path prefixes the campaign owns) and `objective_task_types` (task modes belonging to the campaign). `task_preflight` now passes the task's allowed output targets and inferred task mode, and the `UNDECLARED_CAMPAIGN_SCOPE` / `CAMPAIGN_SCOPE_COLLISION` guards fire on `scope_match_any` (markers OR outputs OR task type). Added a `check_task_preflight.py` fixture locking in that a reworded intent writing to the campaign output class is blocked while genuinely-unrelated output stays free, and documented the new fields in the campaign contract template.
- **Why**: The prior guard matched scope only on intent keywords, so an autonomous loop could keep running the same stalled campaign by rewording the task intent to avoid every marker. Adding output-path and task-type matching makes same-lane work that writes into the campaign's owned output class in-scope regardless of wording — closing the rephrasing escape while still not over-blocking genuinely unrelated work.
- **Validation**: `python3 checks/check_task_preflight.py`; `python3 checks/check_campaign_contract.py`; `python3 checks/run_harness_checks.py --profile full --timeout 90` (all pass).
- **Does not prove**: that all same-campaign work is caught (semantic paraphrase writing to a novel output class can still evade; markers/outputs/task-types are owner-declared); scientific validity; claim or gate approval.
- **Next check**: Backfill this pending entry with the commit hash.
## 2026-07-10 — Infer campaign output classes from progress history

- **Commit(s)**: `d833d88`
- **Change type**: framework / execution-gate enforcement / anti-evasion
- **Action**: Added `infer_campaign_output_classes(root)` which learns a campaign's output footprint from the `allowed_outputs` of the task contracts that already recorded campaign progress, excluding generic scaffolding dirs (`agent_runs/`, `audits/`, `outputs/`, `work/`, `discovery/`, `tasks/`, `decisions/`, `docs/`) so only campaign-specific classes (e.g. `data/backfill/`) are learned. `match_campaign_scope` now unions these inferred classes with the owner-declared `objective_outputs`, and `task_preflight` passes them in. A `check_task_preflight.py` fixture locks in that a campaign declaring NO `objective_outputs` still blocks reworded same-output work via the inferred class, while unrelated output and generic dirs stay free.
- **Why**: Closes the last easy evasion of the campaign breaker: previously an owner had to declare `objective_outputs` for the output dimension to catch reworded work. Now the guard learns the real output class from the campaign's own progress even when nothing was declared, so rewording the intent AND omitting the declaration no longer escapes a stopped campaign.
- **Validation**: `python3 checks/check_task_preflight.py`; `python3 checks/check_campaign_contract.py`; `python3 checks/run_harness_checks.py --profile full --timeout 90` (all pass).
- **Does not prove**: that a task writing to a genuinely novel output class the campaign has never used is caught; that inference is complete when progress-task contracts are archived/deleted; scientific validity; claim or gate approval.
- **Next check**: Backfill this pending entry with the commit hash.
## 2026-07-10 — Complete the campaign structure: human valve, FREEZE, metric verification, cache, CLI

- **Commit(s)**: `949b37e`
- **Change type**: framework / execution-gate enforcement / structural completion
- **Action**: Closed the five audited gaps in the campaign circuit-breaker structure. (1) **Human release valve**: `campaigns/campaign_decisions.yml` recorded via `aeros campaign continue|stop` and consumed by `assess_campaign` — a `continue` decision releases a named breaker (or all) for a bounded number of tasks then re-applies (forcing re-review); a `stop` decision halts the campaign with a `human_stop` breaker. The human's answer is now a first-class, bounded, re-reviewed record instead of a contract hand-edit. (2) **FREEZE/convergence**: a `convergence_freeze` breaker fires when the objective metric holds within `convergence_epsilon` across the last `convergence_window` tasks — the positive "results converged, stop expanding and request finalize" counterpart to the stall breakers. (3) **Metric anti-inflation**: `record_campaign_progress` now rejects an empty evidence file and a declared integer gain larger than the evidence's data-row count, so a task cannot report a large `metric_after` pointing at a tiny real file. (4) **Performance**: `infer_campaign_output_classes` is memoized per process on the progress file's identity so repeated preflights do not re-glob `tasks/**`. (5) **Onboarding**: `aeros campaign new` scaffolds a contract from the template. Added fixtures for freeze, continue-release-with-expiry, stop-halt, and metric anti-inflation.
- **Why**: The enforcement chain (assess → preflight BLOCK → run) was complete but one-directional: it could stop the loop but the human's continue/stop answer was not a first-class record, there was no convergence signal, and the yield metric was self-declared. These additions make the loop bidirectional and harder to fool without adding a new authority layer or LLM semantics.
- **Validation**: `python3 checks/check_campaign_contract.py`; `python3 checks/check_task_preflight.py`; `python3 -m aeros.cli campaign new|continue|stop|assess`; `python3 checks/run_harness_checks.py --profile full --timeout 90` (all pass).
- **Does not prove**: that convergence thresholds are scientifically right; that a fractional/rate metric is verified beyond non-emptiness; that a human continue decision is wise; that inference is complete when task contracts are archived; scientific validity; claim or gate approval.
- **Next check**: Backfill this pending entry with the commit hash.
## 2026-07-10 — Fix: zero-gain campaign tasks must record (found by end-to-end dogfood)

- **Commit(s)**: `411f941`
- **Change type**: framework / bugfix / campaign metric verification
- **Action**: An end-to-end campaign lifecycle dogfood (fresh init project, real completion path, real `aeros run`, real CLI decisions) exercised all six phases. Phases 1-4 and 6 passed (breaker emerged from real accumulated progress, `aeros run` blocked at the entrypoint, `campaign continue` released it, the release expired and re-armed, `campaign stop` halted). Phase 5 (convergence FREEZE) failed to fire because the metric anti-inflation check rejected legitimate zero-gain tasks as "empty evidence", so the plateau they represent was never recorded. Removed the standalone empty-evidence rejection; only a claimed positive integer gain must be backed by that many evidence rows. Added a regression fixture that a zero-gain task records while an inflated gain is still rejected.
- **Why**: A task that finds nothing new is the diminishing-returns/plateau signal that `low_marginal_yield` and `convergence_freeze` need to see; rejecting it suppressed convergence detection. The fixtures had tested inflation but never the legitimate zero-gain case — the dogfood caught it.
- **Validation**: `python3 checks/check_campaign_contract.py`; end-to-end dogfood now passes all six phases incl. `convergence_freeze`; `python3 checks/run_harness_checks.py --profile full --timeout 90` (all pass).
- **Does not prove**: that all metric semantics are captured; that a zero-gain task did real work; scientific validity; gate approval.
- **Next check**: Backfill this pending entry with the commit hash.
## 2026-07-10 — Add repeatable campaign end-to-end lifecycle check

- **Commit(s)**: `b996e7e`
- **Change type**: framework / test coverage / regression guard
- **Action**: Added `checks/check_campaign_e2e.py`, a repeatable end-to-end lifecycle check that drives the whole campaign loop through the real code paths in a throwaway project and asserts system-level behaviour: (1) a breaker emerges from real accumulated diminishing-returns progress, (2) `run_task` blocks the next same-campaign task at the real entrypoint, (3) a recorded human `continue` decision releases the breaker, (4) the release expires and the breaker re-arms, (5) a plateaued objective metric raises `convergence_freeze`, (6) a recorded human `stop` decision halts the campaign. Registered in the CHECKS list so it runs in the full profile.
- **Why**: The zero-gain bug just fixed passed every unit fixture but broke the system-level behaviour (convergence detection). A lifecycle test that runs the full loop would have caught it; this locks that coverage in so future campaign changes are validated as a system, not only as isolated units.
- **Validation**: `python3 checks/check_campaign_e2e.py`; `python3 checks/run_harness_checks.py --profile full --timeout 120` (all pass).
- **Does not prove**: that real-project campaigns behave identically; that the throwaway fixture covers every metric shape; scientific validity; gate approval.
- **Next check**: Backfill this pending entry with the commit hash.
## 2026-07-11 — Bind campaign decisions to human approval and verify unique metric gain

- **Commit(s)**: `dc41c54`
- **Change type**: framework / authority enforcement / campaign metric integrity
- **North star:** A stopped autonomous campaign cannot release itself, and duplicate evidence cannot manufacture progress.
- **Action**: Required `aeros campaign continue|stop` to consume a project-local approval artifact whose clean git author is an configured approver identity; removed caller-supplied reviewer authority and recorded the verified author, approval path, date, and decision reference. Protected the campaign decision log with the existing pre-commit guard. Reversed the E2E fixture so an approval-free self-release fails and a committed human fixture alone releases the breaker. Campaign progress now checks metric continuity and computes novel evidence units using declared CSV/TSV unique keys (or the first column by default), excluding duplicates and units already counted by prior campaign tasks.
- **Validation**: targeted campaign, E2E, protected-path, task-preflight, ledger, smoke, and full harness checks.
- **Non-goal**: Do not judge whether a continuation is scientifically wise, whether an evidence unit is relevant, or whether a metric definition is optimal.
- **Does not prove**: scientific validity; source quality; claim support; gate approval; resistance to a human who intentionally shares the approver identity with an autonomous agent.
- **Drift risk**: Legacy campaign decisions without approval metadata are readable for history but no new decision can be created without a committed approval. Non-tabular evidence uses unique non-empty lines and remains a mechanical verifier only.
- **Next check**: Roll out to the next active campaign and confirm an agent-authored approval is rejected while a human-committed bounded continuation succeeds.
## 2026-07-11 — Converge authority, research value, artifact state, job compilation, and adaptive checks

- **Commit(s)**: `dc41c54`
- **Change type**: framework / runtime convergence / control-tax reduction
- **North star:** Reduce the cost of truthful research progress by strengthening real authority boundaries while removing duplicated declarations and daily checks.
- **Action**: Reclassified Git approver evidence as `local_authorship`, added fail-closed signed/external authority levels and a scoped `aeros approve`; added seven evidence-bound research-value events and `low_decision_value`; split artifact state into selection/processing/admission with legacy output-intent projection; compiled one `data_probe` ResearchJob into TaskContract, ActionSpec, and ExecutionEnvelope with monotonic authority; mapped observed writes to six risk domains; reduced smoke from 54 to 15 core checks and pre-drive to three checks; retained the complete full harness. De-vendor remains gated on real-project rollout.
- **Validation**: authority, campaign, artifact semantics, ResearchJob, adaptive selection, sync doctor, pre-drive, smoke, and full harness.
- **Non-goal**: Do not claim Git authorship proves a real person; do not treat novel units as research value; do not force legacy artifact migration; do not de-vendor before real-project evidence.
- **Does not prove**: scientific validity; research-value event importance; signed approval wisdom; external identity; optimal check selection; safe package migration.
- **Drift risk**: Legacy output intents remain projections; local authorship is forgeable under a hostile local agent; adaptive path rules are deterministic and may conservatively select extra checks.
- **Next check**: Roll the first four batches into one clean active project, measure pre-drive/post-action latency and substantive issue detection, then decide whether De-vendor admission is earned.
## 2026-07-11 — Infer research value so low_decision_value reflects real value, not annotation

- **Commit(s)**: `9b24b32`
- **Change type**: framework / campaign breaker / false-positive reduction
- **Action**: Added `infer_research_value_events(root)` and wired it into the `low_decision_value` breaker so it fires on `declared ∪ inferred == ∅`. Inference recognises decision-relevant value from high-confidence framework artifacts (a registered result, a grounded claim, a closed data gap, a resolved replication blocker) produced *since the campaign started* (anchored to the contract mtime, so pre-campaign results grant no permanent immunity; unreadable mtimes fail safe → the breaker still fires). When it does fire, the recommended action states both readings (genuinely no value → stop/reconsider, or value produced but unrecorded → record it); when value is inferred but not declared, `inferred_research_value` + `unrecorded_value_hint` nudge formal recording. Documented the fix and a calibration note (count-based breakers under-fire on front-loaded trajectories; value-based is the robust primary signal) in docs/design/campaign_circuit_breaker.md. This was motivated by a read-only assess over MAHA's real literature-collection history.
- **Why**: `low_decision_value` previously fired purely on absence of annotation, conflating "no decision value" with "value produced but not recorded" — a false-positive risk on real projects. Inference from unforgeable artifacts keeps the "prove value, not volume" pressure while cutting false alarms.
- **Validation**: `python3 checks/check_campaign_contract.py`; `python3 checks/check_campaign_e2e.py`; `python3 checks/run_harness_checks.py --profile full` (all pass on the combined batch).
- **Does not prove**: that inferred artifacts truly advanced a decision; that mtime anchoring is tamper-proof; scientific validity; gate approval.
- **Next check**: Backfill this pending entry with the commit hash.
## 2026-07-11 — Prove signed authority, research value, and ResearchJob post-checks end to end

- **Commit(s)**: `5915b06`
- **Change type**: framework / vertical validation / no new control surface
- **North star:** Replace template-green claims with executable system-level evidence.
- **Action**: Extended existing full-only lifecycle checks rather than adding daily checks. A temporary SSH key now signs an approval produced by `aeros approve`; `git verify-commit` validates it before campaign consumption. Parallel campaign fixtures prove that quantity-only work trips `low_decision_value` while an evidence-bound `resolved_data_gap` prevents it. The `data_probe` ResearchJob now compiles to a real deterministic action that reads CSV, records source SHA-256/rows/columns, executes in an isolated worktree, copies back only the declared report, maps the observed write to `data_sample_integrity`, and runs the selected probe post-check.
- **Validation**: `check_campaign_e2e.py`; `check_research_job_compiler.py`; `check_adaptive_checks.py`; sync doctor; smoke; full harness.
- **Non-goal**: Do not claim SSH key possession proves a real-world person; do not score scientific importance; do not de-vendor based on template fixtures alone.
- **Does not prove**: production key custody; external approval; data fitness; optimal check selection; safe package migration.
- **Drift risk**: Signed approval security depends on keeping the signing key outside agent authority. The fixture intentionally verifies mechanics, not production custody.
- **Next check**: Commit the template, then run the same bounded data-probe and adaptive post-check path in one clean real project before admitting De-vendor.
## 2026-07-11 — Admit additive De-vendor package mode after real-project rollout

- **Commit(s)**: `69935a3`
- **Change type**: framework / packaging / incremental migration
- **North star:** Remove runtime-copy tax without sacrificing local reproducibility or deleting project state.
- **Action**: Cultured-meat commits `563b64d5` and `bdda9324` proved the first four convergence batches on a real bounded data probe. Switched setuptools to discover every `aeros*` namespace, added `.aeros/project.yml` plus `aeros.lock`, additive `aeros migrate inspect|prepare`, and `aeros doctor`. Added a full-only E2E that builds a fresh venv, installs AEROS locally, creates a project with no vendored runtime/check/policy directories, prepares package mode, and requires doctor PASS. Migration never deletes vendored files automatically.
- **Validation**: cultured-meat sync doctor, isolated probe, adaptive post-checks, smoke; `check_devendor_package.py`; template smoke/full.
- **Non-goal**: Do not remove vendored runtime from existing projects, auto-migrate policy customizations, or claim package mode preserves every downstream override.
- **Does not prove**: safe migration of every legacy project; scientific validity; release readiness; external package-index availability.
- **Drift risk**: Projects must pin `aeros_version`, runtime identity, policy bundle, and schema in `aeros.lock`; custom vendored policy changes need explicit migration review.
- **Next check**: Keep cultured meat vendored until package mode runs alongside it for one additional project action, then use an explicit removal plan rather than automatic deletion.

## 2026-07-11 — Add authority lifecycle hardening and an isolated official economic-data probe

- **Commit(s)**: `dc41c54`
- **Change type**: framework / authority lifecycle / Econ Pack / bounded official-data execution
- **North star:** Move AEROS from arranging economics work toward completing one truthful, permission-bounded economics action without weakening human authority.
- **Alignment**: Ordered authority evidence now has non-weakenable action floors, signer-to-approver binding, committed-policy verification, signed policy rotation, and an explicit TOFU bootstrap boundary. Econ Pack adds referential Sample → Specification → Result → Exhibit → Sentence → Claim registries, advisory method protocols, literature radar, and evidence-aware skill scorecards. `aeros drive --job probe_data --execute` compiles an official Census/FRED probe into a declared ActionSpec and isolated-worktree ExecutionEnvelope, accepts only exact nonproduction probe/provenance outputs, and runs deterministic coverage, missingness, join-key, source-ID, and hash checks.
- **Validation**: Authority lifecycle E2E; campaign authority checks; Econ Pack checks; Census missing-key and fixture checks; real no-key FRED GDP probe through `drive` and isolated-worktree acceptance; execution-envelope, drive, sync-doctor, smoke, and full harness checks.
- **Non-goal**: Do not add FRED metadata-key integration, provision a Census API key, promote probe data to canonical, execute estimator protocol packs, certify a scientific claim, or expand the feature surface beyond this vertical slice.
- **Does not prove**: first-bootstrap real-world human presence; safe signing-key custody; Census positive network execution; FRED vintage history; provider-verified FRED units without its metadata API; computational lineage from specification to result; scientific validity; claim support; gate approval; paper readiness.
- **Drift risk**: The first signer bootstrap remains local TOFU; FRED current-release CSV is not an ALFRED vintage; Census live access remains credential-blocked; Econ object registries currently prove referential consistency rather than executor-produced lineage; legacy skill receipts will yield sparse scorecards rather than fabricated zeros.
- **Next check**: After this batch is committed and hash-backed, choose one narrow follow-up only: either add authenticated FRED metadata verification or provide a Census key for a positive official-network E2E. Do not do both or add a new horizontal module in the same batch.

## 2026-07-12 — Reduce process ceremony behind immutable research boundaries

- **Commit(s)**: `6453b9e`
- **Change type**: framework / profile mapping / control-tax reduction / measurement protocol
- **North star:** Maximize model capability inside reversible candidate work while enforcing only boundaries that cannot safely be delegated.
- **Alignment**: Added a mapping-only `explore/research/submit/regulated` profile policy with `research` as the user-facing default and exactly eight profile-invariant authority/evidence/resource rules. Ordinary tasks may now use zero skills without a waiver; only explicit `required_skill_classes` create completion-level use-or-waive enforcement. Recorded the candidate-worktree default design without claiming provider/LLM sandboxing, and added a paired real-project A/B protocol that measures accepted artifacts, control tax, human interruptions, and safety escapes before any old rule can be retired. Smoke remains 18 checks by replacing skill ceremony with profile/invariant validation rather than adding another daily check.
- **Validation**: `check_execution_profiles.py`; `check_skill_coverage.py`; `check_skill_use_attestation.py`; `check_sync_doctor.py`; `check_architecture_freeze.py`; smoke 18/18; full 139/139.
- **Non-goal**: Do not enable model-led planning, add a hypothesis/memory registry, delete Campaign, weaken signed authority, auto-retire checks, claim provider/LLM sandboxing, or start the real-project A/B before this baseline is committed.
- **Does not prove**: lower control tax; better model decisions; higher artifact acceptance; safe provider/LLM isolation; scientific validity; claim support; promotion, submission, or release approval.
- **Drift risk**: Downstream projects retain their old skill ceremony until explicitly synced. `research_profiles.yml` is mapping-only, so callers must not represent it as a runtime sandbox switch. Required skill classes remain fail-closed at completion even though ordinary recommendations no longer require waivers.
- **Next check**: Sync one clean project per A/B arm, pair comparable bounded episodes using `docs/design/profile_ab_protocol.md`, and inspect every safety escape before considering any rule retirement.
## 2026-07-11 — Make de-vendor package check portable across host Pythons

- **Commit(s)**: `1e7c298`
- **Change type**: framework / test robustness / bugfix
- **Action**: Fixed `check_devendor_package.py` so the package-mode E2E passes under any host Python, not only one that happens to be a 3.10+ interpreter carrying PyYAML. Three fixes: (1) build the install venv with a `>=3.10` interpreter (was `sys.executable`, which broke when the harness ran under Python 3.9 — the wheel requires `>=3.10`); (2) add real `python3.10/3.11/3.12/3.13` via `shutil.which` to the build-Python candidate list instead of only machine-specific hardcoded paths; (3) require `yaml` in the candidate probe — the check installs `--no-deps` and relies on `--system-site-packages` for PyYAML, so it must select a Python that actually has PyYAML (a homebrew 3.11 without it made `migrate prepare` die on `import yaml`, surfacing as "lock files missing").
- **Why**: Full harness went red purely on the host Python: `python3` = 3.9.13 → wheel install refused; auto-selected homebrew 3.11 → missing PyYAML. The de-vendor logic itself was fine; the check's environment assumptions were not.
- **Validation**: `checks/check_devendor_package.py` passes under Python 3.9, 3.10, and 3.14 ambients; `python3.10 checks/run_harness_checks.py --profile full` (all pass).
- **Does not prove**: that every exotic host Python is supported; that de-vendor removal is safe; scientific validity.
- **Next check**: Backfill this pending entry with the commit hash.
## 2026-07-13 — Fail-close candidate profiles from real-project paired A/B

- **Commit(s)**: 2992742
- **Change type**: framework / adaptive profile enforcement / rollout evidence
- **North star:** Reduce control tax only where real-project evidence shows that truthful progress remains observable.
- **Action**: Converted the existing adaptive selector into a fail-closed post-action assessment when callers provide an observed action exit and expected outputs. Nonzero or missing exits and missing, empty, or out-of-worktree expected outputs now fail. Added analysis/figure and manuscript path mappings to result-registry, reproducibility, and provenance checks. Recorded the CMPD/MAHA/VLM paired decision: no rule is retired; candidate profiles remain reversible preflight only.
- **Validation**: python3 checks/check_adaptive_checks.py; python3 checks/check_execution_profiles.py; smoke/full harness; paired MAHA and VLM reruns after downstream sync.
- **Non-goal**: Do not add a new runtime module, infer omitted dependencies, certify output freshness, retire full checks, approve claims/gates, or authorize promotion/release.
- **Does not prove**: scientific validity; complete path coverage; freshness of a pre-existing non-empty artifact; that lower control time generalizes beyond the paired tasks.
- **Drift risk**: Callers must declare material dependency paths in addition to observed writes. An omitted dependency can still suppress a relevant check, so promotion/release remains on strict/full.
- **Next check**: Sync MAHA and VLM, rerun the original paired episodes, and require candidate failure or visibility for the provenance/action-exit issues previously missed.

## 2026-07-13 — Enforce candidate execution, profile-selected checks, dynamic skills, and tiered citation verification

- **Commit(s)**: `c2cb768`
- **Change type**: framework / runtime enforcement / control-tax reduction / manuscript evidence integrity
- **North star:** Give capable agents broad freedom inside reversible candidate work while keeping promotion, authority, evidence, and submission boundaries mechanically strict.
- **Action**: Made isolated candidate worktrees the default for write-producing agent and provider collection actions; only declared, nonempty, conflict-free outputs are accepted back into the canonical workspace, while denied or undeclared writes fail closed. Activated immutable `explore/research/submit/regulated` runtime profiles: explore/research select post-action checks from observed artifacts, submit adds the paper/citation/result/provenance floor and automatically requires the submission review skill class, and regulated preserves full contract checks. Ordinary dynamic skills remain optional and capped at three, but actual use must record findings and artifact impact. Added explicit citation Tier 0/1/2 semantics: Tier 0 requires bibliographic mapping, Tier 1 requires passage/locator/interpretation plus medium-or-high automated verification, and Tier 2 requires full text, approved interpretation, and an independent verifier with source fingerprint. Added a fail-safe contract-check fallback for minimal or older projects lacking the adaptive-check catalog.
- **Validation**: Seven targeted checks pass (`agent_envelope`, `execution_profiles`, `skill_use_attestation`, `skill_coverage`, `manuscript_citation_interpretation`, `manuscript_citation_faithfulness`, `sync_doctor`); smoke 18/18; full 139/139. Adversarial fixtures prove denied/undeclared writes do not enter canonical state and Tier 2 cannot pass without independent verification.
- **Non-goal**: Do not auto-promote candidate outputs, auto-approve claims/gates/releases, treat skill use as scientific correctness, or claim automated passage matching proves interpretation truth.
- **Does not prove**: scientific validity; safe external credential use; optimal skill selection; correctness of a human interpretation; real-world verifier identity; claim, gate, submission, or release approval.
- **Drift risk**: Projects without `adaptive_checks.yml` conservatively run explicit contract checks; downstream projects do not gain these defaults until migrated or synced; Tier 1 automated verification quality still depends on the verifier implementation and recorded source basis.
- **Next check**: Backfill this pending entry with the functional commit hash, then run a bounded real-project submission-profile episode before retiring any older process checks.

## 2026-07-13 — Route mature candidate pools without broad-capture ceremony

- **Commit(s)**: `97e57d1`
- **Change type**: framework / real-project rollout bugfix / control-tax reduction
- **North star:** Let AEROS respond to actual project state: stop broad capture when a usable candidate pool already exists, avoid irrelevant skill ceremony, and diagnose runtime mode without migration false positives.
- **Action**: Made broad-capture metrics denominator-honest (`lead_to_candidate_rate` is unavailable when no leads exist), added a deterministic 20-candidate triage threshold, and moved saturated candidate pools to candidate triage/promotion rather than another capture pass. Updated the research driver so this state surfaces as capture-efficiency risk with a concrete triage preflight. Broad-capture tasks no longer infer required skill classes unless a contract explicitly requires them; dynamic skill use remains available. Sync doctor now distinguishes vendored, package, and unknown runtime modes and marks de-vendor capability as not applicable for vendored projects. Reduced `check_econ_pack.py` startup cost by retaining all six pure job-compilation assertions while exercising one representative CLI dispatch instead of spawning six redundant processes.
- **Validation**: `check_broad_capture_firewall.py`, `check_drive.py`, `check_task_preflight.py`, `check_skill_coverage.py`, and `check_sync_doctor.py` pass; smoke 18/18 at a 30-second per-check ceiling; full harness 139/139 at a 60-second ceiling. A 20-second smoke attempt timed out only on the existing authority lifecycle E2E under host load; that check passed directly and in the 30-second smoke run.
- **Non-goal**: Do not auto-promote candidates, infer candidate quality from count, forbid optional skills, migrate vendored projects, alter claims/gates, or certify scientific validity.
- **Does not prove**: that 20 is optimal for every project; that any candidate is admissible evidence; that triage will produce a canonical artifact; that skill-free capture is scientifically sufficient; or that package migration is unnecessary.
- **Drift risk**: The threshold is a deterministic default and may need project-level calibration. Projects without explicit candidate counts cannot benefit from saturation routing. Runtime-mode detection is structural and does not prove a vendored copy is current.
- **Next check**: Backfill the functional commit hash, then resync the VLM project and confirm its 0-lead/697-candidate state routes to triage, carries no inferred skill obligation, and reports vendored mode without a de-vendor false positive.

## 2026-07-13 — Register compile-QA and repository-rigor skills

- **Commit(s)**: pending
- **Change type**: framework / skill registry / downstream integrity repair
- **North star:** Keep skill receipts mechanically honest without granting skills scientific or approval authority.
- **Action**: Added bounded core-map entries for the already installed `latex-compile-qa` and `project-rigor-check` skills, which were named by the practical menu and valid downstream contracts but absent from the machine-readable registry. The skill-layer check now requires both entries so the omission cannot silently recur.
- **Validation**: Targeted skill-layer, skill-invocation, improvement-backlog, and update-ledger checks; downstream CMPD sync and approval-integrity validation remain required before closing the backlog item.
- **Non-goal**: Do not rewrite prior skill receipts, waive missing invocations, certify LaTeX content, treat repository hygiene as research evidence, or approve a gate.
- **Does not prove**: correct skill use; scientific validity; citation truth; reproducibility; claim support; gate or release approval.
- **Drift risk**: Projects remain on their vendored map until synced; project-owned backlog entries must be preserved during the framework rollout.
- **Next check**: Commit the template, sync the clean CMPD project with `tools/sync_aeros_latest.zsh`, and require `check_skill_invocations.py` plus `check_approval_integrity.py` to pass there.

## 2026-07-13 — Repair full-text skill registration and bibliography lane routing

- **Commit(s)**: pending
- **Change type**: framework / skill registry / exact work-lane routing
- **North star:** Keep source verification auditable without forcing a source-identity repair to masquerade as manuscript writing.
- **Action**: Registered `sci-download` inside the machine-readable `skills:` map and removed the unreachable duplicated subtree created by the prior root-level insertion. Added one exact literature-lane exception for `tex/references.bib`; all other `tex/` paths, including `tex/paper.tex`, remain forbidden. Corrected session semantics so the append-only update-ledger hash chain is bookkeeping, while real `decisions/` and claim authority remain protected. Added parsed-name, allow/deny, and semantic-classification regression assertions.
- **Validation**: `check_skill_layer.py`, `check_skill_invocations.py`, `check_work_lanes.py`, `check_session_scope.py`, improvement-backlog validation, update-ledger validation, hash-chain validation, and downstream CMPD sync/checks.
- **Non-goal**: Do not broaden literature tasks into manuscript editing, certify downloaded PDFs, rewrite task receipts, or weaken gate/claim authority.
- **Does not prove**: source truth; full-text interpretation quality; citation support; scientific validity; claim, gate, submission, or release approval.
- **Drift risk**: Downstream vendored projects retain the malformed map and coarse lane rule until an official sync; the exact exception must not become a prefix exception.
- **Next check**: Commit the template, sync clean CMPD, and require T026 skill, lane, bibliography, and session checks to pass before completing the task.

## 2026-07-13 — Backfill skill/lane registry repair commit

- **Commit(s)**: `7cc59a3`
- **Change type**: ledger backfill
- **Action**: Bound the skill-registration, exact bibliography-lane, and update-ledger session-classification repair to its functional commit and closed AEROS-IMPROVE-036/037.
- **Validation**: Template full profile passed 139/139 before commit; update-ledger and append-only hash-chain checks rerun after this backfill.
- **Does not prove**: source truth, citation support, scientific validity, claim or gate approval.

## 2026-07-13 — Preserve downstream backlog ownership and align skill-class validation

- **Commit(s)**: pending
- **Change type**: framework / sync ownership / skill receipt validation
- **North star:** Framework rollout must not erase project obligations, and one skill-use fact must receive the same verdict from every validator.
- **Action**: Changed official sync to preserve an existing project `harness/improvement_backlog.yml` and seed it only when absent. Changed invocation validation to recognize skills listed as candidates for a required class, matching completion attestation semantics, and added fixtures for both contracts.
- **Validation**: Skill-use attestation, skill-invocation, sync-doctor, backlog, update-ledger, hash-chain, smoke/full profile, then a second clean CMPD sync with its 036/037/038 entries byte-preserved.
- **Non-goal**: Do not merge template backlog facts into downstream projects, waive missing required skills, or certify skill output.
- **Does not prove**: research progress, source truth, citation support, scientific validity, claim or gate approval.
- **Next check**: Commit, sync CMPD, verify its backlog hash is unchanged, and complete T026 only after all task checks pass.

## 2026-07-13 — Backfill sync/skill validation repair commit

- **Commit(s)**: `d366738`
- **Change type**: ledger backfill
- **Action**: Bound the project-backlog preservation and required-skill validator parity repair to its functional commit and closed AEROS-IMPROVE-038/039.
- **Validation**: Targeted checks and smoke 18/18 passed before commit; downstream hash-preservation and T026 checks remain the rollout proof.
- **Does not prove**: research progress, skill output correctness, scientific validity, claim or gate approval.

## 2026-07-13 — Scope sync-script assertions to template mode

- **Commit(s)**: pending
- **Change type**: framework / sync-doctor mode boundary
- **Action**: Kept source-level assertions for the template-only sync driver when that file exists, while allowing vendored downstream projects to run sync-doctor capability checks without the intentionally unsynced driver.
- **Validation**: Template and CMPD sync-doctor checks plus smoke profile.
- **Does not prove**: project currency, research validity, claim support, or gate approval.

## 2026-07-13 — Backfill sync-doctor mode-boundary commit

- **Commit(s)**: `40ef1dc`
- **Change type**: ledger backfill
- **Action**: Bound the template/downstream sync-doctor guard to its functional commit and closed AEROS-IMPROVE-040.
- **Validation**: Template smoke 18/18 before commit; downstream CMPD sync-doctor remains the rollout check.
- **Does not prove**: project currency, research validity, claim support, or gate approval.

## 2026-07-13 — Accept project citation identifiers in the citation audit

- **Commit(s)**: `f648361`
- **Change type**: framework / citation audit parser / regression fixture
- **North star:** Keep citation-faithfulness checks fail-closed without confusing a parser vocabulary mismatch with missing literature evidence.
- **Action**: Extended `check_citation_audit.py` to parse both `P###` and `CITE###` identifiers. Factored row-level faithfulness validation into one path and added an executable fixture proving both identifier families are visible while a `TBD` claim-support field still fails closed.
- **Validation**: Citation-audit, improvement-backlog, update-ledger, hash-chain, smoke, and full-profile checks before downstream sync.
- **Non-goal**: Do not create citation-audit rows, verify source identity, approve sentence interpretations, strengthen claims, or change downstream projects outside the official sync path.
- **Does not prove**: bibliographic truth; full-text interpretation quality; manuscript sentence support; scientific validity; claim, gate, submission, or release approval.
- **Drift risk**: Vendored projects remain unable to recognize `CITE###` audit rows until officially synced; audit presence alone must not be treated as passage-level claim support.
- **Next check**: Commit the template repair, sync clean CMPD, add the seven source-bounded audit rows, and require the complete T025 contract to pass.

## 2026-07-13 — Backfill citation-audit parser repair commit

- **Commit(s)**: `f648361`
- **Change type**: ledger backfill
- **Action**: Bound the `P###`/`CITE###` parser compatibility and fail-closed regression fixture to its functional commit and closed AEROS-IMPROVE-041.
- **Validation**: Targeted checks, smoke 18/18, full 139/139, and session-scope audit passed before the functional commit.
- **Does not prove**: source truth, passage interpretation, manuscript sentence support, scientific validity, or claim/gate/submission/release approval.

## 2026-07-13 — Require explicit citation-audit table rows

- **Commit(s)**: `b3cda68`
- **Change type**: framework / citation audit / fail-closed coverage
- **North star:** Ensure citation coverage is demonstrated by inspectable faithfulness fields rather than an identifier appearing somewhere in prose.
- **Action**: Removed the union between parsed audit rows and arbitrary `P###`/`CITE###` tokens in the audit document. Added an executable fixture where `CITE011` appears only in narrative text and must remain outside the audited-ID set.
- **Validation**: Citation-audit, improvement-backlog, update-ledger, hash-chain, smoke, and full-profile checks before downstream sync.
- **Non-goal**: Do not judge the substantive truth of an audit row, create sentence interpretation records, edit a manuscript, or change any downstream project outside official sync.
- **Does not prove**: source truth; passage interpretation; manuscript sentence support; scientific validity; claim, gate, submission, or release approval.
- **Drift risk**: Downstream vendored checks retain the narrative-token bypass until officially synced; explicit row presence still cannot substitute for Tier-1 sentence interpretation.
- **Next check**: Commit, sync clean CMPD, verify all seven explicit T025 rows pass, and close the project-local parser obligation in a harness-scoped change.

## 2026-07-13 — Backfill explicit citation-audit row commit

- **Commit(s)**: `b3cda68`
- **Change type**: ledger backfill
- **Action**: Bound narrative-token bypass removal and its executable fixture to the functional commit and closed AEROS-IMPROVE-042.
- **Validation**: Targeted checks, smoke 18/18, full 139/139, and session-scope audit passed before the functional commit.
- **Does not prove**: source truth, passage interpretation, manuscript sentence support, scientific validity, or claim/gate/submission/release approval.

## 2026-07-13 — Align canonical Tier-1 records across citation scanners

- **Commit(s)**: `9aa5f43`
- **Change type**: framework / sentence grounding / tier semantics
- **North star:** One honest citation interpretation record should receive one consistent verdict across AEROS checks without fabricated human approval.
- **Action**: Added content-key lookup for canonical records when the legacy line-bearing sentence ID differs, changed method-precedent evidence from human-approved to Tier-1 automated interpretation, and taught the legacy verifier to accept only explicit Tier-1 records with faithful medium/high automation plus verifier metadata. Human-approved records remain valid; Tier-2 automation without human approval remains blocking. Added both positive and negative executable fixtures.
- **Validation**: Both citation checks, the literature wrapper, backlog/ledger/hash-chain checks, smoke, and full profile before downstream sync.
- **Non-goal**: Do not auto-create project interpretation records, certify source passages, infer human review, or weaken Tier-2 independent verification in the submission scanner.
- **Does not prove**: interpretation correctness; source truth; manuscript support; scientific validity; claim, gate, submission, or release approval.
- **Drift risk**: Vendored projects retain incompatible IDs and Tier-1 semantics until official sync; content lookup requires an exact normalized manuscript sentence and citation key, so prose edits correctly invalidate the record.
- **Next check**: Commit, sync clean CMPD, create the 36 canonical source/rendered Tier-1 records under T027, and require both scanners to report zero weak/blocking rows without any human-approval fabrication.

## 2026-07-13 — Backfill canonical Tier-1 citation compatibility commit

- **Commit(s)**: `9aa5f43`
- **Change type**: ledger backfill
- **Action**: Bound canonical record lookup, Tier-1 automated verification, and the Tier-2 negative fixture to the functional commit and closed AEROS-IMPROVE-043.
- **Validation**: Targeted citation/literature checks, smoke 18/18, full 139/139, and session-scope audit passed before the functional commit.
- **Does not prove**: interpretation correctness, source truth, manuscript support, scientific validity, or claim/gate/submission/release approval.

## 2026-07-13 — Converge candidate semantics and execute a bounded specification job

- **Commit(s)**: `f63e583`
- **Change type**: framework / runtime convergence / economics execution
- **North star:** Reduce control-surface overstatement while making one economics job produce inspectable candidate artifacts under real isolation.
- **Action**: Replaced search-saturation language with candidate-backlog and broad-capture-pause semantics while retaining deprecated compatibility projections; made vendored/package coexistence an explicit hybrid runtime mode; exercised all six economics drive handlers in process; made source-checkout initialization consume the canonical profile seed; measured the unchanged smoke profile; and added a fail-closed `run_specification` vertical slice that reads a registered CSV/OLS specification, executes in an isolated worktree, and emits nonproduction JSON plus exhibit CSV artifacts with provenance and adaptive post-check selection.
- **Validation**: Eight targeted checks passed; smoke passed 18/18 in 18.752 seconds; full harness passed 139/139; `git diff --check` passed.
- **Non-goal**: Do not claim search-space saturation, remove checks from smoke without detection/overlap evidence, support fixed effects/clustering/weights or arbitrary estimators, promote candidate outputs, modify downstream projects, or certify a specification scientifically.
- **Does not prove**: data fitness; identification validity; model correctness beyond the bounded fixture; result admission; claim support; canonical promotion; gate, submission, or release approval.
- **Drift risk**: The legacy capture fields remain temporary compatibility aliases; installed-package fallback seeds remain bootstrap-only when canonical checkout files are unavailable; the first specification executor intentionally rejects unsupported estimator features rather than guessing.
- **Next check**: Backfill the functional commit hash, then roll the bounded specification job into one clean real project only when that project's registered data contract and specification actually require it.

## 2026-07-13 — Backfill candidate/runtime convergence provenance

- **Commit(s)**: `f63e583`
- **Change type**: ledger backfill
- **Action**: Bound candidate-semantics downgrade, hybrid runtime recognition, economics handler coverage, effective init-profile parity, measured smoke cost, and isolated nonproduction specification execution to the functional commit; closed AEROS-IMPROVE-044 and REV048.
- **Validation**: Eight targeted checks, smoke 18/18, full 139/139, metadata checks, and staged diff hygiene passed before the functional commit.
- **Does not prove**: data fitness, identification validity, general econometric support, scientific validity, result admission, claim support, canonical promotion, or gate/submission/release approval.
## 2026-07-11 — Bounded autonomous execution + watchdog fingerprint hygiene fix

- **Commit(s)**: `428f8be`
- **Change type**: framework / autonomous execution / bugfix
- **Action**: Commits the coherent green batch that formalizes bounded autonomous execution — `controller_loop` (default-deny command execution: only read-only/dry-run/check unless `--allow-task-runs`), `episode_watchdog` (deterministic anti-loop stop/replan/cache decisions), `context_budget` (pointer-first token budgeting), `run_bundle` (content-addressed, fail-closed reproducible runs), and `check_specification_run` — plus this session's watchdog fingerprint-hygiene fix. `episode_watchdog.semantic_state_fingerprint` now strips per-save volatile metadata lines (`updated_at` in aeros_state.yml, written by `state.py` as `_now()` on every save; `last_validation` in CURRENT_STATE.md) before hashing, so a step that only re-stamps a timestamp is not mistaken for substantive state change. Without this the `no_state_change` stop never fired. A `check_next_action` fixture locks in that a re-stamped timestamp leaves the fingerprint unchanged while a substantive gate/stage change moves it.
- **Why**: The controller loop needs a trustworthy anti-loop watchdog; a volatile timestamp in a semantic-fingerprint file silently defeated one of its named stop conditions. Timestamps that accompany real progress (search_log/registry rows) are deliberately not stripped.
- **Validation**: `python3.10 checks/check_next_action.py`; `python3.10 checks/run_harness_checks.py --profile full` (all pass); demonstrated timestamp-only change → identical fingerprint, substantive change → different fingerprint.
- **Does not prove**: that every volatile field across all semantic files is covered; that the controller loop is useful in real projects; scientific validity; gate approval.
- **Next check**: Backfill this pending entry with the commit hash.

## 2026-07-25 — Add single-flight execution for expensive project jobs

- **Commit(s)**: pending
- **Change type**: framework / execution efficiency / real-project rollout
- **North star:** Expensive research jobs with unchanged declared inputs must attach, reuse, or stop instead of spawning another data-intensive process.
- **Action**: Added `aeros heavy` with a deterministic RunKey, atomic single-flight lease, byte-validated accepted-output cache, cost-class retry budget, unchanged-failure plateau, and compact Resume Pack. Added separate working/artifact roots, environment-aware external-data fallback, and fail-closed `BLOCKED_EXTERNAL_INPUT` status so disconnected drives do not become configuration errors or accidental reruns. Registered a real fixture in smoke and exposed the capability through sync doctor.
- **Validation**: `check_heavy_run.py` passed; smoke passed 19/19; Habit, Tobacco, and GLP1 read-only status calls returned `BLOCKED_EXTERNAL_INPUT` with no heavy process spawned while their external storage was unavailable.
- **Non-goal**: Do not execute project pipelines, recursively inventory large datasets, certify scientific validity, admit results, promote claims, or grant release authority.
- **Does not prove**: that every agent obeys project instructions instead of invoking Python directly; that disconnected external data are current; that project outputs pass their substantive acceptance gates.
- **Drift risk**: A job can only be safely reused when every identity-relevant script, configuration, manifest, and cheap stat input is declared. Project rollout remains blocked until its external roots are mounted and status is re-evaluated.
- **Next check**: Commit the framework slice, backfill its hash, then mount each project's external storage and run status only before authorizing any heavy execution.
