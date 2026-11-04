from datetime import datetime

import pytest

from app import services as sv
from app.errors import ApiError
from conftest import NOW, STRONG

FUT = "2026-11-10T09:00"


def u(db, name="ana", role="USER"):
    return sv.create_user(db, name, STRONG, role, NOW)


def test_create_user_normalizes_and_hides_hash(db):
    row = u(db, "Ana")
    assert row["username"] == "ana" and row["role"] == "USER"
    assert row["created_at"] == NOW.isoformat()
    assert set(sv.public_user(row)) == {"id", "username", "role"}


def test_create_user_duplicate(db):
    u(db)
    with pytest.raises(ApiError) as e:
        u(db, "ANA")
    assert e.value.status == 409


def test_create_user_default_role_user(db):
    row = sv.create_user(db, "bob.x", STRONG)
    assert row["role"] == "USER"


def test_authenticate(db):
    u(db)
    assert sv.authenticate(db, "ANA", STRONG)["username"] == "ana"
    for name, pw in (("ana", "bad"), ("ghost", STRONG), (None, STRONG), ("ana", None), ("ana", 5)):
        with pytest.raises(ApiError) as e:
            sv.authenticate(db, name, pw)
        assert e.value.status == 401 and e.value.message == "Invalid credentials"


def test_create_cita_ok(db):
    uid = u(db)["id"]
    row = sv.create_cita(db, uid, "PEDIATRIA", FUT, "  control  ", NOW)
    assert row["estado"] == "ACTIVA" and row["motivo"] == "control"
    assert row["fecha_hora"] == FUT and row["usuario_id"] == uid
    assert set(sv.public_cita(row)) == {
        "id", "usuario_id", "especialidad", "fecha_hora", "motivo", "estado"}


def test_double_booking_conflict_and_release(db):
    a, b = u(db, "ana")["id"], u(db, "beto")["id"]
    first = sv.create_cita(db, a, "PEDIATRIA", FUT, "control", NOW)
    with pytest.raises(ApiError) as e:
        sv.create_cita(db, b, "PEDIATRIA", FUT, "control", NOW)
    assert e.value.status == 409
    sv.create_cita(db, b, "CARDIOLOGIA", FUT, "control", NOW)  # other specialty ok
    sv.cancel_cita(db, first["id"], {"id": a, "role": "USER"})
    assert sv.create_cita(db, b, "PEDIATRIA", FUT, "control", NOW)["id"]


def test_active_limit_boundary(db):
    uid = u(db)["id"]
    for h in ("09:00", "09:30", "10:00"):
        sv.create_cita(db, uid, "PEDIATRIA", f"2026-11-10T{h}", "control", NOW)
    with pytest.raises(ApiError) as e:
        sv.create_cita(db, uid, "PEDIATRIA", "2026-11-10T10:30", "control", NOW)
    assert e.value.status == 429


def test_cancelled_do_not_count_toward_limit(db):
    uid = u(db)["id"]
    ids = [sv.create_cita(db, uid, "PEDIATRIA", f"2026-11-10T{h}", "control", NOW)["id"]
           for h in ("09:00", "09:30", "10:00")]
    sv.cancel_cita(db, ids[0], {"id": uid, "role": "USER"})
    assert sv.create_cita(db, uid, "PEDIATRIA", "2026-11-10T10:30", "control", NOW)


def test_validation_errors_propagate(db):
    uid = u(db)["id"]
    with pytest.raises(ApiError):
        sv.create_cita(db, uid, "NOPE", FUT, "control", NOW)
    with pytest.raises(ApiError):
        sv.create_cita(db, uid, "PEDIATRIA", "2020-01-01T09:00", "control", NOW)
    with pytest.raises(ApiError):
        sv.create_cita(db, uid, "PEDIATRIA", FUT, "no", NOW)


def test_list_scoping_and_pagination(db):
    a, b = u(db, "ana")["id"], u(db, "beto")["id"]
    for h in ("09:00", "09:30", "10:00"):
        sv.create_cita(db, a, "PEDIATRIA", f"2026-11-10T{h}", "control", NOW)
    sv.create_cita(db, b, "CARDIOLOGIA", FUT, "control", NOW)
    mine = sv.list_citas(db, a, 1, 2)
    assert mine["page"] == 1 and mine["size"] == 2 and len(mine["items"]) == 2
    assert [c["fecha_hora"] for c in mine["items"]] == ["2026-11-10T09:00", "2026-11-10T09:30"]
    page2 = sv.list_citas(db, a, 2, 2)
    assert [c["fecha_hora"] for c in page2["items"]] == ["2026-11-10T10:00"]
    assert all(c["usuario_id"] == a for c in sv.list_citas(db, a, 1, 50)["items"])
    assert len(sv.list_all_citas(db, 1, 50)["items"]) == 4
    assert len(sv.list_all_citas(db, 2, 3)["items"]) == 1
    assert sv.list_all_citas(db, 1, 1000)["size"] == 50


def test_get_cita_bola(db):
    a, b = u(db, "ana")["id"], u(db, "beto")["id"]
    adm = u(db, "root", "ADMIN")["id"]
    cid = sv.create_cita(db, a, "PEDIATRIA", FUT, "control", NOW)["id"]
    assert sv.get_cita(db, cid, {"id": a, "role": "USER"})["id"] == cid
    assert sv.get_cita(db, cid, {"id": adm, "role": "ADMIN"})["id"] == cid
    for who in ({"id": b, "role": "USER"},):
        with pytest.raises(ApiError) as e:
            sv.get_cita(db, cid, who)
        assert e.value.status == 404
    with pytest.raises(ApiError) as e:
        sv.get_cita(db, 9999, {"id": a, "role": "USER"})
    assert e.value.status == 404


def test_cancel_twice(db):
    a = u(db)["id"]
    cid = sv.create_cita(db, a, "PEDIATRIA", FUT, "control", NOW)["id"]
    me = {"id": a, "role": "USER"}
    assert sv.cancel_cita(db, cid, me)["estado"] == "CANCELADA"
    with pytest.raises(ApiError) as e:
        sv.cancel_cita(db, cid, me)
    assert e.value.status == 409


def test_dashboard_stats(db):
    a = u(db)["id"]
    c1 = sv.create_cita(db, a, "PEDIATRIA", FUT, "control", NOW)["id"]
    sv.create_cita(db, a, "CARDIOLOGIA", FUT, "control", NOW)
    sv.cancel_cita(db, c1, {"id": a, "role": "USER"})
    assert sv.dashboard_stats(db) == {"usuarios": 1, "citas_activas": 1, "citas_canceladas": 1}


def test_service_error_messages(db):
    uid = u(db)["id"]
    with pytest.raises(ApiError, match="^Username already exists$"):
        u(db)
    sv.create_cita(db, uid, "PEDIATRIA", FUT, "control", NOW)
    other = u(db, "beto")["id"]
    with pytest.raises(ApiError, match="^Slot already taken$"):
        sv.create_cita(db, other, "PEDIATRIA", FUT, "control", NOW)
    with pytest.raises(ApiError, match="^Appointment not found$"):
        sv.get_cita(db, 12345, {"id": uid, "role": "USER"})
    cid = sv.create_cita(db, uid, "CARDIOLOGIA", FUT, "control", NOW)["id"]
    sv.cancel_cita(db, cid, {"id": uid, "role": "USER"})
    with pytest.raises(ApiError, match="^Appointment already cancelled$"):
        sv.cancel_cita(db, cid, {"id": uid, "role": "USER"})
    for h in ("10:00", "10:30"):
        sv.create_cita(db, uid, "ODONTOLOGIA", f"2026-11-12T{h}", "control", NOW)
    with pytest.raises(ApiError, match="^Active appointments limit reached$"):
        sv.create_cita(db, uid, "ODONTOLOGIA", "2026-11-12T11:30", "control", NOW)
