# AEROS Kernel

The AEROS kernel is an integrity kernel, not a scientific truth judge.

It answers formal legality questions:

- Is this transition formally legal?
- Is this evidence type admissible for this use?
- Is lineage present?
- Is an artifact being laundered into a stronger role than it can support?
- Are required obligations or exception debts visible?

It does **not** answer scientific judgment questions:

- Is this theory correct?
- Is this result ultimately true?
- Is this paper publishable?
- Is this the best explanation?

## Division of labor

```text
Execution Layer     -> runs work and writes events/artifacts
Integrity Kernel    -> rejects process fraud and formal illegality
Epistemic Compiler  -> compiles claim ceiling and allowed language
Human Gate          -> makes judgment and owns accountability
```

## Core objects

- `State`: compatibility narrative states for high-level legality checks
- `Action`: formal transition attempts
- `Evidence`: artifact path, type, intended use, and strength
- `ArtifactNode`: typed artifact in the research graph
- `EvidenceEdge`: typed relationship between artifacts/claims
- `ClaimAdmissibility`: ceiling, obligations, exception debt, and risk flags

## Rule

Events and receipts log what happened. They do not decide whether research state
advanced or whether a claim is allowed. The kernel and claim compiler evaluate
legality and admissibility; human gates make judgment calls.
