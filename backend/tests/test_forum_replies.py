"""Tests de respuestas del foro: CRUD, aceptación y permisos."""

import pytest


@pytest.fixture()
def seeded_replies(fake_db):
    """Siembra categorías, posts y replies para pruebas."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 1},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post con respuestas", "content": "Contenido del post base para test de replies",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 2, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-con-respuestas", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
    ]
    fake_db.state["forum_replies"] = [
        {
            "id": 1, "post_id": 1, "user_id": 3, "content": "Primera respuesta al post",
            "is_accepted": False, "like_count": 0, "status": "active",
            "created_at": "2026-01-10T11:00:00+00:00", "updated_at": "2026-01-10T11:00:00+00:00",
        },
        {
            "id": 2, "post_id": 1, "user_id": 4, "content": "Segunda respuesta aceptada",
            "is_accepted": True, "like_count": 2, "status": "active",
            "created_at": "2026-01-10T12:00:00+00:00", "updated_at": "2026-01-10T12:00:00+00:00",
        },
    ]


def test_create_reply_requires_auth(client, seeded_replies):
    resp = client.post("/api/forum/posts/1/replies", json={"content": "Respuesta sin auth"})
    assert resp.status_code == 401


def test_create_reply_success(as_third_party, seeded_replies):
    resp = as_third_party.post("/api/forum/posts/1/replies", json={
        "content": "Esta es una respuesta válida con suficientes caracteres"
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert "created_at" in body


def test_create_reply_short_content_rejected(as_third_party, seeded_replies):
    resp = as_third_party.post("/api/forum/posts/1/replies", json={"content": "X"})
    assert resp.status_code == 400


def test_create_reply_on_nonexistent_post(as_third_party, seeded_replies):
    resp = as_third_party.post("/api/forum/posts/999/replies", json={
        "content": "Respuesta a un post que no existe en la plataforma"
    })
    assert resp.status_code == 404


def test_accept_reply_only_post_owner(as_third_party, seeded_replies):
    resp = as_third_party.post("/api/forum/replies/1/accept")
    assert resp.status_code == 403
