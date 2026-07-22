# CarrierOS v0.16 PR 1 Rollback Plan

## Principle

PR 1 is additive and must remain backward-compatible with v0.15. No production deployment is authorized by this pull request. Rollback restores application code first and removes additive schema only when necessary; legacy records are never deleted.

## Precondition

Before any non-test apply:

- identify the exact database path and application commit;
- stop or quiesce writes;
- create a separate verified backup with a non-overwriting filename;
- run `PRAGMA quick_check` on source and backup;
- run the dry-run migration on a backup copy;
- record count and money validation;
- obtain human approval.

## Application rollback

1. Stop incoming writes.
2. Deploy the previously approved v0.15 image/commit.
3. Keep schema-13 additive tables/columns in place initially; v0.15 ignores them.
4. Run health, login, organization isolation, load list, driver balance, payment, and Stripe-entitlement smoke tests.
5. Reopen traffic only after those checks pass.

This is the preferred rollback because it avoids unnecessary database mutation.

## Schema rollback rehearsal

On an approved copy only:

```powershell
python scripts/migrate_v016_foundation.py --database C:\safe\carrieros-copy.db --rollback --backup C:\safe\carrieros-before-rollback.db --report C:\safe\v016-rollback.json
```

The rollback removes v0.16 tables and append-only triggers and sets schema version 12. Additive columns may remain because portable SQLite column removal is unsafe; v0.15 ignores them. If normalized-only writes ever become active in a later PR, this rollback is no longer sufficient and a reverse-transform migration is mandatory.

## Restore from backup

Use backup restoration only if integrity or validation fails and ordinary application rollback cannot recover service:

1. Stop all application instances and background workers.
2. Preserve the failed database separately for investigation.
3. Verify backup checksum and `quick_check`.
4. Restore to a new database path rather than overwriting the only remaining copy.
5. Point the prior approved release to the restored path.
6. Run full smoke and financial spot checks.
7. Record the lost-write window and reconcile Stripe/webhook events before reopening.

## Rollback triggers

- Any failed migration validation or database integrity check.
- Record-count or organization-money mismatch.
- Cross-tenant data visibility.
- Changed legacy financial result without an approved fixture difference.
- Repeated migration/startup failure.
- Audit/snapshot mutation becoming possible.
- Material performance or availability regression.

## Evidence to retain

Application version, schema version, backup path/checksum, migration report, test result, reviewer, approver, start/end time, reason, failed evidence, rollback action, post-rollback checks, and Stripe/event reconciliation.

## PostgreSQL rollback extension

PR 4 must add dual-compatible application releases, write freeze/delta handling, PostgreSQL backup/restore, connection switchback, sequence reconciliation, and a bounded rollback window. This PR does not authorize or perform that cutover.
