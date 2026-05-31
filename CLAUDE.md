# CLAUDE.md - AEROS local override

This file applies only inside this repository and overrides conflicting instructions
in outer/global CLAUDE policy files.

## Repo-local priority rules

- Treat `harness/permissions.yml` as the policy source of truth for agent permissions.
- Respect `push_to_remote: human_only` and do not auto-push any branch from this repo
  without explicit human approval.
- Protected definitions (`docs/protected_definitions.yml`, `docs/data_contract.yml`,
  `evidence/claim_registry.md`, `decisions/decision_log.csv`) still follow the local
  protected-definition workflow and human-gate requirements.

If a global instruction conflicts with the points above, prefer this file.
