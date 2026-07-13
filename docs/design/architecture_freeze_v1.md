# AEROS Architecture Freeze v1

Date: 2026-06-23

## Freeze decision

AEROS is now frozen as an authority-aware local research runtime. The next phase
is not broader automation; it is enforcement, measurement, and external
verification of the existing architecture.

North star:

> AEROS does not decide what is true. It enforces what was authorized, verifies
> what was produced, invalidates what became stale, and stops where scientific
> responsibility begins.

## Five-layer model

1. Human Assertions
   - DataContract
   - ClaimRegistry
   - Decision artifacts
   - Human approvals and explicit limitations

2. Machine Facts
   - RunRecord
   - ArtifactManifest
   - ProvenanceRecord
   - ResultRecord machine fields

3. Runtime
   - WorkItem
   - ActionSpec
   - ExecutionEnvelope
   - Bounded controller loop
   - Run journal / receipts

4. Derived Views
   - cockpit
   - next
   - context
   - graph
   - global state
   - stale triage

5. Evaluation
   - smoke invariants
   - adversarial fixtures
   - project benchmarks
   - external reproduction

## Feature admission rule

No new core feature may enter AEROS unless it satisfies at least one condition:

- measurably reduces human pushes per accepted substantive artifact;
- measurably lowers false progress, unsupported-claim escape, or overclaim risk;
- measurably reduces recovery time after stale or failed runs;
- turns a previously declared boundary into an enforced boundary;
- is required to run a benchmark that would otherwise be impossible.

Features that do not satisfy this rule stay in backlog, external adapter, or
experimental plugin status.

## Do-not-expand list

The architecture-freeze baseline pauses:

- new lanes;
- new gates;
- new registries;
- new dashboards;
- new agent roles;
- new parser deep integrations;
- automatic prompt self-evolution;
- automatic paper-ready judgment while allowing non-authoritative readiness reports;
- automatic claim upgrade;
- automatic claim upgrade without a human gate;
- automatic release approval.

## Sequencing constraints

ExecutionEnvelope must be real confinement, not a declarative YAML promise. The
first implementation must run in an isolated worktree or equivalent isolated
workspace and must verify that observed writes are a subset of declared writes.
`aeros run` deterministic local commands (`run.command` with zero agent calls)
now execute through this isolated worktree path. LLM/provider-backed task runs
remain policy-gated but are not claimed as fully sandboxed until provider-side
isolated execution exists.

AgentEnvelope v1 adds audit-mode enforcement for provider-backed agent tasks:
after each agent call, AEROS blocks task acceptance if observed writes are
outside declared `allowed_outputs` or denied roots. This is not full sandboxing;
it is a visibility and fail-closed layer until agent execution can be moved into
provider-side isolated workspaces.

ClaimVector v1 is allowed only as an advisory language-boundary compiler. It
may derive allowed and forbidden claim language from evidence/admission/
identification inputs, but it must not write the claim registry, certify
scientific truth, approve gates, or turn absence of a violation into support.
Claim-upgrade automation may generate recommendation packets, but the registry
change remains a human-gated authority event.

Paper-readiness automation may generate a report-only packet from the derived
readiness vector, but the required output verdict is `not_asserted`. Human
review remains the only authority for deciding whether a paper package is ready
for submission or release.

Automatic reconcile is deferred until ResultRecord and ResultAdmission are
semantically separated. Machine refresh may update machine facts; it must not
silently overwrite human admission, claim, or release judgments. EvidenceUnit
and ResultAdmission v1 fixtures now enforce this separation mechanically, but
they remain admission-boundary controls rather than claim-support certification.

SQLite journal v1 is allowed only as a disposable derived index over source
files. It may speed up queries and joins, but Git-tracked files remain the
source of truth and the journal must mark `authority=derived_index_only`.

Parser benchmarking is deferred to a larger golden corpus after runtime
enforcement is working. Existing parser fixtures, including false-fulltext
negative cases, remain smoke tests for boundary behavior rather than
parser-quality proof.

## Baseline metrics

The benchmark phase should report at least:

- control_plane_action_ratio;
- fresh_clone_reproduction_rate;
- human_pushes_per_accepted_substantive_artifact;
- false_progress_rate;
- unsupported_claim_escape_rate;
- correct_stop_rate;
- overblocking_rate.

These metrics are the line between a research runtime and a self-maintaining
control plane.

## Non-goals

This freeze does not certify scientific truth, approve any gate, upgrade any
claim, release any project, or prove that AEROS has low control tax. It defines
the baseline from which those questions can be measured.

## vNext reduction baseline

The user-facing default is `research`, with `explore`, `submit`, and
`regulated` as mappings over one immutable kernel. Profiles may reduce process
ceremony but may not weaken these eight invariants:

1. Agents cannot forge or apply human decisions.
2. Credentials, paid access, external writes, and release require authority.
3. Completion requires an observed expected artifact.
4. Admitted Results require data/code/environment/run lineage.
5. Claim producers cannot upgrade their own claim status.
6. Paper numbers bind to Result, Specification, and Exhibit evidence.
7. Claim-bearing citations require locator-backed source evidence.
8. Autonomous loops require time, cost, resource, and repetition limits.

Reversible model work should converge on an isolated candidate-worktree
default. Candidate paper, claim, specification, code, public-source lead, and
nonproduction-probe edits may be broad inside that workspace. Canonical data,
admitted Results, accepted claims, human decisions, submission, and release
remain promotion boundaries. Deterministic local actions and write-producing
provider/LLM callbacks now use isolated candidate worktrees with declared-output
acceptance. This confines project writes; it does not sandbox networks,
credentials, provider billing, or scientific judgment.

Skills are dynamic optional capabilities by default. Only an explicit
`required_skill_classes` contract creates a use-or-waive completion obligation.
Profile simplification is accepted or rejected through paired real-project A/B
evidence under `docs/design/profile_ab_protocol.md`; no rule is retired merely
because the template remains green.
