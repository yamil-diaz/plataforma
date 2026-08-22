"""Tests de moderación admin: cambiar estado, fijar posts, resolver reportes."""

import pytest


@pytest.fixture()
def seeded_mod(fake_db):
    """Siembra categorías, posts y reports para pruebas de moderación."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 1},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post a moderar", "content": "Contenido del post que será moderado por el admin",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-a-moderar", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
    ]
    fake_db.state["forum_reports"] = [
        {
            "id": 1, "reporter_id": 3, "post_id": 1, "reply_id": None,
            "reason": "spam", "explanation": "Reporte pendiente de revisión",
            "status": "pending", "admin_note": None,
            "resolved_by": None, "resolved_at": None,
            "created_at": "2026-01-10T10:30:00+00:00",
        },
    ]


def test_admin_change_status_requires_admin_role(as_uploader, seeded_mod):
    resp = as_uploader.put("/api/admin/forum/posts/1/status", json={"status": "hidden"})
    assert resp.status_code == 403


def test_admin_change_status_success(as_admin, seeded_mod):
    resp = as_admin.put("/api/admin/forum/posts/1/status", json={"status": "hidden"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["updated"] is True
    assert body["status"] == "hidden"


def test_admin_invalid_status_rejected(as_admin, seeded_mod):
    resp = as_admin.put("/api/admin/forum/posts/1/status", json={"status": "bogus"})
    assert resp.status_code == 400


def test_admin_toggle_pin_success(as_admin, seeded_mod):
    resp = as_admin.put("/api/admin/forum/posts/1/pin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pinned"] is True


def test_admin_toggle_pin_twice_unpins(as_admin, seeded_mod):
    as_admin.put("/api/admin/forum/posts/1/pin")
    resp = as_admin.put("/api/admin/forum/posts/1/pin")
    assert resp.status_code == 200
    assert resp.json()["pinned"] is False
