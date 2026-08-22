"""Tests de categorías del foro: listado público y comportamiento de is_active."""

import pytest


@pytest.fixture()
def seeded_cats(fake_db):
    """Siembra 3 categorías: 2 activas, 1 inactiva."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "Discusiones generales", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 0},
        {"id": 2, "name": "Soporte", "description": "Ayuda técnica", "icon": "help", "color": "#10b981", "sort_order": 2, "is_active": True, "post_count": 0},
        {"id": 3, "name": "Descontinuada", "description": "Cerrada", "icon": "lock", "color": "#6b7280", "sort_order": 3, "is_active": False, "post_count": 0},
    ]
    return fake_db


def test_categories_list_returns_active_only(client, seeded_cats):
    resp = client.get("/api/forum/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [c["id"] for c in data]
    assert 1 in ids
    assert 2 in ids
    assert 3 not in ids


def test_categories_list_empty_when_none_active(fake_db):
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "X", "description": "", "icon": "", "color": "", "sort_order": 1, "is_active": False, "post_count": 0},
    ]
    from fastapi.testclient import TestClient
    import server
    c = TestClient(server.app)
    resp = c.get("/api/forum/categories")
    assert resp.status_code == 200
    assert resp.json() == []


def test_categories_response_shape(client, seeded_cats):
    resp = client.get("/api/forum/categories")
    assert resp.status_code == 200
    for cat in resp.json():
        assert "id" in cat
        assert "name" in cat
        assert "description" in cat
        assert "icon" in cat


def test_categories_sorted_by_sort_order(client, seeded_cats):
    resp = client.get("/api/forum/categories")
    assert resp.status_code == 200
    data = resp.json()
    orders = [c["sort_order"] for c in data]
    assert orders == sorted(orders)


def test_category_with_post_count(client, seeded_cats):
    seeded_cats.state["forum_categories"][0]["post_count"] = 42
    resp = client.get("/api/forum/categories")
    assert resp.status_code == 200
    gen = next(c for c in resp.json() if c["name"] == "General")
    assert gen["post_count"] == 42
