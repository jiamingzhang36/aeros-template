# Human Gate Decision Packet: G3

Generated: 2026-06-01T02:30:39+00:00
Stage: discovery
Current gate: G2
Gate status: approved
Candidate gate: discovery / G3
Earned claim ceiling: measurement

## Recommendation

Approve G3 if the human reviewer accepts the evidence packet.

## Gate Criteria Status

| Gate | Status | Notes |
|---|---|---|
| G0 | PASS | all criteria satisfied |
| G1 | PASS | all criteria satisfied |
| G2 | PASS | all criteria satisfied |
| G3 | PASS | all criteria satisfied |

## Failed / Missing Criteria

None. All criteria through the target gate passed.

## Key Risks for Human Review

- Check whether the evidence actually supports the proposed claim strength.
- Check whether the selected design and data diagnostics match the project intent.
- Check whether any forced overrides, stale tasks, or missing provenance should block approval.

## Human Actions

- Approve: `aeros gate approve G3 --stage discovery --owner <name> --note <why>`
- Block: `aeros gate block G3 --stage discovery --owner <name> --reason <why>`
- Revise: edit the relevant artifacts or task contracts, then rerun `aeros iterate`.
- Stop: record the reason in `decisions/issue_log.csv` or the project log.
