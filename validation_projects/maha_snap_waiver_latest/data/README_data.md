# Data Access Notes

This wrapper intentionally contains no raw source data.

## Public Policy Data

The policy-rule, approval-risk, and boundary diagnostics are derived from the canonical MAHA repository's USDA/FNS and state-document tracking files. The wrapper records only result artifacts and provenance metadata.

## Restricted NielsenIQ Data

NielsenIQ Consumer Panel microdata are restricted and are not stored in this wrapper. Household, trip, purchase, product, UPC-level, and payment-row files must not be exported here.

The wrapper may contain or register aggregate Nielsen-derived artifacts only when they do not expose household-level, purchase-level, or restricted microdata. Any full rerun of raw Nielsen ingestion or household-cluster bootstrap uncertainty intervals requires the controlled local Nielsen data path documented in the canonical MAHA project.

## Current Data Tiers

- Public/aggregate verification: supported by `evidence/result_index.csv`, `outputs/model_outputs/`, and `outputs/.provenance/`.
- Controlled-data rerun: requires local restricted data access and is outside this wrapper's public replication tier.
