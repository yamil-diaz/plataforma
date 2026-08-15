"""Integración: approve/reject de libros con y sin uploader_id.

Antes del PASO 1, aprobar un libro con uploader_id NULL (semilla, ZIP o
Gutenberg) provocaba HTTP 500 por el NOT NULL de notifications.user_id.
"""


def test_approve_con_uploader_valido_genera_notificacion(fake_db, as_admin):
    resp = as_admin.put("/api/books/20/approve")
    assert resp.status_code == 200, resp.text
    book = fake_db.state["books"][20]
    assert book["published"] == 1
    notificaciones = fake_db.state["notifications"]
    assert len(notificaciones) == 1
    user_id, message, created_at = notificaciones[0]
    assert user_id == 2
    assert "aprobada" in message


def test_approve_con_uploader_null_no_genera_notificacion_ni_500(fake_db, as_admin):
    resp = as_admin.put("/api/books/30/approve")
    assert resp.status_code == 200, resp.text
    book = fake_db.state["books"][30]
    assert book["published"] == 1
    assert fake_db.state["notifications"] == []


def test_approve_libro_publicado_sin_uploader_no_rompe(fake_db, as_admin):
    resp = as_admin.put("/api/books/40/approve")
    assert resp.status_code == 200, resp.text
    assert fake_db.state["notifications"] == []


def test_reject_con_uploader_valido_notifica_y_elimina(fake_db, as_admin):
    resp = as_admin.delete("/api/books/20/reject")
    assert resp.status_code == 200, resp.text
    assert 20 not in fake_db.state["books"]
    assert len(fake_db.state["notifications"]) == 1
    user_id, message, _ = fake_db.state["notifications"][0]
    assert user_id == 2
    assert "no fue aprobada" in message


def test_reject_con_uploader_null_no_genera_notificacion_ni_500(fake_db, as_admin):
    resp = as_admin.delete("/api/books/30/reject")
    assert resp.status_code == 200, resp.text
    assert 30 not in fake_db.state["books"]
    assert fake_db.state["notifications"] == []


def test_approve_reject_requieren_rol_admin(fake_db, as_uploader):
    resp_approve = as_uploader.put("/api/books/20/approve")
    assert resp_approve.status_code == 403
    resp_reject = as_uploader.delete("/api/books/20/reject")
    assert resp_reject.status_code == 403
    assert 20 in fake_db.state["books"]