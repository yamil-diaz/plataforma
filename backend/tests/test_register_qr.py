"""FASE 4: asociación del registro al QR de referencia (users.referred_by_qr_id).

El backend recibe el campo opcional `ref`, lo vuelve a validar (nunca confía
en el frontend) y, solo si el QR existe y está activo, guarda su id interno en
users.referred_by_qr_id dentro de la misma transacción de creación del usuario.
Un ref inválido/inexistente/inactivo jamás impide el registro: el usuario se
crea igual con referred_by_qr_id = NULL. El role y los Rayos los fija siempre
el servidor.
"""

import pytest

API = "/api/register"


def _registro(email, **extra):
    payload = {"name": "Ana Test", "email": email, "password": "claveSegura123"}
    payload.update(extra)
    return payload


def _usuario(fake_db, email):
    return next(
        (u for u in fake_db.state["users"].values() if u.get("email") == email),
        None,
    )


# A. registro sin ref -> referred_by_qr_id = NULL
def test_A_registro_sin_ref_deja_referred_by_qr_id_null(client, fake_db):
    r = client.post(API, json=_registro("sinref@test.com"))
    assert r.status_code == 200
    u = _usuario(fake_db, "sinref@test.com")
    assert u is not None
    assert u["referred_by_qr_id"] is None
    assert u["role"] == "user"


# B. registro con QR001 (existe y activo) -> referred_by_qr_id = id de QR001
def test_B_registro_con_qr_valido_activo_asocia_el_id_interno(client, fake_db):
    r = client.post(API, json=_registro("qr001@test.com", ref="QR001"))
    assert r.status_code == 200
    u = _usuario(fake_db, "qr001@test.com")
    assert u["referred_by_qr_id"] == 1
    assert u["role"] == "user"


# C. QR inexistente -> usuario creado, referred_by_qr_id = NULL
def test_C_qr_inexistente_crea_usuario_sin_asociacion(client, fake_db):
    r = client.post(API, json=_registro("fake@test.com", ref="FAKE999"))
    assert r.status_code == 200
    u = _usuario(fake_db, "fake@test.com")
    assert u is not None
    assert u["referred_by_qr_id"] is None


# D. QR inactivo (existe con is_active = FALSE) -> usuario creado, NULL
def test_D_qr_inactivo_crea_usuario_sin_asociacion(client, fake_db):
    r = client.post(API, json=_registro("inactivo@test.com", ref="QR002"))
    assert r.status_code == 200
    u = _usuario(fake_db, "inactivo@test.com")
    assert u is not None
    assert u["referred_by_qr_id"] is None


# E. formato inválido (<script>) -> usuario creado, NULL
def test_E_formato_invalido_script_crea_usuario_sin_asociacion(client, fake_db):
    r = client.post(API, json=_registro("script@test.com", ref="<script>"))
    assert r.status_code == 200
    u = _usuario(fake_db, "script@test.com")
    assert u is not None
    assert u["referred_by_qr_id"] is None


# F. formato >32 caracteres -> usuario creado, NULL
def test_F_ref_mayor_a_32_caracteres_crea_usuario_sin_asociacion(client, fake_db):
    r = client.post(API, json=_registro("largo@test.com", ref="Q" * 33))
    assert r.status_code == 200
    u = _usuario(fake_db, "largo@test.com")
    assert u is not None
    assert u["referred_by_qr_id"] is None


# G. role: el ref (ni ningún campo extra) puede cambiar role / Rayos
def test_G_ref_valido_no_cambia_role_ni_rayos_aunque_se_intente(client, fake_db):
    r = client.post(
        API,
        json=_registro("rol@test.com", ref="QR001", role="admin", rayos_balance=99999),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "user"
    assert r.json()["rayos_balance"] == 100
    u = _usuario(fake_db, "rol@test.com")
    assert u["role"] == "user"
    assert u["referred_by_qr_id"] == 1  # el ref válido sí asocia, el resto se ignora


# H. registro normal: el flujo existente no se rompe
def test_H_registro_normal_sigue_funcionando(client, fake_db):
    r = client.post(API, json=_registro("normal@test.com"))
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "user"
    assert data["rayos_balance"] == 100
    assert _usuario(fake_db, "normal@test.com") is not None


# I. email duplicado mantiene el comportamiento actual (400)
def test_I_email_duplicado_mantiene_comportamiento(client, fake_db):
    email = "dup@test.com"
    assert client.post(API, json=_registro(email)).status_code == 200
    r = client.post(API, json=_registro(email, ref="QR001"))
    assert r.status_code == 400
    assert "ya está registrado" in r.json()["detail"]


# J. registration_reward sigue funcionando exactamente igual (100 Rayos + txn)
def test_J_registration_reward_sigue_funcionando(client, fake_db):
    r = client.post(API, json=_registro("recompensa@test.com", ref="QR001"))
    assert r.status_code == 200
    assert r.json()["rayos_balance"] == 100
    txns = [
        params
        for query, params in fake_db.state["log"]
        if query.strip().lower().startswith("insert into rayos_transactions")
    ]
    assert any(params[2] == "registration_reward" for params in txns)
    assert _usuario(fake_db, "recompensa@test.com")["referred_by_qr_id"] == 1


# La asociación es atómica: el ref nunca se guarda como texto en users
def test_el_ref_se_guarda_como_id_interno_no_como_texto(client, fake_db):
    r = client.post(API, json=_registro("texto@test.com", ref="QR001"))
    assert r.status_code == 200
    u = _usuario(fake_db, "texto@test.com")
    assert u["referred_by_qr_id"] == 1
    assert u["referred_by_qr_id"] != "QR001"