# Replication Package Report

## Verdict

The AEROS wrapper is replication-check ready for smoke-safe verification of registered outputs, provenance metadata, and claim ceilings. It is not a public raw-data replication package for NielsenIQ microdata.

## Inventory

- Master entry point: `code/99_make_all.py`.
- Pipeline manifest: `execution/pipeline_manifest.yml`.
- Registered results: `evidence/result_index.csv`.
- Provenance records: `outputs/.provenance/R001.json` through `outputs/.provenance/R004.json`.
- Draft handoff: `paper/draft.md`.
- Data access note: `data/README_data.md`.
- Environment scaffolding: `requirements.txt` and `environment.yml`.
- Replication entry instructions: `README_replication.md` and `Makefile`.

## Reproducibility Tiers

### Tier 1: Public Wrapper Checks

The wrapper can verify the pipeline entry point, result index, provenance linkage, and claim boundaries without external data. This tier is appropriate for AEROS gate checks and for demonstrating that the project has an auditable artifact chain.

### Tier 2: Controlled Nielsen Reruns

Raw NielsenIQ purchase, trip, panelist, and product files are restricted. Full reruns of raw ingestion, household-month construction, household bootstrap uncertainty intervals, and any purchase-level diagnostics require the controlled local data environment. These restricted reruns must not export household or purchase rows into the wrapper.

## Registered Outputs

- `R001` supports policy-rule measurement and design heterogeneity claims.
- `R002` supports approval-risk concentration claims as descriptive association only.
- `R003` supports ex-ante policy-rule exposure claims using aggregate Nielsen-derived outputs only.
- `R004` supports boundary and feasibility claims, including SNAP/EBT non-observation and target implementation-date limits.

## Release Blockers

- A public release cannot include restricted NielsenIQ household, UPC, purchase, trip, product, or raw panelist files.
- The final paper must preserve the distinction between low-income/SNAP-eligible proxy households and observed SNAP/EBT transactions.
- The final paper must preserve the 21-of-22 approved-state Nielsen coverage boundary unless Hawaii is added by a later data source.
- The final paper must not interpret target implementation dates as observed implementation dates.
- Any claim upgrade beyond descriptive association or measurement requires new evidence and gate review.

## Checks to Run

```bash
python3 checks/check_replication_package.py
python3 checks/check_pipeline_runs.py
python3 checks/check_output_reproducibility.py
python3 checks/check_provenance.py
python3 checks/check_artifact_manifest.py
```

## Protected Definitions

No protected definitions were changed. The wrapper remains private-by-default and aggregate-only for restricted-data-derived outputs.
