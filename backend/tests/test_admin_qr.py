"""FASE 6: panel administrativo de códigos QR.

Endpoints:
- GET   /api/admin/qr-codes          (listar QR con estadísticas)
- POST  /api/admin/qr-codes          (crear QR)
- PATCH /api/admin/qr-codes/{qr_id}  (activar/desactivar QR)

Todos exigen el mismo patrón administrativo existente (get_current_user +
check de role admin): usuario normal y no autenticado reciben 403/401. SQL
siempre parametrizado, sin interpolación. El body no acepta campos ajenos
(role, is_active indebido, etc.). Se verifica que desactivar un QR detiene
nuevas visitas y asociaciones de registro, conservando los datos históricos.
"""

import server

API = "/api/admin/qr-codes"


def _crear(client, code, name="Volante principal"):
    return client.post(API, json={"code": code, "name": name})


def _registrar(client, email, ref=None):
    body = {"name": "Nuevo", "email": email, "password": "claveSegura123"}
    if ref:
        body["ref"] = ref
    return client.post("/api/register", json=body)


# A. Admin puede listar QR
def test_A_admin_puede_listar_qr(as_admin):
    r = as_admin.get(API)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    codes = [qr["code"] for qr in data]
    assert "QR001" in codes and "QR002" in codes and "QR003" in codes
    qr001 = next(qr for qr in data if qr["code"] == "QR001")
    assert qr001["is_active"] is True
    assert qr001["registration_url"] == "/register?ref=QR001"
    for campo in ("id", "code", "name", "is_active", "created_at",
                  "visits_count", "registrations_count", "registration_url"):
        assert campo in qr001


# B. Usuario normal no puede listar QR
def test_B_usuario_normal_no_puede_listar(as_uploader):
    assert as_uploader.get(API).status_code == 403


# C. Usuario no autenticado no puede listar QR
def test_C_no_autenticado_no_puede_listar(client):
    assert client.get(API).status_code == 401


# D. Admin puede crear QR válido
def test_D_admin_puede_crear_qr_valido(as_admin, fake_db):
    r = _crear(as_admin, "QRX1", "Volante principal")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "QRX1"
    assert body["name"] == "Volante principal"
    assert body["is_active"] is True
    assert body["created_at"]
    nuevo = fake_db.state["qr_codes"][body["id"]]
    assert nuevo["code"] == "QRX1"
    assert nuevo["name"] == "Volante principal"
    assert nuevo["is_active"] is True
    assert nuevo["created_at"]


# E. Código inválido es rechazado
def test_E_codigo_invalido_rechazado(as_admin, fake_db):
    r = _crear(as_admin, "QR.001")
    assert r.status_code == 400
    assert not any(qr["code"] == "QR.001" for qr in fake_db.state["qr_codes"].values())


# F. Código vacío es rechazado
def test_F_codigo_vacio_rechazado(as_admin, fake_db):
    r = _crear(as_admin, "   ")
    assert r.status_code == 400
    assert len(fake_db.state["qr_codes"]) == 3


# G. Código > 32 caracteres es rechazado
def test_G_codigo_largo_rechazado(as_admin, fake_db):
    r = _crear(as_admin, "X" * 33)
    assert r.status_code == 400
    assert len(fake_db.state["qr_codes"]) == 3


# H. Caracteres inválidos son rechazados
def test_H_caracteres_invalidos_rechazados(as_admin, fake_db):
    r = _crear(as_admin, "QR<001>")
    assert r.status_code == 400
    assert len(fake_db.state["qr_codes"]) == 3


# I. QR duplicado es rechazado
def test_I_qr_duplicado_rechazado(as_admin, fake_db):
    r = _crear(as_admin, "QR001")
    assert r.status_code == 400
    assert len(fake_db.state["qr_codes"]) == 3


# J. Admin puede desactivar QR
def test_J_admin_puede_desactivar(as_admin, fake_db):
    r = as_admin.patch(f"{API}/1", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    assert fake_db.state["qr_codes"][1]["is_active"] is False


# K. Admin puede reactivar QR
def test_K_admin_puede_reactivar(as_admin, fake_db):
    r = as_admin.patch(f"{API}/2", json={"is_active": True})
    assert r.status_code == 200
    assert fake_db.state["qr_codes"][2]["is_active"] is True


# L. QR inexistente devuelve error apropiado
def test_L_qr_inexistente_error(as_admin):
    r = as_admin.patch(f"{API}/9999", json={"is_active": False})
    assert r.status_code == 404


# M. Las visitas se cuentan correctamente
def test_M_visitas_cuentan_correctamente(as_admin):
    as_admin.post("/api/qr/QR001/visit")
    as_admin.post("/api/qr/QR001/visit")  # misma IP + mismo día -> deduplicada
    as_admin.post("/api/qr/QR003/visit")
    data = as_admin.get(API).json()
    qr001 = next(qr for qr in data if qr["code"] == "QR001")
    qr002 = next(qr for qr in data if qr["code"] == "QR002")
    qr003 = next(qr for qr in data if qr["code"] == "QR003")
    assert qr001["visits_count"] == 1
    assert qr003["visits_count"] == 1
    assert qr002["visits_count"] == 0


# N. Los registros asociados se cuentan correctamente
def test_N_registros_asociados_cuentan(as_admin, fake_db):
    # register sobrescribe la cookie del cliente con el token del nuevo usuario;
    # por eso registramos con un TestClient aparte y listamos con el admin
    from starlette.testclient import TestClient
    registrar = TestClient(server.app)
    _registrar(registrar, "r1@test.com", ref="QR001")
    _registrar(registrar, "r2@test.com", ref="QR001")
    data = as_admin.get(API).json()
    qr001 = next(qr for qr in data if qr["code"] == "QR001")
    qr003 = next(qr for qr in data if qr["code"] == "QR003")
    assert qr001["registrations_count"] == 2
    assert qr003["registrations_count"] == 0


# O. Desactivar QR NO elimina visitas históricas
def test_O_desactivar_no_elimina_visitas_historicas(as_admin, fake_db):
    as_admin.post("/api/qr/QR001/visit")
    as_admin.patch(f"{API}/1", json={"is_active": False})
    assert len(fake_db.state["qr_visits"]) == 1


# P. Desactivar QR NO elimina usuarios históricos
def test_P_desactivar_no_elimina_usuarios_historicos(as_admin, fake_db):
    _registrar(as_admin, "historico@test.com", ref="QR001")
    as_admin.patch(f"{API}/1", json={"is_active": False})
    assert any(u.get("email") == "historico@test.com" for u in fake_db.state["users"].values())


# Q. El QR desactivado no acepta nuevas visitas
def test_Q_desactivado_no_acepta_nuevas_visitas(as_admin, fake_db):
    as_admin.patch(f"{API}/1", json={"is_active": False})
    r = as_admin.post("/api/qr/QR001/visit")
    assert r.status_code == 404
    assert fake_db.state["qr_visits"] == []


# R. El QR desactivado no asocia nuevos registros
def test_R_desactivado_no_asocia_nuevos_registros(as_admin, fake_db):
    as_admin.patch(f"{API}/1", json={"is_active": False})
    _registrar(as_admin, "post@test.com", ref="QR001")
    usuario = next(u for u in fake_db.state["users"].values() if u.get("email") == "post@test.com")
    assert usuario["referred_by_qr_id"] is None


# S. Reactivar QR permite nuevamente visitas/registros
def test_S_reactivar_permite_visitas_y_registros(as_admin, fake_db):
    as_admin.patch(f"{API}/1", json={"is_active": False})
    as_admin.patch(f"{API}/1", json={"is_active": True})
    r = as_admin.post("/api/qr/QR001/visit")
    assert r.status_code == 200
    assert r.json()["counted"] is True
    _registrar(as_admin, "reactivado@test.com", ref="QR001")
    usuario = next(u for u in fake_db.state["users"].values() if u.get("email") == "reactivado@test.com")
    assert usuario["referred_by_qr_id"] == 1


# T. Las consultas usan parámetros y no interpolación SQL
def test_T_sql_parametrizado_sin_interpolacion(as_admin, fake_db):
    _crear(as_admin, "QRTEST", "Nombre parametrizado")
    as_admin.patch(f"{API}/1", json={"is_active": False})
    as_admin.get(API)
    for query, params in fake_db.state["log"]:
        assert "QRTEST" not in query
        assert "Nombre parametrizado" not in query
    assert any(p and "QRTEST" in p for _, p in fake_db.state["log"])


# U. Usuario normal no puede crear QR
def test_U_usuario_normal_no_puede_crear(as_uploader, fake_db):
    r = _crear(as_uploader, "QRUP")
    assert r.status_code == 403
    assert len(fake_db.state["qr_codes"]) == 3


# V. Usuario normal no puede activar/desactivar QR
def test_V_usuario_normal_no_puede_activar_desactivar(as_uploader, fake_db):
    r = as_uploader.patch(f"{API}/1", json={"is_active": False})
    assert r.status_code == 403
    assert fake_db.state["qr_codes"][1]["is_active"] is True


# W. Los campos no permitidos del body no pueden elevar privilegios
def test_W_campos_no_permitidos_no_elevan_privilegios(as_admin, fake_db):
    # role en el body de creación -> rechazado (extra="forbid")
    r = as_admin.post(API, json={"code": "QRW1", "name": "W", "role": "admin"})
    assert r.status_code == 422
    assert not any(qr["code"] == "QRW1" for qr in fake_db.state["qr_codes"].values())
    # is_active en el body de creación no permite crearlo inactivo
    r = as_admin.post(API, json={"code": "QRW2", "name": "W", "is_active": False})
    assert r.status_code == 422
    assert not any(qr["code"] == "QRW2" for qr in fake_db.state["qr_codes"].values())
    # campos extra en PATCH -> rechazados, el QR no cambia
    r = as_admin.patch(f"{API}/1", json={"is_active": False, "role": "admin"})
    assert r.status_code == 422
    assert fake_db.state["qr_codes"][1]["is_active"] is True


# X. Nombre vacío es rechazado
def test_X_nombre_vacio_rechazado(as_admin, fake_db):
    r = _crear(as_admin, "QRN", "   ")
    assert r.status_code == 400
    assert not any(qr["code"] == "QRN" for qr in fake_db.state["qr_codes"].values())


# Y. Nombre demasiado largo es rechazado
def test_Y_nombre_demasiado_largo_rechazado(as_admin, fake_db):
    r = _crear(as_admin, "QRN", "N" * 201)
    assert r.status_code == 400
    assert not any(qr["code"] == "QRN" for qr in fake_db.state["qr_codes"].values())


# Z. code/name no string son rechazados
def test_Z_code_no_string_rechazado(as_admin, fake_db):
    r = as_admin.post(API, json={"code": 12345, "name": "Numérico"})
    assert r.status_code == 422
    assert not any(qr["code"] == "12345" for qr in fake_db.state["qr_codes"].values())


# Z2. is_active debe ser un booleano real
def test_Z2_is_active_no_booleano_rechazado(as_admin, fake_db):
    r = as_admin.patch(f"{API}/1", json={"is_active": "false"})
    assert r.status_code == 422
    assert fake_db.state["qr_codes"][1]["is_active"] is True


# Z3. El listado no expone IPs de visitantes
def test_Z3_listado_no_expone_ips(as_admin):
    as_admin.post("/api/qr/QR001/visit")
    data = as_admin.get(API).json()
    for qr in data:
        assert "ip" not in qr
        assert "ip_address" not in qr