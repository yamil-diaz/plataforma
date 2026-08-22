"""Tests de likes en publicaciones del foro: toggle, validación y conteo."""

import pytest


@pytest.fixture()
def seeded_likes(fake_db):
    """Siembra categorías, posts y likes para pruebas de interacción."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 1},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post para likes", "content": "Contenido del post que recibe likes en el test",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-para-likes", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
        {
            "id": 2, "user_id": 3, "title": "Post propio", "content": "Contenido del post que pertenece al usuario 3",
            "category_id": 1, "book_id": None, "like_count": 1, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-propio", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
    ]
    fake_db.state["forum_likes"] = [
        {"id": 1, "user_id": 3, "target_type": "post", "target_id": 1, "post_id": 1, "created_at": "2026-01-10T10:30:00+00:00"},
    ]
    return fake_db


def test_like_requires_auth(client, seeded_likes):
    resp = client.post("/api/forum/posts/1/like")
    assert resp.status_code == 401


def test_like_toggle_adds_like(as_autor, seeded_likes):
    resp = as_autor.post("/api/forum/posts/1/like")
    assert resp.status_code == 200
    body = resp.json()
    assert body["liked"] is True
    assert body["like_count"] >= 1


def test_like_toggle_removes_like(as_autor, seeded_likes):
    fake_db = seeded_likes
    fake_db.state["forum_likes"].append(
        {"id": 2, "user_id": 4, "target_type": "post", "target_id": 1, "post_id": 1, "created_at": "2026-01-10T10:35:00+00:00"}
    )
    resp = as_autor.post("/api/forum/posts/1/like")
    assert resp.status_code == 200
    body = resp.json()
    assert body["liked"] is False


def test_like_own_post_rejected(as_uploader, seeded_likes):
    resp = as_uploader.post("/api/forum/posts/1/like")
    assert resp.status_code == 400


def test_like_nonexistent_post(as_autor, seeded_likes):
    resp = as_autor.post("/api/forum/posts/999/like")
    assert resp.status_code == 404
