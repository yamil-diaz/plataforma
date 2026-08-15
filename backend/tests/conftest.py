import os
import sys
import types

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Stub de psycopg2: las pruebas no requieren PostgreSQL real ──────────────
if "psycopg2" not in sys.modules:
    errors_mod = types.ModuleType("psycopg2.errors")

    class UniqueViolation(Exception):
        pass

    errors_mod.UniqueViolation = UniqueViolation

    psycopg2_mod = types.ModuleType("psycopg2")
    psycopg2_mod.errors = errors_mod

    def _no_connect(*args, **kwargs):
        raise RuntimeError("psycopg2 stub: las pruebas no usan una BD real")

    psycopg2_mod.connect = _no_connect
    sys.modules["psycopg2"] = psycopg2_mod
    sys.modules["psycopg2.errors"] = errors_mod

    extras_mod = types.ModuleType("psycopg2.extras")
    extras_mod.RealDictCursor = object
    sys.modules["psycopg2.extras"] = extras_mod

# ── Módulo `database` simulado: init_db no-op y get_db → FakeDb ─────────────
from support import FakeDb

database_mod = types.ModuleType("database")
database_mod.init_db = lambda: None
database_mod.get_db = lambda: None  # se sobreescribe por el fixture
sys.modules["database"] = database_mod

import server  # noqa: E402  (tras los stubs; init_db() es no-op)

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def fake_db():
    db = FakeDb()
    server.get_db = lambda: db
    return db


@pytest.fixture()
def client(fake_db):
    return TestClient(server.app)


def _auth_token(user_id, email):
    return server.create_access_token(user_id, email)


@pytest.fixture()
def as_admin(client):
    client.cookies.set("access_token", _auth_token(1, "admin@test.com"))
    return client


@pytest.fixture()
def as_uploader(client):
    client.cookies.set("access_token", _auth_token(2, "uploader@test.com"))
    return client


@pytest.fixture()
def as_third_party(client):
    client.cookies.set("access_token", _auth_token(3, "tercero@test.com"))
    return client