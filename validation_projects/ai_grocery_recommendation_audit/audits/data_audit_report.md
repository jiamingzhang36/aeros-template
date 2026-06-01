# Data Feasibility Audit Report

## Status

Conditionally pass for G4 smoke execution.

## Evidence Reviewed

- `discovery/data_inventory.csv`
- `discovery/data_diagnostics.yml`
- `discovery/variable_construction.md`
- `docs/data_contract.yml`
- `docs/method_card.md`

## Feasibility Summary

The project has enough located candidate sources to run an offline measurement smoke test and to design the full audit protocol. It does not yet have validated production data for final empirical claims.

## Source Assessment

- Nutrition scoring: plausible through USDA FoodData Central and Open Food Facts, but item matching must be validated.
- Affordability scoring: plausible through USDA Thrifty Food Plan benchmarks and retailer/proxy prices, but local price capture is not validated.
- Household constraints: feasible as pre-registered synthetic personas, not observed households.
- AI outputs: not yet collected as final data; smoke execution should use toy/offline responses only.

## Blockers Before Final Results

1. Approve a prompt grid and persona table.
2. Validate item parsing from AI text to structured grocery baskets.
3. Validate price source rules and terms of service.
4. Record model/provider/time metadata for every recommendation run.
5. Keep all claims at measurement/descriptive level until real outputs and provenance exist.
