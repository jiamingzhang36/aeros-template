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

## 2026-07-01

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
