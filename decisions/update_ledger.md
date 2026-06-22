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

## 2026-06-22

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

### 2026-06-22 — Add literature full-text candidate verification semantics

**Commit(s)**: `pending`

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
