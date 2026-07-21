from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "carrieros_v02.db"
SNAPSHOT_PATH = APP_DIR / "data" / "private_seed_snapshot.json"
PASSWORD_HASH_ITERATIONS = 600_000

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_name TEXT,
    owner_email TEXT,
    fallback_diesel_price REAL NOT NULL DEFAULT 5.66,
    processing_fee_pct REAL NOT NULL DEFAULT 3.0,
    admin_fee_per_load REAL NOT NULL DEFAULT 5.0,
    payroll_burden_pct REAL NOT NULL DEFAULT 5.0,
    target_margin_pct REAL NOT NULL DEFAULT 10.0,
    target_max_deadhead_pct REAL NOT NULL DEFAULT 15.0,
    min_company_profit_per_mile REAL NOT NULL DEFAULT 0.25,
    owner_distribution_pct REAL NOT NULL DEFAULT 50.0,
    supported_start_date TEXT NOT NULL DEFAULT '2025-01-01',
    supported_end_date TEXT NOT NULL DEFAULT '2032-12-31',
    max_active_days INTEGER NOT NULL DEFAULT 31,
    tax_reserve_pct REAL NOT NULL DEFAULT 0,
    growth_reserve_pct REAL NOT NULL DEFAULT 0,
    reporting_start_month TEXT NOT NULL DEFAULT '2026-05-01',
    default_report_month TEXT NOT NULL DEFAULT '2026-07-01',
    source_filename TEXT,
    source_sync_date TEXT,
    plan_code TEXT NOT NULL DEFAULT 'owner_operator',
    active_unit_limit INTEGER NOT NULL DEFAULT 2,
    subscription_status TEXT NOT NULL DEFAULT 'trialing',
    trial_ends_at TEXT,
    billing_customer_reference TEXT,
    billing_subscription_reference TEXT,
    billing_price_reference TEXT,
    subscription_current_period_end TEXT,
    subscription_cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    terms_accepted_at TEXT,
    terms_version TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processed_stripe_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    user_id INTEGER,
    event_type TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS overhead_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    monthly_cost REAL NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quick_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    label TEXT NOT NULL COLLATE NOCASE,
    url TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Other',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, label),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    equipment_type TEXT NOT NULL DEFAULT 'Truck',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, name),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    vehicle_id INTEGER,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    role TEXT NOT NULL DEFAULT 'Driver',
    pay_model TEXT NOT NULL DEFAULT 'Profit Split',
    equipment_type TEXT,
    fixed_cost_start TEXT,
    fixed_cost_end TEXT,
    truck_financing_monthly REAL NOT NULL DEFAULT 0,
    auto_insurance_monthly REAL NOT NULL DEFAULT 0,
    trailer_financing_monthly REAL NOT NULL DEFAULT 0,
    trailer_insurance_monthly REAL NOT NULL DEFAULT 0,
    other_fixed_monthly REAL NOT NULL DEFAULT 0,
    mpg REAL NOT NULL DEFAULT 10,
    maintenance_per_mile REAL NOT NULL DEFAULT 0.20,
    driver_profit_split_pct REAL NOT NULL DEFAULT 0,
    contractor_gross_split_pct REAL NOT NULL DEFAULT 0,
    owner_operator_split_pct REAL NOT NULL DEFAULT 0,
    flat_rate_per_load REAL NOT NULL DEFAULT 0,
    pay_per_loaded_mile REAL NOT NULL DEFAULT 0,
    pay_per_total_mile REAL NOT NULL DEFAULT 0,
    day_rate REAL NOT NULL DEFAULT 0,
    payroll_burden_applies INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    source_row INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS weekly_fuel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    average_price REAL NOT NULL,
    source_notes TEXT,
    entered_by TEXT,
    source_row INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, week_start),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS loads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    load_number TEXT NOT NULL,
    pickup_date TEXT,
    delivery_date TEXT,
    driver_id INTEGER,
    vehicle_id INTEGER,
    broker TEXT,
    origin TEXT,
    destination TEXT,
    status TEXT NOT NULL DEFAULT 'Booked',
    revenue REAL,
    loaded_miles REAL NOT NULL DEFAULT 0,
    deadhead_miles REAL NOT NULL DEFAULT 0,
    fuel_override REAL,
    tolls_misc REAL NOT NULL DEFAULT 0,
    other_direct_costs REAL NOT NULL DEFAULT 0,
    notes TEXT,
    include_in_model INTEGER NOT NULL DEFAULT 1,
    source_row INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    driver_id INTEGER,
    load_id INTEGER,
    paid_at TEXT NOT NULL,
    payment_type TEXT NOT NULL DEFAULT 'Regular payout',
    amount REAL NOT NULL,
    method TEXT,
    reference TEXT,
    notes TEXT,
    counts_against_load_pay INTEGER NOT NULL DEFAULT 1,
    include_in_reports INTEGER NOT NULL DEFAULT 1,
    source_row INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS idle_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    start_date TEXT,
    end_date TEXT,
    driver_id INTEGER,
    vehicle_id INTEGER,
    situation TEXT,
    include_in_model INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    source_row INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS compliance_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id INTEGER,
    subject_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    expiration_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS onboarding_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    license_number TEXT,
    license_state TEXT,
    medical_card_expiration TEXT,
    employment_history TEXT,
    emergency_contact TEXT,
    status TEXT NOT NULL DEFAULT 'Invited',
    expires_at TEXT,
    submitted_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    invoice_number TEXT NOT NULL,
    customer TEXT NOT NULL,
    load_id INTEGER,
    amount REAL NOT NULL DEFAULT 0,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    paid_date TEXT,
    status TEXT NOT NULL DEFAULT 'Unpaid',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS detention_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    load_id INTEGER,
    broker TEXT NOT NULL,
    arrival_at TEXT NOT NULL,
    departure_at TEXT NOT NULL,
    free_minutes INTEGER NOT NULL DEFAULT 120,
    hourly_rate REAL NOT NULL DEFAULT 75,
    amount_claimed REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Draft',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS generated_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_loads_org_dates ON loads(organization_id, pickup_date, delivery_date);
CREATE INDEX IF NOT EXISTS idx_payments_org_driver ON payments(organization_id, driver_id, paid_at);
CREATE INDEX IF NOT EXISTS idx_fuel_org_week ON weekly_fuel(organization_id, week_start);
CREATE INDEX IF NOT EXISTS idx_idle_org_dates ON idle_periods(organization_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_compliance_expiry ON compliance_items(organization_id, expiration_date);
CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(organization_id, due_date);
CREATE INDEX IF NOT EXISTS idx_audit_events_org_created ON audit_events(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_quick_links_org_sort ON quick_links(organization_id, sort_order, label);
PRAGMA user_version = 8;
"""

ORGANIZATION_MIGRATIONS = (
    ("plan_code", "ALTER TABLE organizations ADD COLUMN plan_code TEXT NOT NULL DEFAULT 'owner_operator'"),
    ("active_unit_limit", "ALTER TABLE organizations ADD COLUMN active_unit_limit INTEGER NOT NULL DEFAULT 2"),
    ("subscription_status", "ALTER TABLE organizations ADD COLUMN subscription_status TEXT NOT NULL DEFAULT 'trialing'"),
    ("trial_ends_at", "ALTER TABLE organizations ADD COLUMN trial_ends_at TEXT"),
    ("billing_customer_reference", "ALTER TABLE organizations ADD COLUMN billing_customer_reference TEXT"),
    ("billing_subscription_reference", "ALTER TABLE organizations ADD COLUMN billing_subscription_reference TEXT"),
    ("billing_price_reference", "ALTER TABLE organizations ADD COLUMN billing_price_reference TEXT"),
    ("subscription_current_period_end", "ALTER TABLE organizations ADD COLUMN subscription_current_period_end TEXT"),
    ("subscription_cancel_at_period_end", "ALTER TABLE organizations ADD COLUMN subscription_cancel_at_period_end INTEGER NOT NULL DEFAULT 0"),
    ("terms_accepted_at", "ALTER TABLE organizations ADD COLUMN terms_accepted_at TEXT"),
    ("terms_version", "ALTER TABLE organizations ADD COLUMN terms_version TEXT"),
)

DRIVER_MIGRATIONS = (
    ("flat_rate_per_load", "ALTER TABLE drivers ADD COLUMN flat_rate_per_load REAL NOT NULL DEFAULT 0"),
    ("pay_per_loaded_mile", "ALTER TABLE drivers ADD COLUMN pay_per_loaded_mile REAL NOT NULL DEFAULT 0"),
    ("pay_per_total_mile", "ALTER TABLE drivers ADD COLUMN pay_per_total_mile REAL NOT NULL DEFAULT 0"),
    ("day_rate", "ALTER TABLE drivers ADD COLUMN day_rate REAL NOT NULL DEFAULT 0"),
)

ONBOARDING_MIGRATIONS = (
    ("expires_at", "ALTER TABLE onboarding_applications ADD COLUMN expires_at TEXT"),
)


def get_db_path() -> Path:
    return Path(os.getenv("CARRIEROS_DB", str(DEFAULT_DB_PATH)))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


@contextmanager
def db_session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with db_session() as conn:
        cur = conn.execute(sql, tuple(params))
        return int(cur.lastrowid)


def record_audit_event(
    event_type: str,
    organization_id: int | None = None,
    user_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> int:
    """Append a minimal event without storing credentials or customer-entered records."""
    payload = json.dumps(details or {}, separators=(",", ":"), sort_keys=True)
    with db_session() as conn:
        cursor = conn.execute(
            """INSERT INTO audit_events
            (organization_id, user_id, event_type, details_json)
            VALUES (?, ?, ?, ?)""",
            (organization_id, user_id, event_type, payload),
        )
        return int(cursor.lastrowid)


def query_all(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with connect() as conn:
        return list(conn.execute(sql, tuple(params)).fetchall())


def query_one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(sql, tuple(params)).fetchone()


def hash_password(
    password: str,
    salt: str | None = None,
    iterations: int = PASSWORD_HASH_ITERATIONS,
) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
        try:
            iterations = int(parts[1])
        except ValueError:
            return False
        salt, expected = parts[2], parts[3]
    elif len(parts) == 2:
        # Legacy CarrierOS hashes used 180,000 PBKDF2 iterations.
        iterations, salt, expected = 180_000, parts[0], parts[1]
    else:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    ).hex()
    return secrets.compare_digest(actual, expected)


def password_needs_rehash(stored: str) -> bool:
    parts = stored.split("$")
    return not (
        len(parts) == 4
        and parts[0] == "pbkdf2_sha256"
        and parts[1].isdigit()
        and int(parts[1]) >= PASSWORD_HASH_ITERATIONS
    )


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_password_reset_token(user_id: int, lifetime_minutes: int = 30) -> str:
    raw_token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=lifetime_minutes)
    ).replace(microsecond=0).isoformat()
    with db_session() as conn:
        conn.execute(
            "DELETE FROM password_reset_tokens WHERE user_id=? OR expires_at<?",
            (user_id, utc_now_iso()),
        )
        conn.execute(
            "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, token_digest(raw_token), expires_at),
        )
    return raw_token


def reset_password_with_token(token: str, new_password_hash: str) -> sqlite3.Row | None:
    now = utc_now_iso()
    with db_session() as conn:
        row = conn.execute(
            """SELECT t.id AS token_id, u.id AS user_id, u.organization_id
            FROM password_reset_tokens t
            JOIN users u ON u.id=t.user_id
            WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>=?""",
            (token_digest(token), now),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (new_password_hash, row["user_id"]),
        )
        conn.execute(
            "UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL",
            (now, row["user_id"]),
        )
        return row


def init_db(seed: bool = False) -> None:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(organizations)")}
        for column, statement in ORGANIZATION_MIGRATIONS:
            if column not in columns:
                conn.execute(statement)
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_org_billing_customer
            ON organizations(billing_customer_reference)
            WHERE billing_customer_reference IS NOT NULL"""
        )
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_org_billing_subscription
            ON organizations(billing_subscription_reference)
            WHERE billing_subscription_reference IS NOT NULL"""
        )
        driver_columns = {row["name"] for row in conn.execute("PRAGMA table_info(drivers)")}
        for column, statement in DRIVER_MIGRATIONS:
            if column not in driver_columns:
                conn.execute(statement)
        onboarding_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(onboarding_applications)")
        }
        for column, statement in ONBOARDING_MIGRATIONS:
            if column not in onboarding_columns:
                conn.execute(statement)
        conn.commit()
    if seed:
        if not SNAPSHOT_PATH.exists():
            raise RuntimeError(
                "CARRIEROS_SEED_SNAPSHOT is enabled, but the private workbook snapshot is not present."
            )
        seed_snapshot_data()


def load_snapshot() -> dict[str, Any]:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def seed_snapshot_data(force: bool = False) -> None:
    snapshot = load_snapshot()
    with db_session() as conn:
        exists = conn.execute("SELECT id FROM organizations LIMIT 1").fetchone()
        if exists and not force:
            return
        if force:
            for table in (
                "detention_claims", "invoices", "generated_documents", "onboarding_applications",
                "compliance_items", "idle_periods", "payments", "loads", "weekly_fuel",
                "drivers", "vehicles", "quick_links", "overhead_items", "users", "organizations",
            ):
                conn.execute(f"DELETE FROM {table}")

        org = snapshot["organization"]
        settings = snapshot["settings"]
        source = snapshot["source"]
        org_id = conn.execute(
            """INSERT INTO organizations
            (name, owner_name, owner_email, fallback_diesel_price, processing_fee_pct,
             admin_fee_per_load, payroll_burden_pct, target_margin_pct,
             target_max_deadhead_pct, min_company_profit_per_mile,
             owner_distribution_pct, supported_start_date, supported_end_date,
             max_active_days, tax_reserve_pct, growth_reserve_pct,
             reporting_start_month, default_report_month, source_filename, source_sync_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                org["name"], org.get("owner_name"), org.get("owner_email"),
                settings["fallback_diesel_price"], settings["processing_fee_pct"],
                settings["admin_fee_per_load"], settings["payroll_burden_pct"],
                settings["target_margin_pct"], settings["target_max_deadhead_pct"],
                settings["min_company_profit_per_mile"], settings["owner_distribution_pct"],
                settings["supported_start_date"], settings["supported_end_date"],
                settings["max_active_days"], settings["tax_reserve_pct"],
                settings["growth_reserve_pct"], settings["reporting_start_month"],
                settings["default_report_month"], source["filename"], source["sync_date"],
            ),
        ).lastrowid
        conn.execute(
            "INSERT INTO users (organization_id, full_name, email, password_hash, is_admin) VALUES (?, ?, ?, ?, 1)",
            (org_id, org.get("owner_name") or "Administrator", "admin@example.invalid", hash_password(secrets.token_urlsafe(32))),
        )
        for order, item in enumerate(snapshot.get("overhead_items", []), 1):
            conn.execute(
                "INSERT INTO overhead_items (organization_id, name, monthly_cost, sort_order) VALUES (?, ?, ?, ?)",
                (org_id, item["name"], item["monthly_cost"], order),
            )

        vehicle_ids: dict[str, int] = {}
        for item in snapshot.get("vehicles", []):
            vehicle_ids[item["name"]] = int(conn.execute(
                "INSERT INTO vehicles (organization_id, name, equipment_type, active) VALUES (?, ?, ?, ?)",
                (org_id, item["name"], item.get("equipment_type") or "Truck", 1 if item.get("active", True) else 0),
            ).lastrowid)

        driver_ids: dict[str, int] = {}
        driver_vehicle: dict[str, int] = {}
        for item in snapshot.get("drivers", []):
            vehicle_id = vehicle_ids.get(item["vehicle_name"])
            driver_id = int(conn.execute(
                """INSERT INTO drivers
                (organization_id, vehicle_id, name, role, pay_model, equipment_type,
                 fixed_cost_start, fixed_cost_end, truck_financing_monthly,
                 auto_insurance_monthly, trailer_financing_monthly,
                 trailer_insurance_monthly, other_fixed_monthly, mpg,
                 maintenance_per_mile, driver_profit_split_pct,
                 contractor_gross_split_pct, owner_operator_split_pct,
                 payroll_burden_applies, notes, source_row, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    org_id, vehicle_id, item["name"], item.get("role") or "Driver",
                    item.get("pay_model") or "Profit Split", item.get("equipment_type") or "",
                    item.get("fixed_cost_start"), item.get("fixed_cost_end"),
                    item.get("truck_financing_monthly", 0), item.get("auto_insurance_monthly", 0),
                    item.get("trailer_financing_monthly", 0), item.get("trailer_insurance_monthly", 0),
                    item.get("other_fixed_monthly", 0), item.get("mpg", 10),
                    item.get("maintenance_per_mile", .20), item.get("driver_profit_split_pct", 0),
                    item.get("contractor_gross_split_pct", 0), item.get("owner_operator_split_pct", 0),
                    1 if item.get("payroll_burden_applies") else 0, item.get("notes") or "",
                    item.get("source_row"), 1 if item.get("enabled", True) else 0,
                ),
            ).lastrowid)
            driver_ids[item["name"]] = driver_id
            if vehicle_id:
                driver_vehicle[item["name"]] = vehicle_id

        for item in snapshot.get("weekly_fuel", []):
            conn.execute(
                """INSERT INTO weekly_fuel
                (organization_id, week_start, average_price, source_notes, entered_by, source_row)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (org_id, item["week_start"], item["average_price"], item.get("source_notes") or "", item.get("entered_by") or "", item.get("source_row")),
            )

        for item in snapshot.get("loads", []):
            driver_id = driver_ids.get(item.get("driver_name") or "")
            vehicle_id = driver_vehicle.get(item.get("driver_name") or "")
            number = item.get("load_number") or f"UNNUMBERED-{item.get('source_row', 'X')}"
            conn.execute(
                """INSERT INTO loads
                (organization_id, load_number, pickup_date, delivery_date, driver_id,
                 vehicle_id, broker, origin, destination, status, revenue, loaded_miles,
                 deadhead_miles, fuel_override, tolls_misc, other_direct_costs, notes,
                 include_in_model, source_row)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    org_id, number, item.get("pickup_date"), item.get("delivery_date"),
                    driver_id, vehicle_id, item.get("broker") or "", item.get("origin") or "",
                    item.get("destination") or "", item.get("status") or "Booked",
                    item.get("revenue"), item.get("loaded_miles", 0), item.get("deadhead_miles", 0),
                    item.get("fuel_override"), item.get("tolls_misc", 0), item.get("other_direct_costs", 0),
                    item.get("notes") or "", 1 if item.get("include_in_model", True) else 0, item.get("source_row"),
                ),
            )

        for item in snapshot.get("payments", []):
            conn.execute(
                """INSERT INTO payments
                (organization_id, driver_id, paid_at, payment_type, amount, method,
                 reference, notes, counts_against_load_pay, include_in_reports, source_row)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    org_id, driver_ids.get(item.get("driver_name") or ""), item["paid_at"],
                    item.get("payment_type") or "Regular payout", item.get("amount", 0),
                    item.get("method") or "", item.get("reference") or "", item.get("notes") or "",
                    1 if item.get("counts_against_load_pay", True) else 0,
                    1 if item.get("include_in_reports", True) else 0, item.get("source_row"),
                ),
            )

        for item in snapshot.get("idle_periods", []):
            driver_id = driver_ids.get(item.get("driver_name") or "")
            vehicle_id = vehicle_ids.get(item.get("vehicle_name") or "") or driver_vehicle.get(item.get("driver_name") or "")
            conn.execute(
                """INSERT INTO idle_periods
                (organization_id, start_date, end_date, driver_id, vehicle_id,
                 situation, include_in_model, notes, source_row)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    org_id, item.get("start_date"), item.get("end_date"), driver_id,
                    vehicle_id, item.get("situation") or "Company Responsibility",
                    1 if item.get("include", True) else 0, item.get("notes") or "", item.get("source_row"),
                ),
            )


def as_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def new_onboarding_token() -> str:
    return secrets.token_urlsafe(32)


def create_database_backup() -> Path | None:
    source_path = get_db_path()
    if not source_path.exists():
        return None
    backup_dir = Path(
        os.getenv("CARRIEROS_BACKUP_DIR", str(source_path.parent / "backups"))
    )
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    destination = backup_dir / f"carrieros-{timestamp}.db"
    with sqlite3.connect(source_path, timeout=30) as source:
        with sqlite3.connect(destination, timeout=30) as target:
            source.backup(target)
    with sqlite3.connect(destination, timeout=30) as verification:
        result = verification.execute("PRAGMA quick_check").fetchone()
        if not result or result[0] != "ok":
            destination.unlink(missing_ok=True)
            raise RuntimeError("CarrierOS database backup failed integrity verification")
    retention = max(2, int(os.getenv("CARRIEROS_BACKUP_RETENTION", "14")))
    backups = sorted(
        backup_dir.glob("carrieros-*.db"), key=lambda item: item.stat().st_mtime, reverse=True
    )
    for expired in backups[retention:]:
        expired.unlink(missing_ok=True)
    return destination


ORGANIZATION_EXPORT_TABLES = (
    "audit_events",
    "overhead_items",
    "quick_links",
    "vehicles",
    "drivers",
    "weekly_fuel",
    "loads",
    "payments",
    "idle_periods",
    "compliance_items",
    "onboarding_applications",
    "invoices",
    "detention_claims",
    "generated_documents",
)


def export_organization_data(organization_id: int) -> dict[str, Any]:
    with connect() as conn:
        organization = conn.execute(
            "SELECT * FROM organizations WHERE id=?", (organization_id,)
        ).fetchone()
        if not organization:
            raise ValueError("Organization not found")
        users = conn.execute(
            """SELECT id, organization_id, full_name, email, is_admin, created_at
            FROM users WHERE organization_id=? ORDER BY id""",
            (organization_id,),
        ).fetchall()
        payload: dict[str, Any] = {
            "exported_at": utc_now_iso(),
            "organization": dict(organization),
            "users": [dict(row) for row in users],
        }
        for table in ORGANIZATION_EXPORT_TABLES:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE organization_id=? ORDER BY id",
                (organization_id,),
            ).fetchall()
            payload[table] = [dict(row) for row in rows]
        return payload


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
