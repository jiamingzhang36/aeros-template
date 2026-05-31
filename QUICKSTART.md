# QUICKSTART

1. Read 3 files: `AGENTS.md`, `README.md`, `discovery/AGENTS.md`.
2. Fill `discovery/idea_memo.md` (at least: Working Title, Research Question).
3. Create `discovery/01_literature_scope.md` and set `discovery/literature/search_log.md` with one seed search entry.
4. Run:
   - `make checks`
   - `python3 checks/check_discovery_completeness.py`
5. If checks pass, inspect available contracts with `python3 -m aeros.cli list-tasks` and start with `tasks/discovery/D001a_framing.yml`.
6. Record outputs in `agent_runs/` after each task and run required checks.

When moving to execution:

1. Confirm discovery feasibility with `python3 -m aeros.cli feasibility`.
2. Record human approval with `python3 -m aeros.cli gate approve G3 --stage discovery --owner <name> --note <reason>`.
3. Preview execution with `python3 -m aeros.cli pipeline --stage execution --dry-run`.
4. Run `python3 checks/run_harness_checks.py` before major edits.
