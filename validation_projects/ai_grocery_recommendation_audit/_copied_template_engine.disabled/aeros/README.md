# AEROS Runtime (Phase 1)

AEROS is a **tool** (`aeros`) that runs empirical-research task contracts
through an agent under mechanical checks and permission hooks. The surrounding
directory tree (`discovery/`, `docs/`, `evidence/`, `checks/`, ...) is the
**scaffold** the tool operates on — not something you maintain by hand.

The runtime contains no research intelligence — that lives in the agent
(`claude -p`). It only does:

```
load task contract -> run agent -> run checks -> retry or escalate -> update state
```

## Install

```bash
python3 -m pip install -e .   # provides the `aeros` command
```

## Pieces

| File | Role |
| --- | --- |
| `aeros/cli.py` | entry point: `aeros <command>` or `python3 -m aeros.cli <command>` |
| `aeros/runtime/contract.py` | load + validate a task contract (YAML) |
| `aeros/runtime/agent.py` | build prompt, shell out to `claude -p` |
| `aeros/runtime/checks.py` | run checks (prefers `--json`), format agent-actionable feedback |
| `aeros/runtime/state.py` | persist task status + agent-call budget in `aeros_state.yml` |
| `aeros/runtime/kernel.py` | the loop |
| `aeros/hooks/block_raw_write.py` | PreToolUse hook: hard-blocks writes to `data/raw/` |
| `.claude/settings.json` | wires the hook into Claude Code |

## Commands

```bash
aeros list-tasks                 # list .yml task contracts in the project
aeros status                     # gate, per-task status, agent-call budget
aeros gate status                # current human gate state
aeros gate approve G3 --stage discovery --owner <name> --note <why>
aeros pipeline --stage discovery # run a stage in dependency order
aeros check   <contract.yml>     # run a contract's checks, no agent call
aeros run     <contract.yml>     # the full loop: agent -> checks -> retry/escalate
aeros run     <contract.yml> --dry-run   # print prompt + planned checks only
aeros init    <path>             # create a minimal project scaffold
```

(Before install, `python3 -m aeros.cli <command>` is identical.)

## Try it

Dry run (no agent call — prints the exact prompt and planned checks):

```bash
aeros run tasks/discovery/D001a_framing.yml --dry-run
```

Live run (requires an authenticated `claude` CLI on PATH):

```bash
# 1. Fill discovery/01_literature_scope.md with a real topic first.
# 2. Then:
aeros run tasks/discovery/D001a_framing.yml
```

The kernel will: build a prompt from the contract + inputs, call the agent
or deterministic command, run the contract's checks, and feed structured
failures back into a retry when allowed. After the budget or retries are
exhausted it writes `decisions/escalations/<task_id>.md` for a human decision.

## Permission enforcement is real, not advisory

`.claude/settings.json` runs `block_raw_write.py` before every Write/Edit.
A write to `data/raw/` is blocked (exit 2) and the reason is fed back to the
agent. Verify:

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"data/raw/x.csv"}}' \
  | python3 aeros/hooks/block_raw_write.py ; echo "exit=$?"   # -> exit=2
```

## What is NOT done yet (Phase 2+)

- Critic agent persona orchestration beyond task contracts and reports.
- Full JSON output for every individual check script, not only the harness summary.
- A polished separation between reusable runtime, generic scaffold, and project instance.
