"""Tests de bookmarks del foro: toggle y listado de guardados."""

import pytest


@pytest.fixture()
def seeded_bookmarks(fake_db):
    """Siembra categorías, posts y bookmarks para pruebas."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 2},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post guardado", "content": "Contenido del post que está guardado en bookmarks",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-guardado", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
        {
            "id": 2, "user_id": 3, "title": "Post no guardado", "content": "Contenido del post que no está en bookmarks",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-no-guardado", "created_at": "2026-01-10T11:00:00+00:00", "updated_at": "2026-01-10T11:00:00+00:00",
        },
    ]
    fake_db.state["forum_bookmarks"] = [
        {"id": 1, "user_id": 3, "post_id": 1, "created_at": "2026-01-10T10:30:00+00:00"},
    ]


def test_bookmark_requires_auth(client, seeded_bookmarks):
    resp = client.post("/api/forum/posts/1/bookmark")
    assert resp.status_code == 401


def test_bookmark_toggle_adds(as_third_party, seeded_bookmarks):
    resp = as_third_party.post("/api/forum/posts/2/bookmark")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bookmarked"] is True


def test_bookmark_toggle_removes(as_third_party, seeded_bookmarks):
    resp = as_third_party.post("/api/forum/posts/1/bookmark")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bookmarked"] is False


def test_bookmark_nonexistent_post(as_third_party, seeded_bookmarks):
    resp = as_third_party.post("/api/forum/posts/999/bookmark")
    assert resp.status_code == 404


def test_bookmarks_list_requires_auth(client, seeded_bookmarks):
    resp = client.get("/api/forum/bookmarks")
    assert resp.status_code == 401
