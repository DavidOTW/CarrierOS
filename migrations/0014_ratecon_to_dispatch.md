# Migration 0014 — RateCon to Dispatch

Additive SQLite development migration implemented by `app.phase2_migration`.

Adds private-document metadata, immutable RateCon extraction records, evidence-bearing
fields, tenant-scoped match candidates, classified differences, and dispatch approvals.
No legacy table or column is removed. Rollback drops only the Phase 2 tables and leaves
the Phase 1 normalized load, assignment, stop, and financial snapshot foundation intact.

Production promotion remains blocked until private encrypted object storage and malware
scanning are configured, the migration is run against a backup copy, and a human approves
the compatibility and rollback evidence.
