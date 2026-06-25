# Replication README

This AEROS wrapper is a smoke-safe replication scaffold for the canonical MAHA SNAP waiver project. It registers public-document and aggregate-result artifacts without copying raw USDA/state source files or restricted NielsenIQ Consumer Panel microdata into the wrapper.

## Scope

The wrapper supports replication checks for four registered result objects:

- `R001`: policy-rule vector and design taxonomy.
- `R002`: approval-risk concentration diagnostics.
- `R003`: NielsenIQ ex-ante policy-rule exposure aggregates.
- `R004`: boundary and feasibility diagnostics.

The claim ceiling is measurement, descriptive association, or boundary documentation. This package does not identify post-policy consumption effects, demand elasticities, welfare effects, or causal approval effects.

## Quick Start

Run the smoke pipeline from this directory:

```bash
python3 code/99_make_all.py --mode smoke
```

Or use the Makefile:

```bash
make smoke
make check
```

The smoke pipeline verifies registered inputs and confirms that no restricted microdata export is declared. It writes `outputs/logs/pipeline_smoke_report.json`.

## Controlled Data Boundary

Raw NielsenIQ purchase, trip, panelist, and product files are not included. Any rerun that requires raw household or purchase rows must be executed in the controlled data environment described by the canonical MAHA repository. This wrapper only exposes aggregate outputs and provenance records.

The Nielsen result object (`R003`) is therefore reproducible in two tiers:

- Public tier: verify the registered aggregate artifact, provenance metadata, and claim boundary.
- Controlled tier: rerun raw NielsenIQ ingestion, classification, policy-rule exposure, and uncertainty routines inside the approved local data environment.

## Core Checks

```bash
python3 checks/check_replication_package.py
python3 checks/check_pipeline_runs.py
python3 checks/check_output_reproducibility.py
python3 checks/check_provenance.py
python3 checks/check_artifact_manifest.py
```

## Release Blockers

Before public release, confirm that:

- no raw NielsenIQ household, trip, purchase, product, or UPC-level restricted files are exported;
- all publication-facing figures/tables point to the canonical MAHA outputs;
- the final manuscript continues to state that SNAP/EBT transactions are not observed;
- Hawaii is excluded from Nielsen approved-state exposure claims unless covered by a later data source;
- target implementation dates are not described as observed implementation dates.
