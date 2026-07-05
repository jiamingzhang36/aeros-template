# R003 NielsenIQ Ex-Ante Exposure Boundary

This execution-lock result records that the NielsenIQ module is framed as ex-ante policy-rule microsimulation using 2022-2024 pre-policy aggregate exposure outputs.

The target estimand is the share of NielsenIQ-observed low-income-proxy food and beverage spending that would fall inside each state's policy-rule basket, with strict/broad mappings used to handle category ambiguity.

Primary supporting artifacts:

- `docs/data_contract.yml`
- `discovery/variable_construction.md`
- `audits/data_audit_report.md`
- `execution/protocol/main_execution_protocol.md`

Boundary: this is not actual SNAP participation, not EBT transaction exposure, not post-policy consumption reduction, not demand elasticity, and not welfare incidence.
