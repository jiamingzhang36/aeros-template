# ActionSpec Inversion Plan

Status: Phase 2 producer inversion implemented; compatibility inference retained for old artifacts only.

## Problem

`aeros next` now emits a typed `ActionSpec`. Phase 1 derived that spec from the
legacy rendered command string. Phase 2 moves producer branches to declare
ActionSpec semantics directly. Compatibility inference remains only for older
artifacts or external callers that construct a bare `NextAction`.

The resting state must not be two string parsers:

- `action_spec_from_next()` inferring kind/effect from command text.
- `_command_args()` allowlisting command text before execution.

## Phase 1: derived shim

Implemented and superseded for internal producers:

- Render `ActionSpec` in `aeros next`.
- Record `ActionSpec` in `aeros run --until`.
- Validate spec invariants in `check_next_action.py` and `check_action_spec.py`.
- Stop on blockers, placeholders, human-decision effects, and invalid specs.

Boundary:

- The command string still exists for compatibility.
- `ActionSpec.kind` can still be inferred by `action_spec_from_next()` for old
  callers only, and such specs carry `producer_mode: inferred_compat`.

## Phase 2: inverted producer

Implemented:

- Each `next_action` branch constructs an `ActionSpec` directly where
  `kind`, `effect_class`, `capabilities`, preconditions, and budgets are known.
- The command string is rendered from the `ActionSpec`, not the other way around.
- `check_next_action.py` requires computed next actions to have
  `producer_mode: declared`.
- `_infer_kind()` is retained only for backward compatibility and marks specs as
  `producer_mode: inferred_compat`.

Remaining follow-up:

- Shrink `_command_args()` further into a final argv renderer/guard.
- Dispatch real executions on `ActionSpec.kind` and `effect_class` instead of
  command parsing when enough downstream projects have synced.

## Non-goals

- Do not migrate state to SQLite in this phase.
- Do not remove existing CLI commands until downstream projects have synced.
- Do not let ActionSpec approve gates, upgrade claims, certify identification,
  or bypass human authority.

## Acceptance checks

- `check_action_spec.py` has direct cases for each effect class.
- `check_next_action.py` fails if controller records omit ActionSpec.
- No new `next_action` branch may introduce a free-form command without a
  directly declared ActionSpec.
