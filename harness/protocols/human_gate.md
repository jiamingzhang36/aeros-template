# Human Decision Gate

Some decisions must remain human decisions, even when an agent can propose them.

## How Gates Run (Autonomous Mode)

AEROS automates the mechanical layer and reserves the human for irreducible
judgment (the "ironies of automation": gating every step makes the human's job
harder, not easier). The autonomous loop (`aeros run` / pipeline) therefore:

1. **Auto-advances mechanical gates.** A gate whose exit criteria a check can
   adjudicate moves on its own (recorded as `auto_advanced`, never `approved`).
2. **Halts only at human gates.** These are listed in
   `project_manifest.yml` `gate_lifecycle.human_gates` (default `G3, G7, G12,
   G13` — design, claim audit, claim upgrade, release). The `lite` profile uses
   `G3, G7`.
3. **Writes a decision packet** at the halt (`decisions/gates/<gate>_decision_packet.md`):
   what you are approving, the evidence overview, unmet criteria, risks, and
   **excerpts of the judgment artifacts' actual content**. Read the substance —
   a check confirms a section exists, not that it says something; hollow,
   duplicated, or placeholder content is a reason to block even when checks pass.
4. **Writes an approval request** (`decisions/approvals/<gate>.md`) but the agent
   **cannot grant it**.

## Granting a Gate (Trust Anchor)

A gate approval only counts when the approval artifact's last git commit author
is an `approver_identity` (see `harness/permissions.yml` `human_approval`). The
autonomous loop never commits, so it cannot forge a grant. To grant:

```
# (as the human / approver git identity)
git add decisions/approvals/<gate>.md && git commit -m "approve <gate>"
aeros gate approve "<gate>" --stage <stage> --owner <name> --note <why>
```

This is tamper-evident, not tamper-proof, for single-user setups; escalate to
GPG-signed commits for tamper resistance. Set `human_approval.enforcement: off`
to fall back to field-presence-only checks.

## Plan / Apply (proposal deck)

For a richer gate decision, split it into two physical phases (like
`terraform plan` / `apply`):

```
aeros gate plan  "<gate>" --stage <stage>   # agent writes a proposal deck (text only, no execution)
# review/edit decisions/plans/<gate>.md: keep/drop/edit cards; commit it as approver
aeros gate apply "<gate>" --stage <stage>   # a committed, valid deck grants the gate
```

The proposal phase executes nothing and burns no tokens on the real work. Cards
sourced from the anchor/intake are `locked` and may not be dropped; apply rejects
a dropped locked card, a deck with no kept card, or a deck not committed by an
approver identity.

## Human Approval Required

- Change protected definitions.
- Change the preferred specification.
- Change the main sample.
- Change primary outcome or key exposure.
- Promote a robustness result to the main result.
- Strengthen claim type, especially descriptive to causal or historical to forecast.
- Drop observations, geographies, time periods, or sources for substantive reasons.
- Publish, push, release, or share outputs outside the private project.
- Resolve open ambiguities in mechanism-to-task mapping, lead mapping, or evidence sufficiency before accepting completion.
- Ask explicitly when there are multiple reasonable interpretation paths and branch preference is unclear.

## Decision Values

- `accept`
- `accept_with_conditions`
- `revise`
- `reject`
- `defer`

## Required Log Entry

Record decisions in `decisions/decision_log.csv` with:

- date
- task ID
- agent recommendation
- critic verdict
- human decision
- rationale
- follow-up

## Rule

If the task changes the meaning of the empirical claim, the decision must be logged before the change is treated as accepted.
