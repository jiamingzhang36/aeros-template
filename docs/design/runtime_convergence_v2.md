# AEROS Runtime Convergence v2

## Purpose

This cycle reduces duplicated authority and daily control tax. It does not add
a new research lane, gate, or scientific oracle.

## Authority evidence

`local_authorship` is configured local Git provenance, not proof of a
real-world human. `signed_commit` additionally requires `git verify-commit`.
`external_human_approval` is reserved and fails closed until an independent
verifier exists. `aeros approve` creates a scoped artifact; a plain y/n prompt
does not grant authority.

## Research value

Campaign quantity metrics are bounded by unique evidence units. Decision value
is separately represented by seven research-value transitions. Repeated work
with no verified transition raises `low_decision_value`; novelty alone is not
treated as research value.

## Artifact semantics

Artifact state is the product of `selection_status`, `processing_stage`, and
`admission_status`. Legacy `output_intent` is retained as a compatibility
projection and does not force downstream projects to migrate immediately.

## Compilation

The v1 vertical slice is:

`ResearchJob(data_probe) -> TaskContract -> ActionSpec -> ExecutionEnvelope`.

Each stage may only narrow outputs and authority. Humans declare the research
job; generated control objects are not parallel hand-maintained truth sources.

## Adaptive checks

Observed writes map deterministically to six risk domains. Pre-drive is a small
authority/action compilation gate; post-action checks are selected by changed
paths; full remains CI/nightly/release. Check telemetry fields are specified so
future retirement is evidence-based.

## De-vendor admission rule

Do not flip projects from vendored runtime to package+lock until Authority,
Research Value, artifact semantics, ResearchJob compilation, and adaptive
selection have passed at least one clean real-project rollout. The future
project-local contract is `.aeros/project.yml` plus `aeros.lock`; this document
does not authorize migration yet.

## Vertical proof status

- Signed authority: a temporary SSH signing key produces a signed approval via
  `aeros approve`; Git verifies it and campaign consumption retains the signed
  authority evidence.
- Research value: equal-size campaign windows are tested with and without a
  verified obligation-closing event; quantity-only work trips the breaker.
- ResearchJob: a compiled data probe runs in a detached worktree, reads a real
  CSV, emits a hashed probe report, accepts only the declared output, selects
  the data/sample risk domain, and passes its post-check.
