# Expanded Collection Design Report

## Verdict

The optional expanded-collection phase is designed but not executed. The plan is suitable only for auxiliary audit diagnostics and must not be used to upgrade Paper 1 claims.

## Design Summary

The planned prompt grid contains twelve rows: three personas by four prompt variants. It is provider-neutral until T010 receives explicit human approval. The planned personas are `policy_coder`, `econ_referee`, and `replication_auditor`. The planned prompt variants are `taxonomy_recode`, `claim_boundary_audit`, `replication_trace`, and `limitation_red_team`.

## Data Boundary

The expanded collection must use public or aggregate wrapper artifacts only. Restricted NielsenIQ household, trip, purchase, product, UPC-level, and panelist microdata are excluded from prompts and outputs.

## Claim Boundary

The planned collection cannot replace MG human second-coder reliability. It cannot identify causal policy effects, demand elasticities, welfare effects, health effects, actual SNAP/EBT transactions, or post-policy purchase responses.

## Next Decision

T010 should remain blocked unless the user explicitly approves an expanded AI-output collection run. If no expanded AI-output phase is needed, the lifecycle should be scoped to end at G10 or the G11--G13 contracts should be removed rather than forced.
