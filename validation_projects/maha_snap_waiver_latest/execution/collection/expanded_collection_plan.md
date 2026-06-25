# Expanded Collection Plan

## Status

This is a design-only plan for an optional G11 expanded-collection phase. It does not collect new AI outputs, does not call any provider, and does not change Paper 1's claim ceiling.

## Purpose

The only defensible expanded-collection use case for this project is auxiliary audit evidence. It may help stress-test whether the codebook, claim boundaries, and document-linked policy coding are understandable to independent systems or reviewers. It cannot replace MG human second-coder reliability and cannot upgrade any claim to causal, behavioral, welfare, or actual SNAP/EBT transaction evidence.

## Research Boundary

The active Paper 1 claims remain:

- `C001`: heterogeneous state-specific policy-rule measurement;
- `C002`: descriptive or associational approval-risk concentration;
- `C003`: ex-ante aggregate NielsenIQ policy-rule exposure for covered approved states;
- `C004`: explicit boundary diagnostics.

Expanded AI outputs may only be used as audit diagnostics for clarity, consistency, and overclaim detection. They must not be treated as independent empirical outcomes.

## Personas

The planned grid uses three reviewer personas:

- `policy_coder`: checks whether the policy-rule taxonomy can be applied consistently from document excerpts.
- `econ_referee`: checks whether claims remain descriptive or associational and do not become causal.
- `replication_auditor`: checks whether result IDs, evidence IDs, provenance, and data boundaries are traceable.

## Prompt Variants

The plan uses four prompt variants:

- `taxonomy_recode`: re-apply the policy-rule codebook to a bounded excerpt or summary.
- `claim_boundary_audit`: classify each claim as measurement, descriptive, associational, causal, or unsupported.
- `replication_trace`: verify whether a claim references a registered result and evidence object.
- `limitation_red_team`: identify overclaims, missing denominators, or data-boundary violations.

## Models and Runs

The grid is intentionally provider-neutral. The placeholder model value is `approved_provider_model_via_T010`. Before collection, a human must approve the actual provider, model, terms, cost limit, privacy boundary, and prompt packet. At least one repetition per persona-variant cell is planned, for twelve rows total.

## Metadata Requirements

If T010 is approved later, each collected row must preserve:

- `prompt_id`;
- persona;
- prompt variant;
- provider and model;
- run index;
- timestamp;
- exact prompt text or prompt template hash;
- source artifact references;
- output text;
- run identifier;
- cost or token metadata if available;
- privacy/data-boundary attestation.

## Exclusion Rules

Do not include restricted NielsenIQ household, purchase, trip, product, UPC-level, or panelist microdata in any prompt. Do not include private credentials, local-only data paths beyond public artifact identifiers, or unpublished personal information. Do not ask the model to infer hidden USDA motives or latent causal effects.

## Claim-Use Rules

Allowed use:

- appendix-level auxiliary validation;
- prompt-grid audit record;
- codebook clarity stress-test;
- overclaim / boundary scan.

Forbidden use:

- replacing MG human second-coder reliability;
- upgrading claims beyond `C001`--`C004`;
- estimating demand, welfare, health, or post-policy effects;
- treating model output as observed policy evidence.

## Risks

The main risks are automation bias, prompt sensitivity, provider/model drift, undocumented terms of service, and leakage of restricted or private information. These risks are why T010 is approval-required and why this plan does not trigger collection automatically.

## Human Approval Requirement

T010 must not run until the user explicitly approves the provider/model/prompt grid and confirms that prompts contain only public or aggregate wrapper material. If no expanded AI-output phase is needed, G11--G13 should be scoped out of the lifecycle rather than forced.
