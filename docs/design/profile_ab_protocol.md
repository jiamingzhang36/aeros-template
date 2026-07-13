# AEROS Research-Profile A/B Protocol

Status: measurement protocol only. It does not select a winning profile or
change runtime authority.

## Question

Does the lower-ceremony `research` profile reduce control tax and human pushes
while preserving the immutable safety outcomes of the current strict baseline?

## Projects

Run paired episodes on:

- CMPD: literature/data/claim integration;
- MAHA: current-status validation and writing consistency;
- one analysis-heavy project with a real specification/result path.

Do not compare unrelated tasks. Pair episodes by project, task type, expected
artifact, and bounded budget. Keep model/provider and input snapshot fixed when
possible.

## Arms

- `strict_baseline`: current regulated behavior.
- `research_candidate`: dynamic optional skills, candidate worktree, adaptive
  artifact checks, and unchanged promotion authority.

## Required observations

For each episode record only observed values:

| Field | Meaning |
|---|---|
| project | Project identifier |
| arm | strict_baseline or research_candidate |
| task_type | Comparable research action |
| expected_artifact | Artifact promised before execution |
| artifact_accepted | Human or deterministic acceptance outcome |
| human_interruptions | Inputs required before acceptance |
| control_seconds | Time spent in checks, approvals, ledgers, and preflight |
| total_seconds | Total episode wall time |
| model_cost | Observed provider cost, or null |
| false_completion_escape | A false completion reached acceptance |
| unsupported_claim_escape | Unsupported claim reached admission |
| citation_mismatch_escape | Citation mismatch escaped the relevant check |
| unauthorized_side_effect | Undeclared external or workspace effect occurred |
| human_corrections | Substantive corrections before acceptance |

## Derived metrics

```text
useful_drive_rate = accepted artifacts / completed drive episodes
control_tax = control_seconds / total_seconds
human_interruptions_per_accepted_artifact
time_to_first_evidence
time_to_first_result
time_to_first_paper_fix
```

Missing observations remain null; they are not converted to zero. Safety
escapes are reported as counts and inspected individually rather than averaged
away.

## Decision rule

Do not retire an existing rule from template evidence alone. A rule becomes a
retirement candidate only when paired real-project evidence shows lower control
tax or fewer human interruptions without a higher safety-escape count. Human
review decides retirement; this protocol never deletes checks automatically.

## Candidate post-action contract

The candidate arm is not allowed to report PASS from selected checks alone.
It must provide the observed action exit code, observed write paths plus
material dependency paths, and at least one non-empty expected output inside
the candidate worktree:

    aeros checks select \
      --changed PATH \
      --action-exit N \
      --expected-output PATH

A missing/nonzero action exit or missing/empty/out-of-worktree expected output
fails before scientific checks are interpreted. Analysis/figure outputs select
result and provenance checks. Manuscript work that depends on registered
results must declare that dependency so those checks also run. This contract
does not prove that an output is fresh or scientifically valid.

## Boundaries

This protocol does not prove scientific quality, model superiority, profile
causality, or generalization beyond the paired episodes.
