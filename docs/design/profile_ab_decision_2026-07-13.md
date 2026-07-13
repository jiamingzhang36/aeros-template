# Research Profile Paired A/B Decision - 2026-07-13

## Evidence reviewed

Three paired real-project episodes were run from identical per-project commits:

- CMPD citation/paper-binding preflight: candidate reduced control time from
  123 seconds to 2 seconds without changing the expected artifact, but strict
  still exposed fresh-clone/release integrity debt.
- MAHA current-status/writing audit: candidate reduced control time from
  32 seconds to 1 second but missed six registered-result provenance hash
  mismatches.
- VLM D575 transform diagnostic: candidate reduced control time from 76 seconds
  to 1 second, selected only generic ActionSpec/preflight checks for
  outputs/analysis and outputs/figures, and remained green during an initial
  action failure caused by a missing runtime dependency.

## Decision

No existing invariant or full-profile rule is retired.

The candidate profile may be used as a reversible preflight only when:

1. the action exit code is observed and zero;
2. at least one declared expected artifact is non-empty inside the candidate
   worktree;
3. observed writes and material dependency paths select relevant checks;
4. promotion, claim, approval, release, and canonical data authority remain
   unchanged.

Analysis and figure outputs now select analysis, result-registry,
reproducibility, and provenance checks. Manuscript paths now select
result/provenance checks in addition to citation and number binding checks.

Strict/full remains mandatory for promotion, release, fresh-clone validation,
and unresolved provenance or project-migration debt.

## What this does not prove

This decision does not prove scientific validity, that adaptive selection is
complete for every project layout, that non-empty outputs are fresh, or that a
candidate profile may approve claims, gates, or release.
