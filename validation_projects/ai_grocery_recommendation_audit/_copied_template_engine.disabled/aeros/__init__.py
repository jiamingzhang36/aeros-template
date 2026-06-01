"""AEROS runtime: a thin orchestrator over the AEROS template harness.

The intelligence lives in the agent (Claude Code, driven via `claude -p`).
The constraints live in task contracts + checks + permission hooks.
This package only does: load contract -> run agent -> run checks ->
retry or escalate -> update state.
"""

__version__ = "0.0.1"
