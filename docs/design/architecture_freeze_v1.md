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
- automatic paper-ready judgment;
- automatic claim upgrade;
- automatic release approval.

## Sequencing constraints

ExecutionEnvelope must be real confinement, not a declarative YAML promise. The
first implementation must run in an isolated worktree or equivalent isolated
workspace and must verify that observed writes are a subset of declared writes.

ClaimVector v1 is allowed only as an advisory language-boundary compiler. It
may derive allowed and forbidden claim language from evidence/admission/
identification inputs, but it must not write the claim registry, certify
scientific truth, approve gates, or turn absence of a violation into support.

Automatic reconcile is deferred until ResultRecord and ResultAdmission are
semantically separated. Machine refresh may update machine facts; it must not
silently overwrite human admission, claim, or release judgments. EvidenceUnit
and ResultAdmission v1 fixtures now enforce this separation mechanically, but
they remain admission-boundary controls rather than claim-support certification.

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
