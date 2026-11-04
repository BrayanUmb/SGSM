from datetime import datetime

import pytest

from app.errors import ApiError
from app import validators as v

NOW = datetime(2026, 11, 3, 10, 0, 0)


def fails(fn, *args, status=400):
    with pytest.raises(ApiError) as exc:
        fn(*args)
    assert exc.value.status == status
    return exc.value.message


@pytest.mark.parametrize("name", ["abc", "a" * 30, "user.name-1_x", "ABC123"])
def test_username_ok(name):
    assert v.validate_username(name) == name


@pytest.mark.parametrize("name", ["ab", "a" * 31, "bad name", "a;b", "", None, 5, "x'--"])
def test_username_bad(name):
    fails(v.validate_username, name)


def test_password_ok_boundaries():
    assert v.validate_password("Abcdefgh1j") == "Abcdefgh1j"  # exactly 10
    assert v.validate_password("Aa1" + "x" * 125)  # exactly 128


@pytest.mark.parametrize("pw", [
    "Abcdefgh1", "A" * 129 + "a1", "abcdefghij1", "ABCDEFGHIJ1", "Abcdefghijk", None, 12345678901,
])
def test_password_bad(pw):
    fails(v.validate_password, pw)


def test_password_messages_differ():
    assert "between" in fails(v.validate_password, "short")
    assert "include" in fails(v.validate_password, "alllowercase1x")


def test_motivo():
    assert v.validate_motivo("  dolor   ") == "dolor"
    assert v.validate_motivo("12345") == "12345"
    assert len(v.validate_motivo("x" * 200)) == 200
    fails(v.validate_motivo, "1234")
    fails(v.validate_motivo, "  1234  ")
    fails(v.validate_motivo, "x" * 201)
    fails(v.validate_motivo, 123)


def test_especialidad():
    for e in v.ESPECIALIDADES:
        assert v.validate_especialidad(e) == e
    fails(v.validate_especialidad, "BRUJERIA")
    fails(v.validate_especialidad, None)


def test_fecha_hora_ok():
    assert v.validate_fecha_hora("2026-11-04T08:00", NOW) == "2026-11-04T08:00"
    assert v.validate_fecha_hora("2026-11-04T17:30:00", NOW) == "2026-11-04T17:30"
    assert v.validate_fecha_hora("2026-11-04T09:00+00:00", NOW) == "2026-11-04T09:00"


@pytest.mark.parametrize("value", [
    "2026-11-03T10:00",   # equals now -> not future
    "2026-11-03T09:00",   # past
    "2027-03-01T09:00",   # beyond 90 days
    "2026-11-04T09:15",   # bad minute
    "2026-11-04T09:00:30",  # seconds
    "2026-11-04T07:30",   # before opening
    "2026-11-04T18:00",   # closing
    "not-a-date", 123, None,
])
def test_fecha_hora_bad(value):
    fails(v.validate_fecha_hora, value, NOW)


def test_fecha_hora_limit_90_days():
    from datetime import timedelta
    edge = (NOW + timedelta(days=90)).replace(hour=10, minute=0)
    # NOW + 90 days at 10:00 equals the limit -> allowed
    assert v.validate_fecha_hora(edge.isoformat(), NOW)
    fails(v.validate_fecha_hora, (edge + timedelta(minutes=30)).isoformat(), NOW)


def test_fecha_hora_messages():
    assert "future" in fails(v.validate_fecha_hora, "2026-11-03T09:00", NOW)
    assert "far" in fails(v.validate_fecha_hora, "2027-03-01T09:00", NOW)
    assert ":00" in fails(v.validate_fecha_hora, "2026-11-04T09:15", NOW)
    assert "office" in fails(v.validate_fecha_hora, "2026-11-04T07:30", NOW)


def test_pick_allowed():
    assert v.pick_allowed({"a": 1, "b": 2}, ("a", "b")) == {"a": 1, "b": 2}
    assert "role" in fails(v.pick_allowed, {"a": 1, "b": 2, "role": "ADMIN"}, ("a", "b"))
    assert "Missing" in fails(v.pick_allowed, {"a": 1}, ("a", "b"))
    assert "object" in fails(v.pick_allowed, [1], ("a",))


def test_clamp_page():
    assert v.clamp_page(None, None) == (1, 10)
    assert v.clamp_page("3", "20") == (3, 20)
    assert v.clamp_page("0", "0") == (1, 1)
    assert v.clamp_page("-5", "-5") == (1, 1)
    assert v.clamp_page("1", "50") == (1, 50)
    assert v.clamp_page("1", "51") == (1, 50)
    assert v.clamp_page("x", "y") == (1, 10)
    assert v.clamp_page(2, 1) == (2, 1)


def test_password_129_chars_rejected():
    fails(v.validate_password, "Aa1" + "x" * 126)  # 129 chars: one above the limit


def test_error_messages_are_stable():
    assert "username" in fails(v.validate_username, "x").lower()
    assert fails(v.validate_especialidad, "ZZ") == "Unknown especialidad"
    assert fails(v.validate_fecha_hora, 5, NOW) == "Invalid fecha_hora"
    assert fails(v.validate_fecha_hora, "zz", NOW) == "fecha_hora must be ISO-8601"
    assert fails(v.validate_motivo, 5) == "Invalid motivo"
    assert fails(v.validate_motivo, "x") == "Motivo must have between 5 and 200 characters"
    assert fails(v.pick_allowed, {"b": 1, "a": 1, "z": 1, "y": 1}, ("a", "b")) \
        == "Unexpected fields: y, z"
    assert fails(v.pick_allowed, {}, ("a", "b")) == "Missing fields: a, b"
