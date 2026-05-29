# AEROS Runtime (Phase 1)

A thin orchestrator over the AEROS harness. It does **not** contain research
intelligence — that lives in the agent (`claude -p`). The runtime only does:

```
load task contract -> run agent -> run checks -> retry or escalate -> update state
```

## Pieces

| File | Role |
| --- | --- |
| `aeros/cli.py` | entry point: `python3 -m aeros.cli run <contract>` |
| `aeros/runtime/contract.py` | load + validate a task contract (YAML) |
| `aeros/runtime/agent.py` | build prompt, shell out to `claude -p` |
| `aeros/runtime/checks.py` | run checks (prefers `--json`), format agent-actionable feedback |
| `aeros/runtime/state.py` | persist task status + agent-call budget in `aeros_state.yml` |
| `aeros/runtime/kernel.py` | the loop |
| `aeros/hooks/block_raw_write.py` | PreToolUse hook: hard-blocks writes to `data/raw/` |
| `.claude/settings.json` | wires the hook into Claude Code |

## Try it

Dry run (no agent call — prints the exact prompt and planned checks):

```bash
python3 -m aeros.cli run tasks/discovery/D001_literature_search.yml --dry-run
```

Live run (requires an authenticated `claude` CLI on PATH):

```bash
# 1. Fill discovery/01_literature_scope.md with a real topic first.
# 2. Then:
python3 -m aeros.cli run tasks/discovery/D001_literature_search.yml
```

The kernel will: build a prompt from the contract + scope, call the agent,
run `check_literature_registry.py`, and on failure feed the structured check
errors back into a retry (up to `retry_policy.max_retries`). After the budget
or retries are exhausted it writes `decisions/escalations/<task_id>.md` for a
human decision.

## Permission enforcement is real, not advisory

`.claude/settings.json` runs `block_raw_write.py` before every Write/Edit.
A write to `data/raw/` is blocked (exit 2) and the reason is fed back to the
agent. Verify:

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"data/raw/x.csv"}}' \
  | python3 aeros/hooks/block_raw_write.py ; echo "exit=$?"   # -> exit=2
```

## What is NOT done yet (Phase 2+)

- Stage-level runs (`--stage discovery`), gate orchestration (`--until G3`).
- Critic agent and human-gate review memos.
- Provenance capture of model version / prompt for reproducibility.
- `--json` output on checks other than `check_literature_registry.py`.
