from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from .calculations import normalized_pay_model
from .load_states import normalize_state
from .money import (
    MoneyInputError,
    money_to_cents,
    percentage_to_basis_points,
    rate_to_micros,
)


V016_SCHEMA_VERSION = 13

V016_SCHEMA = """
CREATE TABLE IF NOT EXISTS driver_pay_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    effective_date TEXT NOT NULL,
    end_date TEXT,
    version INTEGER NOT NULL,
    pay_model TEXT NOT NULL,
    percentage_basis_points INTEGER NOT NULL DEFAULT 0,
    flat_rate_cents INTEGER NOT NULL DEFAULT 0,
    loaded_mile_rate_micros INTEGER NOT NULL DEFAULT 0,
    total_mile_rate_micros INTEGER NOT NULL DEFAULT 0,
    day_rate_cents INTEGER NOT NULL DEFAULT 0,
    included_revenue_json TEXT NOT NULL DEFAULT '[]',
    included_expense_json TEXT NOT NULL DEFAULT '[]',
    stop_pay_cents INTEGER NOT NULL DEFAULT 0,
    detention_split_basis_points INTEGER NOT NULL DEFAULT 0,
    layover_pay_cents INTEGER NOT NULL DEFAULT 0,
    tonu_pay_cents INTEGER NOT NULL DEFAULT 0,
    bonus_cents INTEGER NOT NULL DEFAULT 0,
    advance_cents INTEGER NOT NULL DEFAULT 0,
    deduction_cents INTEGER NOT NULL DEFAULT 0,
    payroll_burden_applies INTEGER NOT NULL DEFAULT 0,
    approval_status TEXT NOT NULL DEFAULT 'DRAFT',
    approved_by INTEGER,
    approved_at TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    legacy_snapshot_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (driver_id, version),
    CHECK (approval_status IN ('DRAFT','APPROVED','RETIRED')),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS power_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    legacy_vehicle_id INTEGER,
    public_identifier TEXT NOT NULL,
    company_unit_number TEXT NOT NULL,
    protected_vin TEXT,
    equipment_type TEXT NOT NULL DEFAULT 'Truck',
    gvwr_lbs INTEGER,
    mpg_micros INTEGER NOT NULL DEFAULT 10000000,
    fuel_type TEXT NOT NULL DEFAULT 'diesel',
    financing_cents INTEGER NOT NULL DEFAULT 0,
    insurance_cents INTEGER NOT NULL DEFAULT 0,
    maintenance_reserve_micros INTEGER NOT NULL DEFAULT 0,
    tire_reserve_micros INTEGER NOT NULL DEFAULT 0,
    fixed_monthly_cost_cents INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    legacy_snapshot_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (organization_id, company_unit_number),
    UNIQUE (legacy_vehicle_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (legacy_vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS trailers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    unit_number TEXT NOT NULL,
    trailer_type TEXT NOT NULL,
    gvwr_lbs INTEGER,
    empty_weight_lbs INTEGER,
    dimensions TEXT,
    financing_cents INTEGER NOT NULL DEFAULT 0,
    insurance_cents INTEGER NOT NULL DEFAULT 0,
    maintenance_reserve_micros INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (organization_id, unit_number),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS equipment_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    power_unit_id INTEGER NOT NULL,
    trailer_id INTEGER,
    start_at TEXT NOT NULL,
    end_at TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    approved_by INTEGER,
    approved_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
    FOREIGN KEY (power_unit_id) REFERENCES power_units(id) ON DELETE CASCADE,
    FOREIGN KEY (trailer_id) REFERENCES trailers(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS load_stops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    stop_type TEXT NOT NULL,
    facility_name TEXT,
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    latitude TEXT,
    longitude TEXT,
    iana_timezone TEXT,
    appointment_local_start TEXT,
    appointment_local_end TEXT,
    appointment_utc_start TEXT,
    appointment_utc_end TEXT,
    contact_name TEXT,
    contact_phone TEXT,
    confirmation_number TEXT,
    instructions TEXT,
    arrival_at TEXT,
    departure_at TEXT,
    detention_eligible INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (load_id, sequence_number),
    CHECK (stop_type IN ('PICKUP','DELIVERY','INTERMEDIATE')),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS load_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    driver_id INTEGER,
    power_unit_id INTEGER,
    trailer_id INTEGER,
    assignment_stage TEXT NOT NULL,
    provisional INTEGER NOT NULL DEFAULT 1,
    deadhead_origin TEXT,
    deadhead_miles_micros INTEGER NOT NULL DEFAULT 0,
    route_source TEXT NOT NULL DEFAULT 'manual',
    approved_by INTEGER,
    approved_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    UNIQUE (organization_id, public_uuid),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
    FOREIGN KEY (power_unit_id) REFERENCES power_units(id) ON DELETE SET NULL,
    FOREIGN KEY (trailer_id) REFERENCES trailers(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS load_revenue_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount_cents INTEGER NOT NULL,
    stage TEXT NOT NULL DEFAULT 'BOOKED',
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (load_id, category, stage, source),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS load_expense_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount_cents INTEGER NOT NULL,
    stage TEXT NOT NULL DEFAULT 'BOOKED',
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (load_id, category, stage, source),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS load_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    prior_status TEXT,
    new_status TEXT NOT NULL,
    changed_by INTEGER,
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    idempotency_key TEXT NOT NULL,
    reason TEXT,
    UNIQUE (organization_id, idempotency_key),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS load_financial_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_uuid TEXT NOT NULL,
    organization_id INTEGER NOT NULL,
    load_id INTEGER NOT NULL,
    stage TEXT NOT NULL,
    revision INTEGER NOT NULL,
    calculation_version TEXT NOT NULL,
    input_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, public_uuid),
    UNIQUE (load_id, stage, revision),
    CHECK (stage IN ('QUOTE','BOOKED','RATECON_CONFIRMED','ACTUAL')),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS v016_migration_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_key TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    validation_json TEXT,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pay_rules_org_driver_effective
ON driver_pay_rules(organization_id, driver_id, effective_date, end_date);
CREATE INDEX IF NOT EXISTS idx_power_units_org_active
ON power_units(organization_id, active, company_unit_number);
CREATE INDEX IF NOT EXISTS idx_trailers_org_active
ON trailers(organization_id, active, unit_number);
CREATE INDEX IF NOT EXISTS idx_equipment_assignments_org_driver
ON equipment_assignments(organization_id, driver_id, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_load_stops_org_load
ON load_stops(organization_id, load_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_load_assignments_org_load
ON load_assignments(organization_id, load_id, created_at);
CREATE INDEX IF NOT EXISTS idx_load_revenue_org_load
ON load_revenue_items(organization_id, load_id, stage);
CREATE INDEX IF NOT EXISTS idx_load_expense_org_load
ON load_expense_items(organization_id, load_id, stage);
CREATE INDEX IF NOT EXISTS idx_load_status_org_load
ON load_status_history(organization_id, load_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_load_snapshots_org_load
ON load_financial_snapshots(organization_id, load_id, stage, revision);

CREATE TRIGGER IF NOT EXISTS load_financial_snapshots_no_update
BEFORE UPDATE ON load_financial_snapshots
BEGIN
    SELECT RAISE(ABORT, 'load financial snapshots are immutable');
END;

CREATE TRIGGER IF NOT EXISTS load_financial_snapshots_no_delete
BEFORE DELETE ON load_financial_snapshots
BEGIN
    SELECT RAISE(ABORT, 'load financial snapshots are immutable');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are immutable');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are immutable');
END;

PRAGMA user_version = 13;
"""


V016_COLUMN_MIGRATIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "users": (("role", "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'read_only'"),),
    "drivers": (("public_uuid", "ALTER TABLE drivers ADD COLUMN public_uuid TEXT"),),
    "vehicles": (("public_uuid", "ALTER TABLE vehicles ADD COLUMN public_uuid TEXT"),),
    "loads": (
        ("public_uuid", "ALTER TABLE loads ADD COLUMN public_uuid TEXT"),
        ("status_code", "ALTER TABLE loads ADD COLUMN status_code TEXT"),
        ("updated_at", "ALTER TABLE loads ADD COLUMN updated_at TEXT"),
    ),
    "load_opportunities": (
        ("public_uuid", "ALTER TABLE load_opportunities ADD COLUMN public_uuid TEXT"),
    ),
}


@dataclass(frozen=True)
class MigrationValidation:
    organizations: int
    drivers: int
    driver_pay_rules: int
    legacy_vehicles: int
    power_units: int
    loads: int
    load_status_records: int
    load_stops: int
    legacy_revenue_cents: int
    normalized_revenue_cents: int
    tenant_mismatch_count: int
    unresolved_trailer_profiles: int
    valid: bool

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self)


class MigrationValidationError(RuntimeError):
    pass


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _execute_script_transactionally(conn: sqlite3.Connection, script: str) -> None:
    """Execute a SQLite script without ``executescript``'s implicit commit."""

    statement = ""
    for line in script.splitlines():
        statement += line + "\n"
        if sqlite3.complete_statement(statement):
            sql = statement.strip()
            statement = ""
            if sql:
                conn.execute(sql)
    if statement.strip():
        raise sqlite3.DatabaseError("Incomplete v0.16 migration statement")


def _add_columns(conn: sqlite3.Connection) -> None:
    for table, migrations in V016_COLUMN_MIGRATIONS.items():
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for column, statement in migrations:
            if column not in columns:
                conn.execute(statement)


def _amount_cents(value: Any, field: str) -> int:
    if value is None or (isinstance(value, str) and not value.strip()):
        value = "0"
    return money_to_cents(value, field=field)


def _basis_points(value: Any, field: str) -> int:
    if value is None or (isinstance(value, str) and not value.strip()):
        value = "0"
    return percentage_to_basis_points(value, field=field)


def _rate_micros(value: Any, field: str, default: str = "0") -> int:
    if value is None or (isinstance(value, str) and not value.strip()):
        value = default
    return rate_to_micros(value, field=field)


def _backfill_public_ids(conn: sqlite3.Connection) -> None:
    for table in ("drivers", "vehicles", "loads", "load_opportunities"):
        for row in conn.execute(
            f"SELECT id FROM {table} WHERE public_uuid IS NULL OR TRIM(public_uuid)=''"
        ).fetchall():
            conn.execute(
                f"UPDATE {table} SET public_uuid=? WHERE id=?",
                (_new_uuid(), row["id"]),
            )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_drivers_public_uuid ON drivers(public_uuid)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicles_public_uuid ON vehicles(public_uuid)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_loads_public_uuid ON loads(public_uuid)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_public_uuid ON load_opportunities(public_uuid)"
    )


def _migrate_roles(conn: sqlite3.Connection) -> None:
    conn.execute(
        """UPDATE users SET role='owner'
        WHERE is_admin=1 AND (role IS NULL OR TRIM(role)='' OR role='read_only')"""
    )
    conn.execute(
        """UPDATE users SET role='read_only'
        WHERE role IS NULL OR TRIM(role)=''"""
    )


def _migrate_driver_pay_rules(conn: sqlite3.Connection) -> None:
    drivers = conn.execute("SELECT * FROM drivers ORDER BY organization_id,id").fetchall()
    for driver in drivers:
        exists = conn.execute(
            "SELECT id FROM driver_pay_rules WHERE driver_id=? AND version=1",
            (driver["id"],),
        ).fetchone()
        if exists:
            continue
        pay_model = normalized_pay_model(driver["pay_model"])
        percentage_source = {
            "profit_split": driver["driver_profit_split_pct"],
            "contractor_rate_split": driver["contractor_gross_split_pct"],
            "owner_operator": driver["owner_operator_split_pct"],
        }.get(pay_model, 0)
        snapshot = {key: driver[key] for key in driver.keys()}
        effective_date = str(driver["fixed_cost_start"] or driver["created_at"] or date.today().isoformat())[:10]
        conn.execute(
            """INSERT INTO driver_pay_rules
            (public_uuid,organization_id,driver_id,effective_date,end_date,version,
             pay_model,percentage_basis_points,flat_rate_cents,
             loaded_mile_rate_micros,total_mile_rate_micros,day_rate_cents,
             included_revenue_json,included_expense_json,payroll_burden_applies,
             approval_status,source,legacy_snapshot_json)
            VALUES (?,?,?,?,?,1,?,?,?,?,?,?,?, ?,?,'DRAFT','legacy_migration',?)""",
            (
                _new_uuid(),
                driver["organization_id"],
                driver["id"],
                effective_date,
                driver["fixed_cost_end"],
                pay_model,
                _basis_points(percentage_source, f"driver {driver['id']} percentage"),
                _amount_cents(driver["flat_rate_per_load"], f"driver {driver['id']} flat rate"),
                _rate_micros(driver["pay_per_loaded_mile"], f"driver {driver['id']} loaded-mile rate"),
                _rate_micros(driver["pay_per_total_mile"], f"driver {driver['id']} total-mile rate"),
                _amount_cents(driver["day_rate"], f"driver {driver['id']} day rate"),
                json.dumps(["linehaul", "fuel_surcharge", "accessorial"], separators=(",", ":")),
                json.dumps(["fuel", "tolls", "maintenance", "fixed_cost"], separators=(",", ":")),
                int(bool(driver["payroll_burden_applies"])),
                json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str),
            ),
        )


def _driver_cost_source(conn: sqlite3.Connection, vehicle_id: int) -> sqlite3.Row | None:
    rows = conn.execute(
        "SELECT * FROM drivers WHERE vehicle_id=? ORDER BY id",
        (vehicle_id,),
    ).fetchall()
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            sum(
                _amount_cents(row[key], f"driver {row['id']} {key}")
                for key in (
                    "truck_financing_monthly",
                    "auto_insurance_monthly",
                    "other_fixed_monthly",
                )
            ),
            int(row["id"]),
        ),
    )


def _migrate_power_units(conn: sqlite3.Connection) -> None:
    for vehicle in conn.execute("SELECT * FROM vehicles ORDER BY organization_id,id").fetchall():
        exists = conn.execute(
            "SELECT id FROM power_units WHERE legacy_vehicle_id=?", (vehicle["id"],)
        ).fetchone()
        if exists:
            continue
        source = _driver_cost_source(conn, int(vehicle["id"]))
        source_snapshot = {key: source[key] for key in source.keys()} if source else {}
        conn.execute(
            """INSERT INTO power_units
            (public_uuid,organization_id,legacy_vehicle_id,public_identifier,
             company_unit_number,equipment_type,mpg_micros,financing_cents,
             insurance_cents,maintenance_reserve_micros,fixed_monthly_cost_cents,
             active,legacy_snapshot_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                vehicle["public_uuid"],
                vehicle["organization_id"],
                vehicle["id"],
                vehicle["name"],
                vehicle["name"],
                vehicle["equipment_type"] or "Truck",
                _rate_micros(source["mpg"] if source else 10, f"vehicle {vehicle['id']} mpg", "10"),
                _amount_cents(source["truck_financing_monthly"] if source else 0, f"vehicle {vehicle['id']} financing"),
                _amount_cents(source["auto_insurance_monthly"] if source else 0, f"vehicle {vehicle['id']} insurance"),
                _rate_micros(source["maintenance_per_mile"] if source else 0, f"vehicle {vehicle['id']} maintenance"),
                _amount_cents(source["other_fixed_monthly"] if source else 0, f"vehicle {vehicle['id']} fixed cost"),
                int(bool(vehicle["active"])),
                json.dumps(source_snapshot, sort_keys=True, separators=(",", ":"), default=str),
            ),
        )


def _migrate_equipment_assignments(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """SELECT d.*,p.id AS power_unit_id FROM drivers d
        JOIN power_units p ON p.legacy_vehicle_id=d.vehicle_id
        WHERE d.vehicle_id IS NOT NULL ORDER BY d.organization_id,d.id"""
    ).fetchall()
    for row in rows:
        exists = conn.execute(
            """SELECT id FROM equipment_assignments
            WHERE organization_id=? AND driver_id=? AND power_unit_id=? AND end_at IS NULL""",
            (row["organization_id"], row["id"], row["power_unit_id"]),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO equipment_assignments
            (public_uuid,organization_id,driver_id,power_unit_id,start_at,source)
            VALUES (?,?,?,?,?,'legacy_migration')""",
            (
                _new_uuid(),
                row["organization_id"],
                row["id"],
                row["power_unit_id"],
                row["fixed_cost_start"] or row["created_at"],
            ),
        )


def _migrate_loads(conn: sqlite3.Connection) -> None:
    loads = conn.execute("SELECT * FROM loads ORDER BY organization_id,id").fetchall()
    for load in loads:
        status = normalize_state(load["status_code"] or load["status"])
        conn.execute(
            """UPDATE loads SET status_code=?,updated_at=COALESCE(updated_at,created_at)
            WHERE id=?""",
            (status.value, load["id"]),
        )
        status_exists = conn.execute(
            """SELECT id FROM load_status_history
            WHERE organization_id=? AND idempotency_key=?""",
            (load["organization_id"], f"migration:load:{load['id']}:initial"),
        ).fetchone()
        if not status_exists:
            conn.execute(
                """INSERT INTO load_status_history
                (organization_id,load_id,prior_status,new_status,idempotency_key,reason)
                VALUES (?,?,NULL,?,?,?)""",
                (
                    load["organization_id"],
                    load["id"],
                    status.value,
                    f"migration:load:{load['id']}:initial",
                    "Initial state mapped from legacy status",
                ),
            )
        for sequence, stop_type, prefix, fallback in (
            (1, "PICKUP", "pickup", load["origin"]),
            (2, "DELIVERY", "delivery", load["destination"]),
        ):
            stop_exists = conn.execute(
                "SELECT id FROM load_stops WHERE load_id=? AND sequence_number=?",
                (load["id"], sequence),
            ).fetchone()
            if not stop_exists:
                conn.execute(
                    """INSERT INTO load_stops
                    (public_uuid,organization_id,load_id,sequence_number,stop_type,
                     facility_name,address_line1,appointment_local_start,
                     appointment_local_end,contact_name,contact_phone,instructions)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        _new_uuid(),
                        load["organization_id"],
                        load["id"],
                        sequence,
                        stop_type,
                        fallback,
                        load[f"{prefix}_address"],
                        load[f"{prefix}_window_start"],
                        load[f"{prefix}_window_end"],
                        load[f"{prefix}_contact_name"],
                        load[f"{prefix}_contact_phone"],
                        load[f"{prefix}_instructions"],
                    ),
                )
        if load["driver_id"] or load["vehicle_id"]:
            power = conn.execute(
                "SELECT id FROM power_units WHERE legacy_vehicle_id=?",
                (load["vehicle_id"],),
            ).fetchone()
            assignment_exists = conn.execute(
                """SELECT id FROM load_assignments
                WHERE load_id=? AND assignment_stage='LEGACY_BOOKED'""",
                (load["id"],),
            ).fetchone()
            if not assignment_exists:
                conn.execute(
                    """INSERT INTO load_assignments
                    (public_uuid,organization_id,load_id,driver_id,power_unit_id,
                     assignment_stage,provisional,deadhead_miles_micros,route_source)
                    VALUES (?,?,?,?,?,'LEGACY_BOOKED',0,?,'legacy_manual')""",
                    (
                        _new_uuid(),
                        load["organization_id"],
                        load["id"],
                        load["driver_id"],
                        power["id"] if power else None,
                        _rate_micros(load["deadhead_miles"], f"load {load['id']} deadhead"),
                    ),
                )
        revenue_value = load["revenue"]
        if revenue_value is not None:
            conn.execute(
                """INSERT OR IGNORE INTO load_revenue_items
                (public_uuid,organization_id,load_id,category,description,
                 amount_cents,stage,source)
                VALUES (?,?,?,'linehaul','Migrated legacy all-in revenue',?,'BOOKED','legacy_migration')""",
                (
                    _new_uuid(),
                    load["organization_id"],
                    load["id"],
                    _amount_cents(revenue_value, f"load {load['id']} revenue"),
                ),
            )
        for category, column in (("tolls", "tolls_misc"), ("other_expense", "other_direct_costs")):
            amount = _amount_cents(load[column], f"load {load['id']} {column}")
            if amount:
                conn.execute(
                    """INSERT OR IGNORE INTO load_expense_items
                    (public_uuid,organization_id,load_id,category,description,
                     amount_cents,stage,source)
                    VALUES (?,?,?,?,? ,?,'BOOKED','legacy_migration')""",
                    (
                        _new_uuid(),
                        load["organization_id"],
                        load["id"],
                        category,
                        f"Migrated legacy {column}",
                        amount,
                    ),
                )


def validate_v016_migration(conn: sqlite3.Connection) -> MigrationValidation:
    def scalar(sql: str, params: tuple[Any, ...] = ()) -> int:
        return int(conn.execute(sql, params).fetchone()[0] or 0)

    drivers = scalar("SELECT COUNT(*) FROM drivers")
    legacy_vehicles = scalar("SELECT COUNT(*) FROM vehicles")
    loads = scalar("SELECT COUNT(*) FROM loads")
    legacy_revenue = sum(
        _amount_cents(row["revenue"], f"load {row['id']} revenue")
        for row in conn.execute("SELECT id,revenue FROM loads WHERE revenue IS NOT NULL")
    )
    normalized_revenue = scalar(
        """SELECT COALESCE(SUM(amount_cents),0) FROM load_revenue_items
        WHERE stage='BOOKED' AND source='legacy_migration'"""
    )
    mismatch_count = scalar(
        """SELECT
        (SELECT COUNT(*) FROM driver_pay_rules r JOIN drivers d ON d.id=r.driver_id
         WHERE r.organization_id<>d.organization_id) +
        (SELECT COUNT(*) FROM equipment_assignments a JOIN drivers d ON d.id=a.driver_id
         WHERE a.organization_id<>d.organization_id) +
        (SELECT COUNT(*) FROM equipment_assignments a JOIN power_units p ON p.id=a.power_unit_id
         WHERE a.organization_id<>p.organization_id) +
        (SELECT COUNT(*) FROM load_stops s JOIN loads l ON l.id=s.load_id
         WHERE s.organization_id<>l.organization_id) +
        (SELECT COUNT(*) FROM load_assignments a JOIN loads l ON l.id=a.load_id
         WHERE a.organization_id<>l.organization_id) +
        (SELECT COUNT(*) FROM load_assignments a JOIN drivers d ON d.id=a.driver_id
         WHERE a.organization_id<>d.organization_id) +
        (SELECT COUNT(*) FROM load_assignments a JOIN power_units p ON p.id=a.power_unit_id
         WHERE a.organization_id<>p.organization_id) +
        (SELECT COUNT(*) FROM load_revenue_items i JOIN loads l ON l.id=i.load_id
         WHERE i.organization_id<>l.organization_id) +
        (SELECT COUNT(*) FROM load_expense_items i JOIN loads l ON l.id=i.load_id
         WHERE i.organization_id<>l.organization_id)"""
    )
    unresolved_trailers = scalar(
        """SELECT COUNT(*) FROM drivers
        WHERE COALESCE(trailer_financing_monthly,0)<>0
           OR COALESCE(trailer_insurance_monthly,0)<>0"""
    )
    pay_rules = scalar(
        "SELECT COUNT(*) FROM driver_pay_rules WHERE version=1 AND source='legacy_migration'"
    )
    power_units = scalar("SELECT COUNT(*) FROM power_units WHERE legacy_vehicle_id IS NOT NULL")
    load_status_records = scalar(
        """SELECT COUNT(DISTINCT load_id) FROM load_status_history
        WHERE idempotency_key LIKE 'migration:load:%:initial'"""
    )
    load_stops = scalar(
        """SELECT COUNT(*) FROM load_stops
        WHERE sequence_number IN (1,2) AND stop_type IN ('PICKUP','DELIVERY')"""
    )
    valid = all(
        (
            drivers == pay_rules,
            legacy_vehicles == power_units,
            load_status_records == loads,
            load_stops == loads * 2,
            legacy_revenue == normalized_revenue,
            mismatch_count == 0,
        )
    )
    return MigrationValidation(
        organizations=scalar("SELECT COUNT(*) FROM organizations"),
        drivers=drivers,
        driver_pay_rules=pay_rules,
        legacy_vehicles=legacy_vehicles,
        power_units=power_units,
        loads=loads,
        load_status_records=load_status_records,
        load_stops=load_stops,
        legacy_revenue_cents=legacy_revenue,
        normalized_revenue_cents=normalized_revenue,
        tenant_mismatch_count=mismatch_count,
        unresolved_trailer_profiles=unresolved_trailers,
        valid=valid,
    )


def migrate_v016_foundation(conn: sqlite3.Connection) -> MigrationValidation:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("SAVEPOINT v016_foundation")
    try:
        _add_columns(conn)
        _execute_script_transactionally(conn, V016_SCHEMA)
        _backfill_public_ids(conn)
        _migrate_roles(conn)
        _migrate_driver_pay_rules(conn)
        _migrate_power_units(conn)
        _migrate_equipment_assignments(conn)
        _migrate_loads(conn)
        validation = validate_v016_migration(conn)
        if not validation.valid:
            raise MigrationValidationError(
                "v0.16 migration validation failed: " + json.dumps(validation.to_dict(), sort_keys=True)
            )
        conn.execute(
            """INSERT INTO v016_migration_runs
            (migration_key,started_at,completed_at,validation_json,status)
            VALUES ('v016_foundation',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,?,'validated')
            ON CONFLICT(migration_key) DO UPDATE SET
              completed_at=CURRENT_TIMESTAMP,
              validation_json=excluded.validation_json,
              status='validated'""",
            (json.dumps(validation.to_dict(), sort_keys=True, separators=(",", ":")),),
        )
        conn.execute("RELEASE SAVEPOINT v016_foundation")
        return validation
    except (sqlite3.DatabaseError, MoneyInputError, MigrationValidationError):
        conn.execute("ROLLBACK TO SAVEPOINT v016_foundation")
        conn.execute("RELEASE SAVEPOINT v016_foundation")
        raise


V016_ROLLBACK_TABLES = (
    "v016_migration_runs",
    "load_financial_snapshots",
    "load_status_history",
    "load_expense_items",
    "load_revenue_items",
    "load_assignments",
    "load_stops",
    "equipment_assignments",
    "trailers",
    "power_units",
    "driver_pay_rules",
)


def rollback_v016_foundation(conn: sqlite3.Connection) -> None:
    """Remove additive v0.16 tables while retaining all legacy source records.

    SQLite additive columns remain intentionally; v0.15 ignores them and this avoids
    rebuilding live legacy tables during an emergency rollback.
    """

    conn.execute("DROP TRIGGER IF EXISTS load_financial_snapshots_no_update")
    conn.execute("DROP TRIGGER IF EXISTS load_financial_snapshots_no_delete")
    conn.execute("DROP TRIGGER IF EXISTS audit_events_no_update")
    conn.execute("DROP TRIGGER IF EXISTS audit_events_no_delete")
    for table in V016_ROLLBACK_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.execute("PRAGMA user_version=12")
