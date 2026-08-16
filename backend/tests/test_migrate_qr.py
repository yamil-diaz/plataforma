# -*- coding: utf-8 -*-
"""Pruebas de la migración FASE 2 (QR de referencia): migrate_db_qr.py.

Estrategia (convención del repositorio, ver backend/requirements-dev.txt):
- Pruebas principales con stubs de psycopg2 (sin PostgreSQL real): verifican
  que la migración se ejecuta, es idempotente, emite exactamente el DDL
  requerido y NO contiene ninguna sentencia de modificación de datos
  (INSERT/UPDATE/DELETE/TRUNCATE/DROP), por lo que los usuarios existentes
  conservan referred_by_qr_id = NULL y ninguna tabla pierde datos.
- Pruebas de integración opcionales contra un PostgreSQL REAL solo si se
  define explícitamente la variable TEST_DATABASE_URL apuntando a una BD de
  prueba dedicada. NUNCA apuntar esta variable a producción.

Estas pruebas NO tocan producción: la migración recibe una conexión simulada
y, en el modo integración, una BD de prueba local explícita.
"""
import importlib
import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# La migración exige DATABASE_URL en el entorno. Para las pruebas se usa un
# valor ficticio de prueba (nunca producción). En el modo integración real se
# requiere TEST_DATABASE_URL explícito (ver clase TestIntegracionPostgresReal).
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/qr_test")

# El stub del conftest registra 'psycopg2.extras' en sys.modules pero no lo
# expone como atributo del módulo padre. Se repara aquí para que la migración
# pueda resolver psycopg2.extras.RealDictCursor (igual que el psycopg2 real).
if not hasattr(sys.modules.get("psycopg2"), "extras"):
    sys.modules["psycopg2"].extras = sys.modules["psycopg2.extras"]

import migrate_db_qr  # noqa: E402


def _normalizar(sql):
    return " ".join(sql.strip().lower().split())


# ── Stubs de conexión ────────────────────────────────────────────────────────


class FakeCursor:
    def __init__(self):
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append(sql)


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.fixture()
def fake_connect(monkeypatch):
    """Sustituye psycopg2.connect por un stub que registra las sentencias."""
    conexiones = []
    cursor_factories = []

    def _connect(url, cursor_factory=None):
        cursor_factories.append(cursor_factory)
        conn = FakeConn()
        conexiones.append(conn)
        return conn

    monkeypatch.setattr(migrate_db_qr.psycopg2, "connect", _connect)
    monkeypatch.setattr(
        migrate_db_qr,
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/qr_test",
    )
    yield conexiones, cursor_factories


def _sentencias(fake_connect):
    migrate_db_qr.migrate()
    conexiones, _ = fake_connect
    return [_normalizar(s) for s in conexiones[0].cur.statements]


# ── Pruebas con stub (no requieren PostgreSQL) ────────────────────────────────


class TestMigracionQR:
    def test_ejecuta_una_primera_vez_sin_error(self, fake_connect):
        conexiones, _ = fake_connect
        migrate_db_qr.migrate()
        assert len(conexiones) == 1
        conn = conexiones[0]
        assert conn.commits == 1
        assert conn.rollbacks == 0
        assert conn.closed

    def test_ejecuta_una_segunda_vez_sin_error(self, fake_connect):
        conexiones, _ = fake_connect
        migrate_db_qr.migrate()
        migrate_db_qr.migrate()
        assert len(conexiones) == 2
        assert all(c.commits == 1 and c.rollbacks == 0 and c.closed for c in conexiones)
        # Idempotencia estructural: la segunda ejecución emite el mismo DDL.
        assert conexiones[0].cur.statements == conexiones[1].cur.statements

    def test_usa_real_dict_cursor(self, fake_connect):
        _, cursor_factories = fake_connect
        migrate_db_qr.migrate()
        assert cursor_factories[0] is migrate_db_qr.psycopg2.extras.RealDictCursor

    def test_crea_tabla_qr_codes(self, fake_connect):
        stmts = _sentencias(fake_connect)
        ddl = next(s for s in stmts if s.startswith("create table if not exists qr_codes"))
        assert "code varchar(32) unique not null" in ddl
        assert "name text not null" in ddl
        assert "is_active boolean not null default true" in ddl
        assert "created_at text not null" in ddl

    def test_crea_tabla_qr_visits(self, fake_connect):
        stmts = _sentencias(fake_connect)
        ddl = next(s for s in stmts if s.startswith("create table if not exists qr_visits"))
        assert "qr_id integer not null references qr_codes(id) on delete cascade" in ddl
        assert "ip text not null" in ddl
        assert "visit_date text not null" in ddl
        assert "unique(qr_id, ip, visit_date)" in ddl

    def test_users_referred_by_qr_id_existe(self, fake_connect):
        stmts = _sentencias(fake_connect)
        alter = next(
            s
            for s in stmts
            if s.startswith("alter table users add column if not exists referred_by_qr_id")
        )
        assert "references qr_codes(id) on delete set null" in alter

    def test_indice_idx_qr_visits_qr_existe(self, fake_connect):
        stmts = _sentencias(fake_connect)
        assert any(
            s == "create index if not exists idx_qr_visits_qr on qr_visits(qr_id)"
            for s in stmts
        )

    def test_indice_idx_users_referred_by_qr_existe(self, fake_connect):
        stmts = _sentencias(fake_connect)
        assert any(
            s == "create index if not exists idx_users_referred_by_qr on users(referred_by_qr_id)"
            for s in stmts
        )

    def test_qr_codes_se_crea_antes_que_la_fk_de_users(self, fake_connect):
        stmts = _sentencias(fake_connect)
        i_codes = next(i for i, s in enumerate(stmts) if s.startswith("create table if not exists qr_codes"))
        i_alter = next(
            i
            for i, s in enumerate(stmts)
            if s.startswith("alter table users add column if not exists referred_by_qr_id")
        )
        assert i_codes < i_alter

    def test_todas_las_sentencias_son_idempotentes(self, fake_connect):
        for s in _sentencias(fake_connect):
            if s.startswith("create table") or s.startswith("create index"):
                assert "if not exists" in s, s
            if s.startswith("alter table"):
                assert "add column if not exists" in s, s

    def test_no_modifica_datos_existentes(self, fake_connect):
        """La migración es solo DDL: sin INSERT/UPDATE/DELETE/TRUNCATE/DROP.

        Consecuencia: los usuarios existentes no reciben ningún
        referred_by_qr_id (permanece NULL) y ninguna tabla pierde datos."""
        stmts = _sentencias(fake_connect)
        prohibido = ("insert ", "update ", "delete ", "truncate", "drop ")
        for s in stmts:
            assert not any(s.startswith(p) for p in prohibido), (
                f"La migración no debe tocar datos existentes: {s}"
            )


# ── Integración opcional contra PostgreSQL real ──────────────────────────────

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture()
def psycopg2_real():
    """Restaura temporalmente el psycopg2 real (el conftest lo sustituye por
    un stub). Solo lo usan las pruebas de integración con TEST_DATABASE_URL."""
    claves = ("psycopg2", "psycopg2.extras", "psycopg2.errors")
    guardado = {}
    for k in claves:
        guardado[k] = sys.modules.get(k)
        sys.modules.pop(k, None)
    real = importlib.import_module("psycopg2")
    importlib.import_module("psycopg2.extras")
    importlib.import_module("psycopg2.errors")
    yield real
    for k in claves:
        sys.modules.pop(k, None)
        if guardado[k] is not None:
            sys.modules[k] = guardado[k]


@pytest.mark.skipif(
    not TEST_DB_URL,
    reason="TEST_DATABASE_URL no definida: se usan los stubs (convención del repo)",
)
class TestIntegracionPostgresReal:
    """Verifica la migración contra un PostgreSQL de prueba. NO ejecutar contra
    producción: TEST_DATABASE_URL debe apuntar a una BD de prueba dedicada."""

    def test_migracion_completa_e_idempotente(self, psycopg2_real):
        viejo_mod = migrate_db_qr.psycopg2
        vieja_url = migrate_db_qr.DATABASE_URL
        migrate_db_qr.psycopg2 = psycopg2_real
        migrate_db_qr.DATABASE_URL = TEST_DB_URL

        conn = psycopg2_real.connect(TEST_DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        def tabla_existe(nombre):
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (nombre,),
            )
            return cur.fetchone() is not None

        def columna_existe(tabla, columna):
            cur.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                (tabla, columna),
            )
            return cur.fetchone() is not None

        try:
            # Datos previos (para verificar que no se pierden)
            cur.execute("SELECT COUNT(*) FROM users")
            usuarios_antes = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at) "
                "VALUES (%s, %s, %s, 'user', 0, %s)",
                ("Test QR", "qr_preexistente@test.com", "hash", "2026-01-01T00:00:00+00:00"),
            )

            # Primera y segunda ejecución (idempotencia real)
            migrate_db_qr.migrate()
            migrate_db_qr.migrate()

            assert tabla_existe("qr_codes")
            assert tabla_existe("qr_visits")
            assert columna_existe("users", "referred_by_qr_id")

            cur.execute(
                "SELECT indexname FROM pg_indexes WHERE indexname IN ('idx_qr_visits_qr', 'idx_users_referred_by_qr')"
            )
            indices = {r[0] for r in cur.fetchall()}
            assert {"idx_qr_visits_qr", "idx_users_referred_by_qr"} <= indices

            cur.execute(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_name = 'qr_visits' AND constraint_type = 'UNIQUE'"
            )
            assert cur.fetchone() is not None, "UNIQUE(qr_id, ip, visit_date) no existe"

            # Los usuarios existentes conservan referred_by_qr_id = NULL
            cur.execute("SELECT referred_by_qr_id FROM users WHERE email = %s", ("qr_preexistente@test.com",))
            assert cur.fetchone()[0] is None

            # Las tablas existentes no pierden datos
            cur.execute("SELECT COUNT(*) FROM users")
            assert cur.fetchone()[0] >= usuarios_antes + 1

            # Semántica de la FK: visita única por (qr_id, ip, visit_date)
            cur.execute(
                "INSERT INTO qr_codes (code, name, created_at) VALUES ('QR001', 'Test', %s) RETURNING id",
                ("2026-01-01T00:00:00+00:00",),
            )
            qr_id = cur.fetchone()[0]
            for _ in range(2):
                try:
                    cur.execute(
                        "INSERT INTO qr_visits (qr_id, ip, visit_date, created_at) "
                        "VALUES (%s, %s, %s, %s)",
                        (qr_id, "127.0.0.1", "2026-01-01", "2026-01-01T00:00:00+00:00"),
                    )
                except Exception:
                    break
            cur.execute("SELECT COUNT(*) FROM qr_visits WHERE qr_id = %s", (qr_id,))
            assert cur.fetchone()[0] == 1, "La UNIQUE no deduplicó las visitas"

            # ON DELETE SET NULL: al borrar el QR, el usuario queda sin referencia
            cur.execute(
                "INSERT INTO users (name, email, hashed_password, role, rayos_balance, created_at, referred_by_qr_id) "
                "VALUES (%s, %s, %s, 'user', 0, %s, %s)",
                ("QR Usuario", "qr_usuario@test.com", "hash", "2026-01-01T00:00:00+00:00", qr_id),
            )
            cur.execute("DELETE FROM qr_codes WHERE id = %s", (qr_id,))
            cur.execute("SELECT referred_by_qr_id FROM users WHERE email = %s", ("qr_usuario@test.com",))
            assert cur.fetchone()[0] is None, "ON DELETE SET NULL no funcionó"

        finally:
            # Limpieza SOLO de la BD de prueba
            try:
                cur.execute("ALTER TABLE users DROP COLUMN IF EXISTS referred_by_qr_id")
            except Exception:
                pass
            try:
                cur.execute("DROP TABLE IF EXISTS qr_visits")
                cur.execute("DROP TABLE IF EXISTS qr_codes")
            except Exception:
                pass
            try:
                cur.execute("DELETE FROM users WHERE email IN ('qr_preexistente@test.com', 'qr_usuario@test.com')")
            except Exception:
                pass
            conn.close()
            migrate_db_qr.psycopg2 = viejo_mod
            migrate_db_qr.DATABASE_URL = vieja_url