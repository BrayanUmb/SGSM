from datetime import datetime

import pytest

from app import create_app
from app.db import get_db
from app.services import create_user

SECRET = "test-secret-key-with-more-than-32-chars!!"
NOW = datetime(2026, 11, 3, 10, 0, 0)
STRONG = "Passw0rdSegura"


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        "JWT_SECRET": SECRET,
        "CLOCK": lambda: NOW,
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield get_db()


def make_user(app, username, role="USER", password=STRONG):
    with app.app_context():
        create_user(get_db(), username, password, role, NOW)


def login(client, username, password=STRONG):
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    return resp


def auth(client, username, password=STRONG):
    token = login(client, username, password).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(app, client):
    make_user(app, "paciente1")
    return auth(client, "paciente1")


@pytest.fixture
def admin_headers(app, client):
    make_user(app, "admin", "ADMIN")
    return auth(client, "admin")
