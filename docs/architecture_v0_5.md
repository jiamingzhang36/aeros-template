# AEROS v0.5 Architecture: Research Infrastructure, Not Truth Judge

AEROS should not decide what is scientifically true. AEROS decides what is
allowed to be claimed given the artifacts, lineage, analysis path, evidence
admissibility, exception debt, and human decisions on record.

## Core boundary

```text
Execution freedom + integrity enforcement + epistemic compilation + human judgment
```

AEROS is not a central scientific referee. It is a research CI / empirical claim
compiler that prevents process fraud, evidence laundering, illegal state jumps,
and claim inflation.

## Three-layer separation

### Layer A: Execution Layer

The execution layer runs work and records what happened.

Examples:

- run probe
- run backfill
- run specification
- run validation
- write event log
- write artifacts

It must not decide whether the result is scientifically true. It should not
silently mutate claim ceilings, approve gates, or mark scientific adequacy.

### Layer B: Integrity Layer

The integrity layer can hard reject only formal illegality or process fraud.

Examples it may reject:

- receipt laundering
- probe evidence used as final claim support
- action receipt used as empirical evidence
- missing lineage
- deleted or hidden specification runs
- result registered without provenance
- claim edge using inadmissible evidence type
- release attempted without human gate

Examples it must not reject as a truth judgment:

- a theory being uninteresting
- a result being surprising
- a plausible but weak hypothesis
- a design being publishable or not

### Layer C: Epistemic Compiler

The epistemic layer compiles the allowed claim language from the artifact graph.

It outputs:

- claim ceiling
- allowed language set
- forbidden language set
- identification level
- robustness level
- uncertainty and risk flags
- exception debt
- open obligations
- alternative explanations or rebuttals

It does not approve a gate, execute work, or declare the claim true.

## Human Gate

Human gates make judgment calls. They accept or reject risks, decide whether the
bounded language is acceptable, and own accountability. A human gate does not
create empirical evidence.

## From linear FSM to typed artifact graph

The old linear state machine remains useful as a dashboard narrative, but it is
not the real research model.

Wrong mental model:

```text
project.state = validated
```

Correct mental model:

```text
artifact X has validation report Y with provenance Z
claim C is supported by admissible edges from artifacts A, B, C
```

Nodes include:

- DatasetSnapshot
- ProbeRun
- BackfillRun
- ValidationReport
- SpecRun
- Result
- IdentificationReport
- Claim
- ReleaseDecision

Edges include:

- derived_from
- supports
- contradicts
- invalidates
- depends_on
- supersedes
- authorizes
- qualifies

## Claim compiler

Claims are constrained natural language outputs, not just completed schema rows.

```text
ClaimCompiler(evidence_graph, estimand, identification_level, exception_debt)
  -> allowed_language_set
```

Example:

If evidence is exploratory, associational, and lacks identification diagnostics,
AEROS may allow:

- "is associated with"
- "is correlated with"
- "suggests a relationship"

and forbid:

- "caused"
- "effect"
- "impact"
- "led to"

## Design rule

Do not add a new rule layer when the rule can be expressed as one of:

- execution event
- artifact graph edge
- integrity invariant
- admissibility matrix rule
- claim compiler obligation
- human gate decision

## Scope calculus

Evidence may be real while the claim is too broad. Every claim-facing artifact
should carry a scope vector: geography, time period, population, industry, unit,
data source, measurement level, and claim type. The claim compiler checks whether
the claim scope is contained by the evidence scope and emits allowed language,
forbidden language, obligations, and scope-overreach flags. The kernel only
enforces those outputs.

## Exploration without laundering

Discovery-track exploration is allowed and should remain lightweight. It requires
logging and terminal statuses, not full preregistration for every trial.
Confirmatory claims require locked plan/spec/data/estimand artifacts. AEROS
controls what exploration may later claim; it should not block low-risk
exploration at the entrance.

## Human gate classes

Human gates protect high-risk exits rather than every low-risk action. Use
triage gates for system anomaly or exception debt, claim gates for paper/public
claim release, and override gates for explicit departures from default process.


## Paper CI Phase 0: result-born provenance

The wrapper boundary is the estimation call, not the manuscript. Estimation
adapters should introspect fitted model objects and register results in
`evidence/result_registry.csv` before the paper sees the number. This provides a
mechanical birth certificate for result values and extracted spec facts.

Phase 0 guarantees provenance and spec extraction fidelity. It does not certify
that the estimate is correct, that identification is valid, or that a claim is
supported. Claim eligibility derived from the registry is a ceiling input for the
compiler, not a human gate approval.

`aeros paper-ci register-result --record adapter.json` records adapter output.
`aeros paper-ci sync-result-index` projects the result registry into the legacy
`evidence/result_index.csv` view used by downstream number/provenance checks.
