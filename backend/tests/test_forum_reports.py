"""Tests de reportes del foro: creación, validación y duplicados."""

import pytest


@pytest.fixture()
def seeded_reports(fake_db):
    """Siembra categorías, posts y reports para pruebas."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 1},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post reportable", "content": "Contenido del post que será reportado en el test",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "view_count": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-reportable", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
    ]
    fake_db.state["forum_replies"] = [
        {
            "id": 1, "post_id": 1, "user_id": 4, "content": "Respuesta que también puede ser reportada",
            "is_accepted": False, "like_count": 0, "status": "active",
            "created_at": "2026-01-10T11:00:00+00:00", "updated_at": "2026-01-10T11:00:00+00:00",
        },
    ]
    fake_db.state["forum_reports"] = []


def test_report_requires_auth(client, seeded_reports):
    resp = client.post("/api/forum/reports", json={
        "post_id": 1, "reason": "spam", "explanation": "Es spam"
    })
    assert resp.status_code == 401


def test_report_post_success(as_third_party, seeded_reports):
    resp = as_third_party.post("/api/forum/reports", json={
        "post_id": 1, "reason": "spam", "explanation": "Contenido spam reportado"
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["reported"] is True
    assert "id" in body


def test_report_reply_success(as_third_party, seeded_reports):
    resp = as_third_party.post("/api/forum/reports", json={
        "reply_id": 1, "reason": "offensive", "explanation": "Contenido ofensivo detectado"
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["reported"] is True


def test_report_invalid_reason(as_third_party, seeded_reports):
    resp = as_third_party.post("/api/forum/reports", json={
        "post_id": 1, "reason": "invalido", "explanation": "Motivo inválido"
    })
    assert resp.status_code == 400


def test_report_own_content_rejected(as_uploader, seeded_reports):
    resp = as_uploader.post("/api/forum/reports", json={
        "post_id": 1, "reason": "spam", "explanation": "Reporte de contenido propio"
    })
    assert resp.status_code == 400
