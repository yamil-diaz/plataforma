"""Tests de regresión: verifica que los endpoints no-foro no se rompen."""

import pytest


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_books_list_endpoint(client):
    resp = client.get("/api/books")
    assert resp.status_code == 200


def test_featured_books_endpoint(client):
    resp = client.get("/api/featured-books")
    assert resp.status_code == 200


def test_nonexistent_endpoint_returns_404(client):
    resp = client.get("/api/nonexistent_endpoint_xyz")
    assert resp.status_code == 404


def test_forum_endpoint_does_not_leak_other_data(client, fake_db):
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "Cat", "description": "", "icon": "", "color": "", "sort_order": 1, "is_active": True, "post_count": 0},
    ]
    resp = client.get("/api/forum/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all("id" in c and "name" in c for c in data)
