# Validation Projects

This directory contains instantiated projects used to pressure-test AEROS automation.

**These are frozen point-in-time snapshots, not canonical template usage.** Each was
run to validate a specific capability at the time, and its internal config
(`project_manifest.yml`, `harness/permissions.yml`, vendored `checks/`) may lag the
current root template — e.g. it may predate gate tiering, profiles, or the human-gate
trust anchor. They are intentionally **not** kept in sync with template changes; doing
so would be a maintenance treadmill and would destroy their value as records of what the
template looked like when each project ran.

For canonical, up-to-date usage, read the repository root: `README.md`,
`project_manifest.yml`, and `harness/protocols/human_gate.md`.

The repository root is the reusable empty template. Do not copy validation project data,
run reports, paper drafts, outputs, or gate state back into the root template unless they
are intentionally converted into generic examples.
