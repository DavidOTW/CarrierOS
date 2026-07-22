# CarrierOS v0.16 Migration Plan

## Scope

PR 1 supplies an additive SQLite schema-13 foundation and a backup-first validation utility. It does not modify production and is not the final managed-PostgreSQL migration. Legacy columns and records remain authoritative and recoverable.

## Safety invariants

- Never run against production without a verified backup, dry run, compatibility review, rollback review, and human approval.
- Default utility mode operates on a temporary backup, not the source database.
- `--apply` and `--rollback` require an explicit `--backup` destination.
- Backup integrity is verified with `PRAGMA quick_check` before migration begins.
- Migration is additive and wrapped in a savepoint.
- Failed validation rolls back the migration transaction.
- Legacy fields are not deleted or rewritten.
- Every migrated row retains its organization ID.

## Schema 12 to 13 mapping

| Legacy source | v0.16 target | Validation |
|---|---|---|
| `drivers` pay columns | `driver_pay_rules` version 1 | One active rule per driver; model/rates preserved |
| `vehicles` | `power_units` | Same organization, unit identity, MPG, financing/insurance/maintenance/fixed costs |
| legacy driver-to-vehicle relationship | `equipment_assignments` | Current assignment created when resolvable |
| load pickup fields | `load_stops` sequence 1 | Stop count and organization match |
| load delivery fields | `load_stops` sequence 2 | Stop count and organization match |
| load driver/vehicle references | `load_assignments` | Tenant ownership validated |
| load revenue | `load_revenue_items` linehaul cents | Sum of cents equals half-up conversion of legacy load revenue |
| load direct costs | `load_expense_items` | Each available category converted independently to cents |
| load status | `loads.status_code` plus `load_status_history` | Canonical enum mapping and append-only initial history |
| protected resource IDs | UUID columns | Non-null/unique after backfill |

Trailer data has no reliable legacy source. The migration creates the table but does not fabricate trailer records. Trailer profiles and assignments remain an explicit setup item.

## Commands

Dry run on a current database copy:

```powershell
python scripts/migrate_v016_foundation.py --database C:\safe\carrieros-copy.db --report C:\safe\v016-dry-run.json
```

Explicit apply to an approved non-production copy:

```powershell
python scripts/migrate_v016_foundation.py --database C:\safe\carrieros-copy.db --apply --backup C:\safe\carrieros-pre-v016.db --report C:\safe\v016-apply.json
```

Rollback rehearsal:

```powershell
python scripts/migrate_v016_foundation.py --database C:\safe\carrieros-copy.db --rollback --backup C:\safe\carrieros-before-rollback.db --report C:\safe\v016-rollback.json
```

## Validation checklist

1. Source backup exists, opens, and passes `quick_check`.
2. Migration result reports schema version 13.
3. Organization, user, driver, vehicle, load, payment, and audit counts are unchanged.
4. Each legacy driver has one version-1 pay rule.
5. Each legacy vehicle has one power-unit profile.
6. Each load has a public UUID, canonical status, two migrated stops where legacy pickup/delivery existed, an assignment where references existed, and normalized money items.
7. Legacy revenue converted with the documented half-up policy equals normalized revenue cents per organization.
8. No normalized child row crosses organization boundaries.
9. Duplicate public UUIDs and idempotency keys are absent.
10. Full regression and migration tests pass on the migrated copy.

The migration utility emits the machine-readable validation object used by `docs/V016_MIGRATION_VALIDATION_REPORT.md`.

## PostgreSQL cutover plan (PR 4)

1. Introduce SQLAlchemy 2.x models and Alembic migrations matching the approved normalized schema.
2. Create managed PostgreSQL development and staging databases; production credentials remain host-managed.
3. Transform a restored SQLite production backup into PostgreSQL in a controlled offline job.
4. Compare per-table counts, per-organization counts, money totals, UUIDs, foreign keys, and representative snapshots.
5. Run tenant, financial, workflow, billing, and backup-restore suites in staging.
6. Rehearse rollback to the pre-cutover SQLite release and database.
7. Schedule a human-approved maintenance window, pause writes, create an off-host backup, rerun the final delta, and switch the connection flag.
8. Keep the prior release/database read-only for the approved rollback window.
9. Do not scale horizontally until transaction/idempotency and locking tests pass.

## Rollback compatibility

Schema-13 rollback removes only new tables/triggers and returns `user_version` to 12. SQLite cannot safely drop additive columns on all supported versions, so public UUID/status/role columns may remain unused. The v0.15 application ignores them. Legacy records and financial values remain intact.

## Approval record required before production

Record backup location/checksum, dry-run report, application commit, migration version, start/end time, validator, reviewer, total/count comparison, known exceptions, rollback owner, and final human approval. No automated agent supplies that approval.
