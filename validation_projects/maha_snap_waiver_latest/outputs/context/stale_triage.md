# STALE_TRIAGE

frontier_gate: G11
stage: execution
lane: project
items: 2

## T004_main_execution
bucket: rerun_required
impact_level: high
impact_scope: specific_claims
stage: execution
lane: analysis
gate: G4
stale_reason: output_changed
command: python3 -m aeros.cli iterate --stage execution --lane analysis --to-next-gate --dry-run
volatile_only_outputs: False
frontier_connected: True
claim_bound: True
impacted_claims: C001, C002, C003, C004
downstream_frontier_tasks: T008_paper_package_draft, T009_expanded_collection_design, T010_expanded_ai_output_collection, T011_expanded_result_validation, claim_bound_output
impact_propagated_from: none
rationale: Stale item remains visible because output changed or frontier/claim irrelevance cannot be proven. Preview only. Specific claim-bound/result-bound path detected; human review may be needed if checks fail.

## T004b_robustness_plan
bucket: revalidate_free
impact_level: medium
impact_scope: none
stage: execution
lane: analysis
gate: G5
stale_reason: dependency_output_changed
command: python3 -m aeros.cli recover T004b_robustness_plan --check
volatile_only_outputs: False
frontier_connected: True
claim_bound: False
impacted_claims: none
downstream_frontier_tasks: T008_paper_package_draft, T009_expanded_collection_design, T010_expanded_ai_output_collection, T011_expanded_result_validation
impact_propagated_from: none
rationale: Allowed-output fingerprint is unchanged; refresh via checks before spending provider/API budget.

does_not_prove: checks pass; rerun necessity beyond deterministic dependencies; scientific validity; claim support; gate approval
This is deterministic triage only; it does not run agents, refresh fingerprints, alter state, or adjudicate claims.