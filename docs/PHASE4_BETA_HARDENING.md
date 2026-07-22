# Phase 4 — Production beta hardening (first slice)

Phase 3 is deployed. Phase 4 starts with a release-readiness gate that makes
the production controls and backup evidence explicit before a human approves a
promotion.

## Readiness command

Run the check from the repository root after loading the target environment:

```powershell
python scripts/v016_release_readiness.py --json
```

The same gate is available to uptime and deployment monitors at
`GET /health/ready`. It returns `200` only when ready and `503` when blocked,
with check names and safe remediation messages but no secret values. Render
continues to use `/health` for process health; `/health/ready` is the stricter
promotion signal.

The command is non-mutating with respect to the application data. It never
prints secret values, creates a retained backup, or changes a source database;
it uses a temporary restore workspace that is removed before the command
returns. It checks:

- production mode, a long session secret, and an HTTPS canonical URL;
- live Stripe secret/webhook configuration and every subscription price ID;
- an absolute private document path with encryption-at-rest enabled;
- a managed malware scanner (manual and mock-clean modes are intentionally
  blocked for production);
- SQLite integrity and schema version 15 or newer; and
- the newest retained `carrieros-*.db` backup with the same integrity/schema
  checks and a temporary SQLite restore rehearsal.

The result is `READY` only when every check passes. A `READY` result is
evidence for review, not an automatic authorization to deploy. The operator
must still review the migration, backup/restore rehearsal, billing smoke test,
tenant isolation checks, and rollback plan before promotion.

## Scope of this Phase 4 slice

This change does not claim that PostgreSQL, Alembic, MFA, object-storage
encryption, background workers, observability, or a full staging gate are
finished. Those remain the next Phase 4 work items. The readiness gate makes
those future controls visible while preventing a test Stripe key, manual
malware fallback, or unverified database from being mistaken for a launch
approval.
