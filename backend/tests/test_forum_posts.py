"""Tests de publicaciones del foro: CRUD, listado, búsqueda y paginación."""

import pytest


@pytest.fixture()
def seeded_posts(fake_db):
    """Siembra categorías + posts para pruebas de CRUD."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 2},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Primer post", "content": "Contenido del primer post para test",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "primer-post", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
        {
            "id": 2, "user_id": 3, "title": "Segundo post", "content": "Contenido del segundo post para test",
            "category_id": 1, "book_id": None, "like_count": 3, "reply_count": 1, "view_count": 10,
            "is_pinned": True, "is_resolved": False, "status": "active",
            "slug": "segundo-post", "created_at": "2026-01-11T10:00:00+00:00", "updated_at": "2026-01-11T10:00:00+00:00",
        },
        {
            "id": 3, "user_id": 2, "title": "Post eliminado", "content": "Ya no existe",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "deleted",
            "slug": "post-eliminado", "created_at": "2026-01-12T10:00:00+00:00", "updated_at": "2026-01-12T10:00:00+00:00",
        },
    ]


def test_create_post_requires_auth(client, seeded_posts):
    resp = client.post("/api/forum/posts", json={
        "title": "Tres letras", "content": "Contenido con al menos diez caracteres",
        "category_id": 1,
    })
    assert resp.status_code == 401


def test_create_post_success(as_uploader, seeded_posts):
    resp = as_uploader.post("/api/forum/posts", json={
        "title": "Mi nuevo post de prueba", "content": "Este es el contenido del post con suficientes caracteres",
        "category_id": 1,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert "slug" in body
    assert "created_at" in body


def test_create_post_short_title_rejected(as_uploader, seeded_posts):
    resp = as_uploader.post("/api/forum/posts", json={
        "title": "AB", "content": "Contenido con al menos diez caracteres para pasar validación",
        "category_id": 1,
    })
    assert resp.status_code == 400


def test_create_post_invalid_category(as_uploader, seeded_posts):
    resp = as_uploader.post("/api/forum/posts", json={
        "title": "Post válido", "content": "Contenido con al menos diez caracteres para la validación",
        "category_id": 999,
    })
    assert resp.status_code == 400


def test_create_post_short_content_rejected(as_uploader, seeded_posts):
    resp = as_uploader.post("/api/forum/posts", json={
        "title": "Post con contenido corto", "content": "Corto",
        "category_id": 1,
    })
    assert resp.status_code == 400
