"""Integración: permisos de lectura sobre libros pendientes.

- El uploader puede previsualizar su libro pendiente (/start, /pages,
  /chapters, /progress) y también recompensas de lectura.
- Un tercero recibe 403 en todos los endpoints de lectura.
- El admin mantiene acceso.
- El comportamiento para libros publicados no cambia.
"""

BOOK_PENDIENTE = 20      # uploader_id = 2
BOOK_PUBLICADO = 10      # uploader_id = 2, publicado


def test_uploader_previsualiza_su_libro_pendiente_start_y_pages(fake_db, as_uploader):
    resp_start = as_uploader.post(f"/api/books/{BOOK_PENDIENTE}/start")
    assert resp_start.status_code == 200, resp_start.text
    assert resp_start.json()["total_pages"] == 1

    resp_page = as_uploader.get(f"/api/books/{BOOK_PENDIENTE}/pages/1")
    assert resp_page.status_code == 200, resp_page.text
    assert resp_page.json()["content"] == "página del libro pendiente"


def test_uploader_previsualiza_chapters_y_progress_del_pendiente(fake_db, as_uploader):
    resp_chapters = as_uploader.get(f"/api/books/{BOOK_PENDIENTE}/chapters")
    assert resp_chapters.status_code == 200, resp_chapters.text

    resp_progress = as_uploader.post(f"/api/books/{BOOK_PENDIENTE}/progress", json={"page": 1})
    assert resp_progress.status_code == 200, resp_progress.text

    resp_progress_get = as_uploader.get(f"/api/books/{BOOK_PENDIENTE}/progress")
    assert resp_progress_get.status_code == 200, resp_progress_get.text


def test_uploader_puede_lectura_reward_de_su_pendiente(fake_db, as_uploader):
    resp = as_uploader.post(f"/api/books/{BOOK_PENDIENTE}/reading-reward")
    assert resp.status_code == 200, resp.text


def test_tercero_no_puede_leer_libro_pendiente(fake_db, as_third_party):
    assert as_third_party.post(f"/api/books/{BOOK_PENDIENTE}/start").status_code == 403
    assert as_third_party.get(f"/api/books/{BOOK_PENDIENTE}/pages/1").status_code == 403
    assert as_third_party.get(f"/api/books/{BOOK_PENDIENTE}/chapters").status_code == 403
    assert as_third_party.post(f"/api/books/{BOOK_PENDIENTE}/progress", json={"page": 1}).status_code == 403
    assert as_third_party.get(f"/api/books/{BOOK_PENDIENTE}/progress").status_code == 403
    assert as_third_party.post(f"/api/books/{BOOK_PENDIENTE}/reading-reward").status_code == 403


def test_admin_mantiene_acceso_al_pendiente(fake_db, as_admin):
    assert as_admin.post(f"/api/books/{BOOK_PENDIENTE}/start").status_code == 200
    assert as_admin.get(f"/api/books/{BOOK_PENDIENTE}/pages/1").status_code == 200


def test_uploader_puede_previsualizar_pendiente_sin_uploader_de_otro(fake_db, as_uploader):
    resp = as_uploader.get("/api/books/30/pages/1")
    assert resp.status_code == 403


def test_tercero_si_puede_leer_libro_publicado(fake_db, as_third_party):
    resp = as_third_party.post(f"/api/books/{BOOK_PUBLICADO}/start")
    assert resp.status_code == 200, resp.text
    resp_page = as_third_party.get(f"/api/books/{BOOK_PUBLICADO}/pages/1")
    assert resp_page.status_code == 200, resp_page.text
    assert resp_page.json()["content"] == "página del libro publicado"


def test_usuario_no_autenticado_recibe_401(fake_db, client):
    assert client.post(f"/api/books/{BOOK_PENDIENTE}/start").status_code == 401
    assert client.get(f"/api/books/{BOOK_PENDIENTE}/pages/1").status_code == 401