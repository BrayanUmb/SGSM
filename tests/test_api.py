import jwt

from app import security as s
from conftest import SECRET, STRONG, auth, login, make_user

FUT = {"especialidad": "PEDIATRIA", "fecha_hora": "2026-11-10T09:00", "motivo": "control"}


# ---- required lab endpoints: login, ADMIN, USER --------------------------
def test_login_returns_jwt(app, client):
    make_user(app, "ana")
    r = login(client, "ana")
    body = r.get_json()
    assert r.status_code == 200 and body["token_type"] == "Bearer" and body["expires_in"] == 900
    claims = jwt.decode(body["access_token"], SECRET, algorithms=["HS256"],
                        audience=s.AUDIENCE, issuer=s.ISSUER)
    assert claims["role"] == "USER"


def test_login_bad_credentials_generic(app, client):
    make_user(app, "ana")
    a = login(client, "ana", "wrong")
    b = login(client, "ghost", "wrong")
    assert a.status_code == b.status_code == 401
    assert a.get_json() == b.get_json() == {"error": "Invalid credentials"}


def test_admin_endpoint_admin_ok(client, admin_headers):
    r = client.get("/api/admin/dashboard", headers=admin_headers)
    assert r.status_code == 200 and r.get_json()["usuarios"] == 1


def test_admin_endpoint_user_forbidden(client, user_headers):
    assert client.get("/api/admin/dashboard", headers=user_headers).status_code == 403
    assert client.get("/api/admin/citas", headers=user_headers).status_code == 403


def test_user_endpoint(client, user_headers, admin_headers):
    r = client.get("/api/user/profile", headers=user_headers)
    assert r.status_code == 200 and r.get_json()["username"] == "paciente1"
    assert "password_hash" not in r.get_json()
    assert client.get("/api/user/profile", headers=admin_headers).status_code == 200


def test_user_endpoint_requires_token(client):
    assert client.get("/api/user/profile").status_code == 401
    for h in ("Bearer", "Basic abc", "Bearer ", "bearer abc", "Bearer a.b.c"):
        assert client.get("/api/user/profile", headers={"Authorization": h}).status_code == 401


def test_admin_cannot_book_user_only_endpoint(client, admin_headers):
    assert client.post("/api/citas", json=FUT, headers=admin_headers).status_code == 403


def test_token_with_unknown_role_rejected(client):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    tok = jwt.encode({"sub": "1", "role": "ROOT", "iss": s.ISSUER, "aud": s.AUDIENCE,
                      "iat": now, "exp": now + timedelta(minutes=5)}, SECRET, algorithm="HS256")
    assert client.get("/api/user/profile",
                      headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_token_for_deleted_user_rejected(app, client, user_headers):
    from app.db import get_db
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM usuarios")
        db.commit()
    assert client.get("/api/user/profile", headers=user_headers).status_code == 401


# ---- register / mass assignment -----------------------------------------
def test_register_forces_user_role(client):
    r = client.post("/api/auth/register", json={"username": "nuevo", "password": STRONG})
    assert r.status_code == 201 and r.get_json()["role"] == "USER"
    r = client.post("/api/auth/register",
                    json={"username": "hack", "password": STRONG, "role": "ADMIN"})
    assert r.status_code == 400
    assert client.post("/api/auth/register", json={"username": "nuevo", "password": STRONG}
                       ).status_code == 409


def test_register_validation_and_body(client):
    assert client.post("/api/auth/register", json={"username": "x", "password": STRONG}
                       ).status_code == 400
    assert client.post("/api/auth/register", data="nojson").status_code == 400
    assert client.post("/api/auth/register", json={"username": "okname"}).status_code == 400


# ---- brute force / rate limiting ----------------------------------------
def test_login_lockout_after_5_failures(app, client):
    make_user(app, "ana")
    for _ in range(5):
        assert login(client, "ana", "bad").status_code == 401
    assert login(client, "ana", "bad").status_code == 429
    assert login(client, "ana", STRONG).status_code == 429  # even the right password
    assert login(client, "otro", "bad").status_code == 401  # other key unaffected


def test_successful_login_resets_counter(app, client):
    make_user(app, "ana")
    for _ in range(4):
        login(client, "ana", "bad")
    assert login(client, "ana", STRONG).status_code == 200
    for _ in range(5):
        assert login(client, "ana", "bad").status_code == 401


def test_sql_injection_in_login(app, client):
    make_user(app, "ana")
    r = client.post("/api/auth/login", json={"username": "' OR '1'='1", "password": "x"})
    assert r.status_code == 401


# ---- appointments / BOLA -------------------------------------------------
def test_cita_lifecycle(client, user_headers, admin_headers):
    r = client.post("/api/citas", json=FUT, headers=user_headers)
    assert r.status_code == 201
    cid = r.get_json()["id"]
    assert client.get(f"/api/citas/{cid}", headers=user_headers).status_code == 200
    assert client.get(f"/api/citas/{cid}", headers=admin_headers).status_code == 200
    lst = client.get("/api/citas?page=1&size=5", headers=user_headers).get_json()
    assert len(lst["items"]) == 1
    assert len(client.get("/api/admin/citas", headers=admin_headers).get_json()["items"]) == 1
    assert client.delete(f"/api/citas/{cid}", headers=user_headers).get_json()["estado"] == "CANCELADA"


def test_bola_other_user_cannot_read_or_cancel(app, client, user_headers):
    cid = client.post("/api/citas", json=FUT, headers=user_headers).get_json()["id"]
    make_user(app, "intruso")
    other = auth(client, "intruso")
    assert client.get(f"/api/citas/{cid}", headers=other).status_code == 404
    assert client.delete(f"/api/citas/{cid}", headers=other).status_code == 404
    assert client.get("/api/citas", headers=other).get_json()["items"] == []


def test_cita_mass_assignment_rejected(client, user_headers):
    body = {**FUT, "usuario_id": 99, "estado": "CANCELADA"}
    assert client.post("/api/citas", json=body, headers=user_headers).status_code == 400


def test_oversized_body_rejected(client):
    r = client.post("/api/auth/login", data="x" * 20000, content_type="application/json")
    assert r.status_code == 413 and r.get_json() == {"error": "Request Entity Too Large"}


# ---- misconfiguration ---------------------------------------------------
def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "max-age" in r.headers["Strict-Transport-Security"]
    assert "Server" not in r.headers


def test_404_and_405_are_json(client):
    assert client.get("/nope").get_json() == {"error": "Not Found"}
    assert client.put("/api/health").status_code == 405


def test_unexpected_error_is_generic(app, client, monkeypatch):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    monkeypatch.setattr("app.routes.services.dashboard_stats",
                        lambda db: (_ for _ in ()).throw(RuntimeError("secret path /etc")))
    make_user(app, "admin", "ADMIN")
    r = client.get("/api/admin/dashboard", headers=auth(client, "admin"))
    assert r.status_code == 500 and r.get_json() == {"error": "Internal server error"}


def test_app_refuses_weak_or_missing_secret(tmp_path):
    import pytest
    from app import create_app
    for secret in (None, "short"):
        with pytest.raises(RuntimeError):
            create_app({"JWT_SECRET": secret, "DATABASE": str(tmp_path / "x.db")})


def test_auth_error_messages(client):
    assert client.get("/api/user/profile").get_json() == {"error": "Missing bearer token"}
    bad = client.get("/api/user/profile", headers={"Authorization": "Bearer a.b.c"})
    assert bad.get_json() == {"error": "Invalid or expired token"}
