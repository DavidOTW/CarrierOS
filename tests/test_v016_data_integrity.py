from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db import connect, db_session, init_db, record_audit_event
from app.load_states import LoadState, LoadStateError, transition_load_state
from app.permissions import Role, has_permission, normalize_role
from app.v016_migration import rollback_v016_foundation, validate_v016_migration


def _seed_legacy_records() -> tuple[int, int, int]:
    with db_session() as conn:
        org_id = int(
            conn.execute(
                "INSERT INTO organizations (name) VALUES ('Migration Fleet')"
            ).lastrowid
        )
        user_id = int(
            conn.execute(
                """INSERT INTO users
                (organization_id,full_name,email,password_hash,is_admin)
                VALUES (?,?,?,?,1)""",
                (org_id, "Owner", "migration@example.invalid", "unused"),
            ).lastrowid
        )
        vehicle_id = int(
            conn.execute(
                """INSERT INTO vehicles
                (organization_id,name,equipment_type,active)
                VALUES (?,?,?,1)""",
                (org_id, "Unit 12", "Tractor"),
            ).lastrowid
        )
        driver_id = int(
            conn.execute(
                """INSERT INTO drivers
                (organization_id,vehicle_id,name,pay_model,flat_rate_per_load,
                 truck_financing_monthly,auto_insurance_monthly,mpg,
                 maintenance_per_mile,active)
                VALUES (?,?,?,'Flat Rate per Load',?,?,?,?,?,1)""",
                (org_id, vehicle_id, "Driver One", 300, 600, 300, 7.5, 0.20),
            ).lastrowid
        )
        load_id = int(
            conn.execute(
                """INSERT INTO loads
                (organization_id,load_number,status,revenue,driver_id,vehicle_id,
                 origin,destination,loaded_miles,deadhead_miles,tolls_misc)
                VALUES (?,?,?, ?,?,?, ?,?,?,?,?)""",
                (
                    org_id,
                    "MIG-100",
                    "Delivered",
                    1234.56,
                    driver_id,
                    vehicle_id,
                    "Nashville, TN",
                    "Atlanta, GA",
                    250,
                    25,
                    18.75,
                ),
            ).lastrowid
        )
    return org_id, user_id, load_id


def test_v016_migration_preserves_counts_money_and_public_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "foundation.db"))
    init_db()
    org_id, _, load_id = _seed_legacy_records()
    init_db()
    with connect() as conn:
        validation = validate_v016_migration(conn)
        load = conn.execute("SELECT * FROM loads WHERE id=?", (load_id,)).fetchone()
        pay_rule = conn.execute(
            "SELECT * FROM driver_pay_rules WHERE organization_id=?", (org_id,)
        ).fetchone()
        owner = conn.execute("SELECT * FROM users WHERE organization_id=?", (org_id,)).fetchone()
        revenue = conn.execute(
            "SELECT amount_cents FROM load_revenue_items WHERE load_id=?", (load_id,)
        ).fetchone()
        stops = conn.execute(
            "SELECT sequence_number,stop_type FROM load_stops WHERE load_id=? ORDER BY sequence_number",
            (load_id,),
        ).fetchall()
    assert validation.valid is True
    assert validation.legacy_revenue_cents == validation.normalized_revenue_cents == 123456
    assert load["public_uuid"] and load["status_code"] == LoadState.DELIVERED_DOCUMENTS_PENDING
    assert pay_rule["flat_rate_cents"] == 30000
    assert owner["role"] == Role.OWNER
    assert revenue["amount_cents"] == 123456
    assert [(row["sequence_number"], row["stop_type"]) for row in stops] == [
        (1, "PICKUP"),
        (2, "DELIVERY"),
    ]
    with db_session() as conn:
        conn.execute(
            """INSERT INTO load_stops
            (public_uuid,organization_id,load_id,sequence_number,stop_type,facility_name)
            VALUES ('future-stop',?,?,3,'INTERMEDIATE','Future normalized stop')""",
            (org_id, load_id),
        )
        conn.execute(
            """INSERT INTO driver_pay_rules
            (public_uuid,organization_id,driver_id,effective_date,version,pay_model,source)
            VALUES ('future-pay-rule',?,?, '2026-08-01',2,'flat_rate_per_load','manual')""",
            (org_id, pay_rule["driver_id"]),
        )
        assert validate_v016_migration(conn).valid is True


def test_state_machine_is_tenant_scoped_audited_and_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "states.db"))
    init_db()
    org_id, user_id, load_id = _seed_legacy_records()
    init_db()
    with db_session() as conn:
        first = transition_load_state(
            conn,
            organization_id=org_id,
            load_id=load_id,
            target=LoadState.READY_TO_INVOICE,
            actor_user_id=user_id,
            idempotency_key="test:delivery-ready:1",
            reason="Required documents reviewed",
        )
        repeated = transition_load_state(
            conn,
            organization_id=org_id,
            load_id=load_id,
            target=LoadState.READY_TO_INVOICE,
            actor_user_id=user_id,
            idempotency_key="test:delivery-ready:1",
            reason="Retry",
        )
        assert first["id"] == repeated["id"]
        with pytest.raises(LoadStateError):
            transition_load_state(
                conn,
                organization_id=org_id,
                load_id=load_id,
                target=LoadState.CLOSED,
                actor_user_id=user_id,
                idempotency_key="test:skip-to-close",
            )
        with pytest.raises(LoadStateError, match="Unknown load state"):
            transition_load_state(
                conn,
                organization_id=org_id,
                load_id=load_id,
                target="whatever someone typed",
                actor_user_id=user_id,
                idempotency_key="test:free-text",
            )
        with pytest.raises(LoadStateError, match="another target state"):
            transition_load_state(
                conn,
                organization_id=org_id,
                load_id=load_id,
                target=LoadState.INVOICED,
                actor_user_id=user_id,
                idempotency_key="test:delivery-ready:1",
            )
        with pytest.raises(LookupError):
            transition_load_state(
                conn,
                organization_id=org_id + 1,
                load_id=load_id,
                target=LoadState.INVOICED,
                actor_user_id=user_id,
                idempotency_key="test:wrong-tenant",
            )


def test_state_transition_rejects_an_actor_from_another_tenant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "actor-tenant.db"))
    init_db()
    org_id, _, load_id = _seed_legacy_records()
    with db_session() as conn:
        other_org_id = int(
            conn.execute("INSERT INTO organizations (name) VALUES ('Other Fleet')").lastrowid
        )
        other_user_id = int(
            conn.execute(
                """INSERT INTO users
                (organization_id,full_name,email,password_hash,is_admin,role)
                VALUES (?,?,?,?,0,'dispatcher')""",
                (other_org_id, "Other Dispatcher", "other@example.invalid", "unused"),
            ).lastrowid
        )
    init_db()
    with db_session() as conn:
        with pytest.raises(LoadStateError, match="does not belong"):
            transition_load_state(
                conn,
                organization_id=org_id,
                load_id=load_id,
                target=LoadState.READY_TO_INVOICE,
                actor_user_id=other_user_id,
                idempotency_key="test:foreign-actor",
            )


def test_audit_events_are_append_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "audit.db"))
    init_db()
    event_id = record_audit_event("integrity.test", details={"safe": True})
    with connect() as conn:
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            conn.execute("UPDATE audit_events SET event_type='changed' WHERE id=?", (event_id,))
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            conn.execute("DELETE FROM audit_events WHERE id=?", (event_id,))


def test_role_permission_matrix_is_centralized_and_least_privilege() -> None:
    assert normalize_role(None, legacy_admin=True) == Role.OWNER
    assert has_permission(Role.OWNER, "billing.manage")
    assert has_permission(Role.DISPATCHER, "loads.manage")
    assert not has_permission(Role.DISPATCHER, "payments.manage")
    assert has_permission(Role.DRIVER, "driver.loads.view_assigned")
    assert not has_permission(Role.DRIVER, "money.view")


def test_additive_rollback_preserves_legacy_records(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CARRIEROS_DB", str(tmp_path / "rollback.db"))
    init_db()
    org_id, _, load_id = _seed_legacy_records()
    init_db()
    with db_session() as conn:
        rollback_v016_foundation(conn)
    with connect() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 12
        legacy_load = conn.execute(
            "SELECT organization_id,revenue FROM loads WHERE id=?", (load_id,)
        ).fetchone()
        assert legacy_load["organization_id"] == org_id
        assert legacy_load["revenue"] == pytest.approx(1234.56)
        tables = {
            row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "driver_pay_rules" not in tables
        assert "loads" in tables
