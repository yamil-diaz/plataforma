"""FASE 5: tracking de visitas de QR (POST /api/qr/{code}/visit).

Solo contabiliza visitas de QRs que existen y están activos. Deduplicación
por UNIQUE(qr_id, ip, visit_date): 1 IP + 1 QR + 1 día = 1 visita. El endpoint
es exclusivamente tracking: no modifica users, no entrega Rayos, no crea QRs,
no usa SQL construido con f-strings (todo parametrizado).
"""

import copy

from starlette.testclient import TestClient

import server

API = "/api/qr/{code}/visit"


def _visitar(client, code):
    return client.post(API.format(code=code))


# A. QR válido -> visita creada
def test_A_qr_valido_crea_visita(client, fake_db):
    r = _visitar(client, "QR001")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "counted": True}
    assert len(fake_db.state["qr_visits"]) == 1
    qr_id, ip, visit_date, created_at = fake_db.state["qr_visits"][0]
    assert qr_id == 1  # id interno de QR001
    assert ip == "testclient"
    assert visit_date.isdigit() or "-" in visit_date  # fecha de día
    assert created_at  # timestamp completo


# B. QR inexistente -> ninguna visita creada
def test_B_qr_inexistente_no_crea_visita(client, fake_db):
    r = _visitar(client, "FAKE999")
    assert r.status_code == 404
    assert fake_db.state["qr_visits"] == []


# C. QR inactivo -> ninguna visita creada
def test_C_qr_inactivo_no_crea_visita(client, fake_db):
    r = _visitar(client, "QR002")
    assert r.status_code == 404
    assert fake_db.state["qr_visits"] == []


# D. formato inválido -> ninguna visita
def test_D_formato_invalido_no_crea_visita(client, fake_db):
    r = _visitar(client, "%3Cscript%3E")
    assert r.status_code == 404
    assert fake_db.state["qr_visits"] == []


# E. misma IP + mismo QR + mismo día -> solo 1 registro
def test_E_misma_ip_mismo_qr_mismo_dia_solo_una_visita(client, fake_db):
    assert _visitar(client, "QR001").json()["counted"] is True
    r2 = _visitar(client, "QR001")
    assert r2.status_code == 200
    assert r2.json()["counted"] is False  # deduplicado
    assert len(fake_db.state["qr_visits"]) == 1


# F. misma IP + QR diferente -> 1 visita para cada QR
def test_F_misma_ip_qr_diferente_visitas_independientes(client, fake_db):
    assert _visitar(client, "QR001").json()["counted"] is True
    assert _visitar(client, "QR003").json()["counted"] is True
    assert len(fake_db.state["qr_visits"]) == 2
    qrs = {v[0] for v in fake_db.state["qr_visits"]}
    assert qrs == {1, 3}


# G. IP diferente + mismo QR -> visitas independientes
def test_G_ip_diferente_mismo_qr_visitas_independientes(client, fake_db):
    assert _visitar(client, "QR001").json()["counted"] is True
    otro = TestClient(server.app, client=("10.20.30.40", 12345))
    assert _visitar(otro, "QR001").json()["counted"] is True
    assert len(fake_db.state["qr_visits"]) == 2
    ips = {v[1] for v in fake_db.state["qr_visits"]}
    assert ips == {"testclient", "10.20.30.40"}


# H. el endpoint NO modifica users
def test_H_no_modifica_users(client, fake_db):
    usuarios_antes = copy.deepcopy(fake_db.state["users"])
    _visitar(client, "QR001")
    assert fake_db.state["users"] == usuarios_antes


# I. el endpoint NO entrega Rayos
def test_I_no_entrega_rayos(client, fake_db):
    _visitar(client, "QR001")
    assert fake_db.state["rayos_transactions"] == []
    assert all(u["rayos_balance"] == 100 for u in fake_db.state["users"].values())


# J. SQL parametrizado: el código nunca aparece interpolado en la query
def test_J_sql_parametrizado(client, fake_db):
    _visitar(client, "QR001")
    _visitar(client, "QR003")
    for query, params in fake_db.state["log"]:
        # el valor del código va en params, nunca interpolado en el SQL
        assert "QR001" not in query and "QR003" not in query
    codes = [p for _, p in fake_db.state["log"] if p and p[0] in ("QR001", "QR003")]
    assert len(codes) == 2


# K. registro normal sigue funcionando
def test_K_registro_normal_sigue_funcionando(client, fake_db):
    r = client.post("/api/register", json={
        "name": "Normal", "email": "normal5@test.com", "password": "claveSegura123"
    })
    assert r.status_code == 200
    assert r.json()["role"] == "user"


# Estadísticas futuras: consultas de conteo ya soportadas por el esquema
def test_visitas_por_qr_consultables(client, fake_db):
    _visitar(client, "QR001")
    _visitar(client, "QR001")
    _visitar(client, "QR003")
    cursor = fake_db.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM qr_visits WHERE qr_id = %s", (1,))
    assert cursor.fetchone()["cnt"] == 1
    cursor.execute("SELECT COUNT(*) AS cnt FROM qr_visits WHERE qr_id = %s", (3,))
    assert cursor.fetchone()["cnt"] == 1


def test_registros_por_qr_consultables(client, fake_db):
    _visitar(client, "QR001")
    client.post("/api/register", json={
        "name": "Con QR", "email": "conqr@test.com", "password": "claveSegura123", "ref": "QR001"
    })
    client.post("/api/register", json={
        "name": "Con QR 2", "email": "conqr2@test.com", "password": "claveSegura123", "ref": "QR001"
    })
    cursor = fake_db.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE referred_by_qr_id = %s", (1,))
    assert cursor.fetchone()["cnt"] == 2
    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE referred_by_qr_id = %s", (3,))
    assert cursor.fetchone()["cnt"] == 0