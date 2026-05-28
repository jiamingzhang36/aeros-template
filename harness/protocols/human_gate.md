# Human Decision Gate

Some decisions must remain human decisions, even when an agent can propose them.

## Human Approval Required

- Change protected definitions.
- Change the preferred specification.
- Change the main sample.
- Change primary outcome or key exposure.
- Promote a robustness result to the main result.
- Strengthen claim type, especially descriptive to causal or historical to forecast.
- Drop observations, geographies, time periods, or sources for substantive reasons.
- Publish, push, release, or share outputs outside the private project.

## Decision Values

- `accept`
- `accept_with_conditions`
- `revise`
- `reject`
- `defer`

## Required Log Entry

Record decisions in `decisions/decision_log.md` with:

- date
- task ID
- agent recommendation
- critic verdict
- human decision
- rationale
- follow-up

## Rule

If the task changes the meaning of the empirical claim, the decision must be logged before the change is treated as accepted.
