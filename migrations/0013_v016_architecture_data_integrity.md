# Migration 0013: v0.16 architecture and data integrity

Authoritative forward migration: `app.v016_migration.migrate_v016_foundation`.

Authoritative application rollback: `app.v016_migration.rollback_v016_foundation`.

Operator interface: `scripts/migrate_v016_foundation.py`.

The forward migration is Python-backed because it must strictly parse legacy money,
generate nonsequential public UUIDs, map legacy statuses, preserve source snapshots,
and compare record counts and financial totals before committing. A static SQL file
cannot safely perform those validations.

## Dry run

```powershell
python scripts/migrate_v016_foundation.py --database C:\copy\carrieros.db
```

Dry-run is the default. It migrates a temporary verified SQLite backup and does not
change the source database.

## Apply

```powershell
python scripts/migrate_v016_foundation.py `
  --database C:\approved\carrieros.db `
  --apply `
  --backup C:\approved\backups\pre-v016.db `
  --report C:\approved\reports\v016-migration.json
```

The command refuses an in-place apply without an explicit backup destination.

## Roll back

```powershell
python scripts/migrate_v016_foundation.py `
  --database C:\approved\carrieros.db `
  --rollback `
  --backup C:\approved\backups\pre-v016-rollback.db
```

Rollback removes only additive v0.16 tables and triggers and resets SQLite
`user_version` to 12. Additive compatibility columns remain because v0.15 ignores
them; removing them would require rebuilding live legacy tables and would create
more rollback risk. All legacy tables and source values remain authoritative.
