# Revision Log

Use this file to track template or project-level changes that alter workflow, evidence standards, task contracts, checks, or file structure. Record local date/time with timezone and the commit when available.

## Revisions

| Date/time | Revision ID | Commit | Change type | Files changed | Reason | Checks | Notes |
|---|---|---|---|---|---|---|---|
| 2026-05-28 18:31 +0800 | REV008 | 39ab92c | task structure | `tasks/D*.md`, `README.md` | Renumber discovery tasks sequentially after consolidation | `checks/run_harness_checks.py` pass | Current discovery sequence is D001-D006. |
| 2026-05-28 18:26 +0800 | REV007 | 39aff96 | task structure | `tasks/D002*`, `tasks/D005*`, removed former D003/D006 | Merge overlapping discovery tasks | `checks/run_harness_checks.py` pass | Data scouting absorbed feasibility triage; literature verification absorbed extraction. |
| 2026-05-28 18:21 +0800 | REV006 | a659ff8 | simplification | `data_inventory.csv`, `idea_bank.csv`, checks, tasks | Merge source memo tracing into existing discovery tables | `checks/run_harness_checks.py` pass | Removed separate source memo trace file/check. |
| 2026-05-28 17:09 +0800 | REV005 | 6151190 | data feasibility | `data_inventory.csv`, `feasibility_memo.md`, D002/D003/T002, README | Require skill-assisted data probing before feasibility conclusions | `checks/run_harness_checks.py` pass | Records skills considered, used, blocked, and next probes. |
| 2026-05-28 17:07 +0800 | REV004 | 9ecc9af | data feasibility | `feasibility_memo.md`, `feasibility_matrix.md`, D002/D003/T002, README | Add provisional data feasibility gates | `checks/run_harness_checks.py` pass | Separates source existence from data feasibility and causal readiness. |
| 2026-05-28 16:56 +0800 | REV003 | e333f63 | literature evidence | literature checks, D007, citation audit, extraction template, README | Tighten literature evidence workflow | `checks/run_harness_checks.py` pass | DOI preferred but not required; stable locator and extraction chain required for evidence use. |
| 2026-05-28 15:26 +0800 | REV002 | f45c5af | skill governance | skill menu / related docs | Tier research skills by default use | not recorded | Establishes core/optional/reference skill handling. |
| TBD | REV001 | TBD | project setup | TBD | Initial setup | TBD | Fill this row when instantiating a project from the template. |
