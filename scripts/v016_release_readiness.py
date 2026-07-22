"""Run the non-mutating Phase 4 production release gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.release_readiness import evaluate_release_readiness  # noqa: E402 - repository root bootstrap for direct execution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, help="database path (defaults to CARRIEROS_DB)")
    parser.add_argument("--backup-dir", type=Path, help="backup directory (defaults to CARRIEROS_BACKUP_DIR)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    report = evaluate_release_readiness(database_path=args.database, backup_dir=args.backup_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("CarrierOS production release readiness: " + ("READY" if report["ready"] else "BLOCKED"))
        for check in report["checks"]:
            print(f"[{check['status'].upper()}] {check['name']}: {check['detail']}")
        for warning in report["warnings"]:
            print(f"[WARN] {warning}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
