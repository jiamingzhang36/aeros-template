# Hook Templates

This directory contains tool-agnostic examples for enforcing the harness.

Agent systems differ in how they implement hooks and permissions. Treat these files as templates to translate into the local agent runner.

Recommended hook points:

- before file writes
- before shell commands
- after file writes
- after task completion

Recommended blocking rules:

- block writes to `2_execution/data/raw/**`
- ask before writing protected definitions
- block destructive git commands
- require a run report after task completion
- require checks after code, claim, paper, or output changes
