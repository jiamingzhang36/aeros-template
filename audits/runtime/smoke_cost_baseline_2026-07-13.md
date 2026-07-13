# AEROS Smoke Cost Baseline

Date: 2026-07-13
Profile: `smoke`
Result: 18/18 PASS
Observed wall time: 18.75 seconds
Source: `audits/runtime/smoke_cost_baseline_2026-07-13.json`

## Largest observed costs

| Check | Seconds |
|---|---:|
| `check_authority_lifecycle_e2e.py` | 5.5 |
| `check_update_ledger_hash_chain.py` | 2.1 |
| `check_campaign_contract.py` | 2.0 |
| `check_econ_pack.py` | 1.8 |
| `check_authority_evidence.py` | 1.6 |
| `check_research_job_compiler.py` | 1.1 |
| `check_protected_path_hook.py` | 1.1 |

## Decision

This run measures the current cost; it does not remove checks. The profile is
above the stated sub-five-second ambition, but elapsed time alone is not enough
to retire an authority or artifact boundary. A later profile change must pair
cost with real-issue detection, false-positive, and overlap observations.

The first candidate for decomposition is the signed authority lifecycle E2E:
retain a cheap authority-floor invariant in daily smoke and keep key creation,
rotation, revocation, and force-resistance mechanics in full/CI. That change is
not made in this batch because no detection/overlap baseline exists yet.

## Does not prove

- that any check is redundant;
- that the same timings hold on another machine;
- that a faster profile would preserve detection quality;
- scientific validity, claim support, promotion, or release readiness.
