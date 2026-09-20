"""Tests para las funcionalidades añadidas en Fases 1+2 del Foro Estudiantil.

Cubre: campos author_username/is_pinned/is_accepted, GET /admin/forum/posts,
desactivación de categorías, y sort oldest/active.
"""

import pytest


# ── Fixtures compartidos ────────────────────────────────────────────────────


@pytest.fixture()
def seeded_full(fake_db):
    """Siembra categorías, posts, replies y users para tests de campos."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 3},
        {"id": 2, "name": "Ayuda", "description": "", "icon": "help", "color": "#10b981", "sort_order": 2, "is_active": True, "post_count": 0},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post fijado", "content": "Contenido del post fijado para test de is_pinned",
            "category_id": 1, "book_id": None, "like_count": 2, "reply_count": 1, "views": 10,
            "is_pinned": True, "is_resolved": True, "status": "active",
            "slug": "post-fijado", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
        {
            "id": 2, "user_id": 3, "title": "Post normal", "content": "Contenido del post normal para test general",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 2, "views": 5,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-normal", "created_at": "2026-01-11T10:00:00+00:00", "updated_at": "2026-01-12T10:00:00+00:00",
        },
        {
            "id": 3, "user_id": 2, "title": "Post oculto", "content": "Contenido oculto para test de status filter",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "views": 0,
            "is_pinned": False, "is_resolved": False, "status": "hidden",
            "slug": "post-oculto", "created_at": "2026-01-12T10:00:00+00:00", "updated_at": "2026-01-12T10:00:00+00:00",
        },
    ]
    fake_db.state["forum_replies"] = [
        {
            "id": 1, "post_id": 1, "user_id": 3, "content": "Respuesta aceptada al post fijado",
            "is_accepted": True, "like_count": 1, "status": "active",
            "created_at": "2026-01-10T11:00:00+00:00", "updated_at": "2026-01-10T11:00:00+00:00",
        },
        {
            "id": 2, "post_id": 2, "user_id": 4, "content": "Respuesta normal al post normal",
            "is_accepted": False, "like_count": 0, "status": "active",
            "created_at": "2026-01-11T11:00:00+00:00", "updated_at": "2026-01-11T11:00:00+00:00",
        },
    ]
    return fake_db


# ── Tests: campos author_username ────────────────────────────────────────────


def test_post_list_returns_author_username(client, seeded_full):
    """El listado de posts debe devolver author_username."""
    resp = client.get("/api/forum/posts")
    assert resp.status_code == 200
    posts = resp.json()["posts"]
    assert len(posts) >= 1
    post = next(p for p in posts if p["id"] == 1)
    assert post["author_username"] == "uploader"


def test_post_detail_returns_author_username(client, seeded_full):
    """El detalle de un post debe devolver author_username."""
    resp = client.get("/api/forum/posts/1")
    assert resp.status_code == 200
    post = resp.json()["post"]
    assert post["author_username"] == "uploader"
    assert post["author_name"] == "Uploader"


def test_replies_return_author_username(client, seeded_full):
    """Las respuestas deben devolver author_username."""
    resp = client.get("/api/forum/posts/1/replies")
    assert resp.status_code == 200
    replies = resp.json()["replies"]
    assert len(replies) >= 1
    reply = replies[0]
    assert reply["author_username"] == "tercero"


# ── Tests: is_pinned ─────────────────────────────────────────────────────────


def test_post_list_returns_is_pinned(client, seeded_full):
    """El listado de posts debe devolver is_pinned como booleano."""
    resp = client.get("/api/forum/posts")
    assert resp.status_code == 200
    posts = resp.json()["posts"]
    pinned = next(p for p in posts if p["id"] == 1)
    unpinned = next(p for p in posts if p["id"] == 2)
    assert pinned["is_pinned"] is True
    assert unpinned["is_pinned"] is False


def test_pinned_posts_appear_first(client, seeded_full):
    """Los posts fijados deben aparecer primero en el listado."""
    resp = client.get("/api/forum/posts")
    assert resp.status_code == 200
    posts = resp.json()["posts"]
    pinned_idx = next(i for i, p in enumerate(posts) if p["id"] == 1)
    unpinned_idx = next(i for i, p in enumerate(posts) if p["id"] == 2)
    assert pinned_idx < unpinned_idx


# ── Tests: is_accepted ───────────────────────────────────────────────────────


def test_replies_return_is_accepted(client, seeded_full):
    """Las respuestas deben devolver is_accepted como booleano."""
    resp = client.get("/api/forum/posts/1/replies")
    assert resp.status_code == 200
    replies = resp.json()["replies"]
    accepted = next(r for r in replies if r["id"] == 1)
    assert accepted["is_accepted"] is True


def test_post_detail_returns_is_resolved(client, seeded_full):
    """El detalle del post con respuesta aceptada debe mostrar is_resolved."""
    resp = client.get("/api/forum/posts/1")
    assert resp.status_code == 200
    post = resp.json()["post"]
    assert post["is_resolved"] is True


# ── Tests: GET /admin/forum/posts ────────────────────────────────────────────


def test_admin_list_posts_requires_admin(as_uploader, seeded_full):
    """Solo admin puede listar posts desde el panel admin."""
    resp = as_uploader.get("/api/admin/forum/posts")
    assert resp.status_code == 403


def test_admin_list_posts_requires_auth(client, seeded_full):
    """Se requiere autenticación para listar posts admin."""
    resp = client.get("/api/admin/forum/posts")
    assert resp.status_code == 401


def test_admin_list_posts_success(as_admin, seeded_full):
    """Admin puede listar todos los posts (incluyendo no-activos)."""
    resp = as_admin.get("/api/admin/forum/posts")
    assert resp.status_code == 200
    data = resp.json()
    assert "posts" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert data["total"] == 3  # Incluye hidden


def test_admin_list_posts_filter_by_status(as_admin, seeded_full):
    """Admin puede filtrar posts por status."""
    resp = as_admin.get("/api/admin/forum/posts", params={"status": "hidden"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["posts"][0]["status"] == "hidden"


def test_admin_list_posts_pagination(as_admin, seeded_full):
    """Admin puede paginar posts — el endpoint acepta page y limit."""
    resp = as_admin.get("/api/admin/forum/posts", params={"page": 1, "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert "pages" in data
    assert "total" in data


def test_admin_list_posts_response_shape(as_admin, seeded_full):
    """Cada post del admin debe tener los campos esperados."""
    resp = as_admin.get("/api/admin/forum/posts")
    assert resp.status_code == 200
    for post in resp.json()["posts"]:
        assert "id" in post
        assert "title" in post
        assert "status" in post
        assert "author_username" in post
        assert "category_name" in post
        assert "is_pinned" in post


# ── Tests: desactivar categoría ─────────────────────────────────────────────


def test_deactivate_category_requires_admin(as_uploader, seeded_full):
    """Solo admin puede desactivar categorías."""
    resp = as_uploader.put("/api/admin/forum/categories/1/deactivate")
    assert resp.status_code == 403


def test_deactivate_category_requires_auth(client, seeded_full):
    """Se requiere autenticación para desactivar categorías."""
    resp = client.put("/api/admin/forum/categories/1/deactivate")
    assert resp.status_code == 401


def test_deactivate_category_success(as_admin, seeded_full):
    """Admin puede desactivar una categoría activa."""
    resp = as_admin.put("/api/admin/forum/categories/1/deactivate")
    assert resp.status_code == 200
    assert resp.json()["deactivated"] is True


def test_deactivate_category_already_inactive(as_admin, seeded_full):
    """No se puede desactivar una categoría ya inactiva."""
    # Hacer inactiva primero
    fake_db = seeded_full
    for c in fake_db.state["forum_categories"]:
        if c["id"] == 1:
            c["is_active"] = False
    resp = as_admin.put("/api/admin/forum/categories/1/deactivate")
    assert resp.status_code == 400


def test_deactivate_category_not_found(as_admin, seeded_full):
    """Error si la categoría no existe."""
    resp = as_admin.put("/api/admin/forum/categories/999/deactivate")
    assert resp.status_code == 404


def test_deactivate_category_removes_from_public_list(client, seeded_full):
    """Categoría desactivada no aparece en listado público."""
    fake_db = seeded_full
    for c in fake_db.state["forum_categories"]:
        if c["id"] == 1:
            c["is_active"] = False
    resp = client.get("/api/forum/categories")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert 1 not in ids


# ── Tests: sort oldest ───────────────────────────────────────────────────────


def test_sort_oldest_accepted_by_server(client, seeded_full):
    """Sort oldest debe ser aceptado por el servidor sin errores."""
    resp = client.get("/api/forum/posts", params={"sort": "oldest"})
    assert resp.status_code == 200
    data = resp.json()
    assert "posts" in data
    assert "total" in data
    # FakeDb no puede simular ORDER BY ASC, pero el endpoint no debe fallar
    assert data["total"] >= 1


# ── Tests: sort active ───────────────────────────────────────────────────────


def test_sort_active_returns_results(client, seeded_full):
    """Sort active debe devolver resultados sin errores."""
    resp = client.get("/api/forum/posts", params={"sort": "active"})
    assert resp.status_code == 200
    assert "posts" in resp.json()


# ── Tests: Fase 3A — Edición de posts ───────────────────────────────────────


def test_edit_post_requires_auth(client, seeded_full):
    """Editar post requiere autenticación."""
    resp = client.put("/api/forum/posts/1", json={"title": "Editado"})
    assert resp.status_code == 401


def test_edit_post_success(as_uploader, seeded_full):
    """El propietario puede editar su post."""
    resp = as_uploader.put("/api/forum/posts/1", json={
        "title": "Post fijado editado",
        "content": "Contenido actualizado del post fijado para test"
    })
    assert resp.status_code == 200
    assert resp.json()["updated"] is True


def test_edit_post_other_user_rejected(as_third_party, seeded_full):
    """Un usuario no puede editar el post de otro."""
    resp = as_third_party.put("/api/forum/posts/1", json={"title": "Intento de hack"})
    assert resp.status_code == 403


def test_edit_post_admin_allowed(as_admin, seeded_full):
    """El admin puede editar cualquier post."""
    resp = as_admin.put("/api/forum/posts/1", json={"title": "Editado por admin"})
    assert resp.status_code == 200


def test_edit_post_short_title_rejected(as_uploader, seeded_full):
    """Título menor a 3 caracteres es rechazado."""
    resp = as_uploader.put("/api/forum/posts/1", json={"title": "AB"})
    assert resp.status_code == 400


def test_edit_post_hidden_rejected(as_uploader, seeded_full):
    """No se puede editar un post oculto."""
    for p in seeded_full.state["forum_posts"]:
        if p["id"] == 1:
            p["status"] = "hidden"
    resp = as_uploader.put("/api/forum/posts/1", json={"title": "Intento"})
    assert resp.status_code == 400


# ── Tests: Fase 3B — Notificaciones ─────────────────────────────────────────


def test_reply_generates_notification(fake_db, seeded_full):
    """Al responder a un post, se genera notificación al autor del post."""
    fake_db.state["notifications"] = []
    as_user = __import__('fastapi.testclient', fromlist=['TestClient']).TestClient
    from fastapi.testclient import TestClient
    import server
    client_tc = TestClient(server.app)
    client_tc.cookies.set("access_token", server.create_access_token(3, "tercero@test.com"))
    resp = client_tc.post("/api/forum/posts/1/replies", json={
        "content": "Respuesta que genera notificación al autor del post"
    })
    assert resp.status_code == 200
    # Verificar que se creó notificación para user_id=2 (autor del post 1)
    notifs = [n for n in fake_db.state["notifications"] if n[0] == 2]
    assert len(notifs) >= 1


def test_reply_no_self_notification(fake_db, seeded_full):
    """Un usuario que responde a su propio post no recibe notificación."""
    fake_db.state["notifications"] = []
    from fastapi.testclient import TestClient
    import server
    client_tc = TestClient(server.app)
    client_tc.cookies.set("access_token", server.create_access_token(2, "uploader@test.com"))
    resp = client_tc.post("/api/forum/posts/1/replies", json={
        "content": "Respuesta del propio autor que no debe generar notificación"
    })
    assert resp.status_code == 200
    # user_id=2 es el autor del post 1, no debería recibir notificación
    notifs = [n for n in fake_db.state["notifications"] if n[0] == 2]
    assert len(notifs) == 0


# ── Tests: Fase 3B — Like notification ──────────────────────────────────────


def test_like_generates_notification(fake_db, seeded_full):
    """Al dar like a un post de otro, se genera notificación."""
    fake_db.state["notifications"] = []
    from fastapi.testclient import TestClient
    import server
    client_tc = TestClient(server.app)
    client_tc.cookies.set("access_token", server.create_access_token(3, "tercero@test.com"))
    resp = client_tc.post("/api/forum/posts/1/like")  # Post 1 es de user 2
    assert resp.status_code == 200
    assert resp.json()["liked"] is True
    # user_id=3 le dio like al post 1 (de user_id=2), notificación para user 2
    notifs = [n for n in fake_db.state["notifications"] if n[0] == 2]
    assert len(notifs) >= 1


def test_like_own_post_no_notification(fake_db, seeded_full):
    """Like a post propio no debería llegar aquí (endpoint rechaza), pero verificamos."""
    from fastapi.testclient import TestClient
    import server
    client_tc = TestClient(server.app)
    client_tc.cookies.set("access_token", server.create_access_token(2, "uploader@test.com"))
    resp = client_tc.post("/api/forum/posts/1/like")
    assert resp.status_code == 400  # No puedes dar like a tu propia publicación


def test_unlike_does_not_generate_notification(fake_db, seeded_full):
    """Quitar like no genera notificación."""
    fake_db.state["notifications"] = []
    fake_db.state["forum_likes"] = [
        {"id": 1, "post_id": 1, "user_id": 3, "created_at": "2026-01-10T10:30:00+00:00"}
    ]
    from fastapi.testclient import TestClient
    import server
    client_tc = TestClient(server.app)
    client_tc.cookies.set("access_token", server.create_access_token(3, "tercero@test.com"))
    resp = client_tc.post("/api/forum/posts/1/like")  # Post 1 es de user 2
    assert resp.status_code == 200
    assert resp.json()["liked"] is False
    # No debería haber notificaciones nuevas por quitar like
    notifs = [n for n in fake_db.state["notifications"]]
    assert len(notifs) == 0


# ── Tests: Fase 3B — Content excerpt ────────────────────────────────────────


def test_list_posts_includes_content_excerpt(client, seeded_full):
    """El listado de posts incluye content_excerpt."""
    resp = client.get("/api/forum/posts")
    assert resp.status_code == 200
    posts = resp.json()["posts"]
    for post in posts:
        assert "content_excerpt" in post


def test_admin_list_includes_content_excerpt(as_admin, seeded_full):
    """El listado admin de posts incluye content_excerpt."""
    resp = as_admin.get("/api/admin/forum/posts")
    assert resp.status_code == 200
    for post in resp.json()["posts"]:
        assert "content_excerpt" in post


def test_search_includes_content_excerpt(client, seeded_full):
    """La búsqueda incluye content_excerpt."""
    resp = client.get("/api/forum/search", params={"q": "fijado"})
    assert resp.status_code == 200
    for post in resp.json()["posts"]:
        assert "content_excerpt" in post
