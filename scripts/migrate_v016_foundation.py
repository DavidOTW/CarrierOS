from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.v016_migration import (  # noqa: E402 - repository root bootstrap for direct execution
    V016_SCHEMA_VERSION,
    migrate_v016_foundation,
    rollback_v016_foundation,
)


def _connection(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _backup(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing backup: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source, timeout=30) as source_conn:
        with sqlite3.connect(destination, timeout=30) as destination_conn:
            source_conn.backup(destination_conn)
    with sqlite3.connect(destination, timeout=30) as verification:
        result = verification.execute("PRAGMA quick_check").fetchone()
        if not result or result[0] != "ok":
            destination.unlink(missing_ok=True)
            raise RuntimeError("Backup integrity verification failed")


def _report(path: Path, *, mode: str, validation: dict | None) -> dict:
    with _connection(path) as conn:
        integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    return {
        "database": str(path.resolve()),
        "mode": mode,
        "schema_version": version,
        "expected_schema_version": V016_SCHEMA_VERSION if mode != "rollback" else 12,
        "integrity_check": integrity,
        "validation": validation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run, apply, or roll back the additive CarrierOS v0.16 foundation migration."
    )
    parser.add_argument("--database", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    source = args.database.resolve()
    if not source.is_file():
        parser.error(f"database does not exist: {source}")
    if (args.apply or args.rollback) and not args.backup:
        parser.error("--backup is required for --apply and --rollback")

    if args.apply or args.rollback:
        target = source
        backup = args.backup.resolve()
        if backup == source:
            parser.error("backup path must differ from the source database")
        _backup(source, backup)
        mode_name = "rollback" if args.rollback else "apply"
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="carrieros-v016-")
        target = Path(temp_dir.name) / source.name
        _backup(source, target)
        mode_name = "dry-run"

    validation = None
    with _connection(target) as conn:
        if args.rollback:
            rollback_v016_foundation(conn)
        else:
            validation = migrate_v016_foundation(conn).to_dict()
        conn.commit()
    payload = _report(target, mode=mode_name, validation=validation)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    if not (args.apply or args.rollback):
        temp_dir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
