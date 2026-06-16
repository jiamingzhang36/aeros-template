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
