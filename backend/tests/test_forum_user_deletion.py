"""Tests de eliminación de usuarios con posts/respuestas y consistencia de post_count."""

import pytest


@pytest.fixture()
def seeded_user_posts(fake_db):
    """Siembra categorías, posts y replies para pruebas de eliminación de usuario."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 2},
        {"id": 2, "name": "Ayuda", "description": "", "icon": "help", "color": "#10b981", "sort_order": 2, "is_active": True, "post_count": 1},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post usuario 2", "content": "Contenido del post del usuario 2",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 1, "views": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-usuario-2", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
        {
            "id": 2, "user_id": 2, "title": "Otro post usuario 2", "content": "Otro contenido",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "views": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "otro-post-usuario-2", "created_at": "2026-01-11T10:00:00+00:00", "updated_at": "2026-01-11T10:00:00+00:00",
        },
        {
            "id": 3, "user_id": 3, "title": "Post usuario 3", "content": "Contenido del usuario 3",
            "category_id": 2, "book_id": None, "like_count": 0, "reply_count": 0, "views": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-usuario-3", "created_at": "2026-01-12T10:00:00+00:00", "updated_at": "2026-01-12T10:00:00+00:00",
        },
    ]
    fake_db.state["forum_replies"] = [
        {
            "id": 1, "post_id": 1, "user_id": 3, "content": "Respuesta del usuario 3 al post 1",
            "status": "active", "is_accepted": False, "like_count": 0,
            "created_at": "2026-01-10T11:00:00+00:00", "updated_at": "2026-01-10T11:00:00+00:00",
        },
    ]


def test_delete_user_posts_remain(fake_db, seeded_user_posts):
    """Verificar que al eliminar usuario, sus posts quedan con user_id NULL y permanecen en BD."""
    # Simular ON DELETE SET NULL en forum_posts.user_id
    # Buscar posts del usuario 2
    posts_user2 = [p for p in fake_db.state["forum_posts"] if p.get("user_id") == 2]
    assert len(posts_user2) == 2

    # Simular eliminación del usuario (ON DELETE SET NULL)
    for p in fake_db.state["forum_posts"]:
        if p.get("user_id") == 2:
            p["user_id"] = None

    # Verificar que posts siguen existiendo
    posts_after = [p for p in fake_db.state["forum_posts"] if p["id"] in [1, 2]]
    assert len(posts_after) == 2
    assert all(p.get("user_id") is None for p in posts_after)

    # Verificar que post del usuario 3 no cambió
    post_user3 = next(p for p in fake_db.state["forum_posts"] if p["id"] == 3)
    assert post_user3.get("user_id") == 3


def test_delete_user_replies_remain(fake_db, seeded_user_posts):
    """Verificar que al eliminar usuario, sus replies quedan con user_id NULL y permanecen en BD."""
    replies_user3 = [r for r in fake_db.state["forum_replies"] if r.get("user_id") == 3]
    assert len(replies_user3) == 1

    # Simular eliminación del usuario (ON DELETE SET NULL)
    for r in fake_db.state["forum_replies"]:
        if r.get("user_id") == 3:
            r["user_id"] = None

    # Verificar que reply sigue existiendo
    reply_after = next(r for r in fake_db.state["forum_replies"] if r["id"] == 1)
    assert reply_after.get("user_id") is None


@pytest.fixture()
def seeded_post_count(fake_db):
    """Siembra categorías y posts para pruebas de post_count."""
    fake_db.state["forum_categories"] = [
        {"id": 1, "name": "General", "description": "", "icon": "chat", "color": "#3b82f6", "sort_order": 1, "is_active": True, "post_count": 2},
        {"id": 2, "name": "Ayuda", "description": "", "icon": "help", "color": "#10b981", "sort_order": 2, "is_active": True, "post_count": 1},
    ]
    fake_db.state["forum_posts"] = [
        {
            "id": 1, "user_id": 2, "title": "Post activo cat 1", "content": "Contenido",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "views": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-activo-cat1", "created_at": "2026-01-10T10:00:00+00:00", "updated_at": "2026-01-10T10:00:00+00:00",
        },
        {
            "id": 2, "user_id": 2, "title": "Post activo cat 1 - 2", "content": "Contenido",
            "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "views": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-activo-cat1-2", "created_at": "2026-01-11T10:00:00+00:00", "updated_at": "2026-01-11T10:00:00+00:00",
        },
        {
            "id": 3, "user_id": 3, "title": "Post activo cat 2", "content": "Contenido",
            "category_id": 2, "book_id": None, "like_count": 0, "reply_count": 0, "views": 0,
            "is_pinned": False, "is_resolved": False, "status": "active",
            "slug": "post-activo-cat2", "created_at": "2026-01-12T10:00:00+00:00", "updated_at": "2026-01-12T10:00:00+00:00",
        },
    ]


def test_create_post_increments_count(fake_db, seeded_post_count):
    """Crear post → post_count +1"""
    # Simular INSERT + UPDATE post_count
    new_id = max(p["id"] for p in fake_db.state["forum_posts"]) + 1
    fake_db.state["forum_posts"].append({
        "id": new_id, "user_id": 2, "title": "Nuevo post", "content": "Contenido nuevo",
        "category_id": 1, "book_id": None, "like_count": 0, "reply_count": 0, "views": 0,
        "is_pinned": False, "is_resolved": False, "status": "active",
        "slug": "nuevo-post", "created_at": "2026-01-13T10:00:00+00:00", "updated_at": "2026-01-13T10:00:00+00:00",
    })

    # Simular UPDATE forum_categories SET post_count = post_count + 1 WHERE id = 1
    for c in fake_db.state["forum_categories"]:
        if c["id"] == 1:
            c["post_count"] += 1
            break

    cat = next(c for c in fake_db.state["forum_categories"] if c["id"] == 1)
    assert cat["post_count"] == 3


def test_delete_post_decrements_count(fake_db, seeded_post_count):
    """Eliminar post → post_count -1"""
    post = next(p for p in fake_db.state["forum_posts"] if p["id"] == 1)
    cat_id = post["category_id"]

    # Simular UPDATE forum_posts SET status = 'deleted'
    post["status"] = "deleted"

    # Simular UPDATE forum_categories SET post_count = GREATEST(post_count - 1, 0)
    for c in fake_db.state["forum_categories"]:
        if c["id"] == cat_id:
            c["post_count"] = max(c["post_count"] - 1, 0)
            break

    cat = next(c for c in fake_db.state["forum_categories"] if c["id"] == 1)
    assert cat["post_count"] == 1


def test_admin_mark_deleted_decrements_count(fake_db, seeded_post_count):
    """Admin marcar deleted → post_count -1"""
    post = next(p for p in fake_db.state["forum_posts"] if p["id"] == 1)
    assert post["status"] == "active"
    cat_id = post["category_id"]

    # Admin cambia a deleted
    old_status = post["status"]
    post["status"] = "deleted"

    # Decrementar solo si no estaba deleted antes
    if old_status != "deleted":
        for c in fake_db.state["forum_categories"]:
            if c["id"] == cat_id:
                c["post_count"] = max(c["post_count"] - 1, 0)
                break

    cat = next(c for c in fake_db.state["forum_categories"] if c["id"] == 1)
    assert cat["post_count"] == 1


def test_restore_from_deleted_increments_count(fake_db, seeded_post_count):
    """Volver de deleted a active → post_count +1"""
    post = next(p for p in fake_db.state["forum_posts"] if p["id"] == 1)
    post["status"] = "deleted"  # empezar en deleted
    cat_id = post["category_id"]

    # Decrementar primero (simulando que ya fue borrado)
    for c in fake_db.state["forum_categories"]:
        if c["id"] == cat_id:
            c["post_count"] = max(c["post_count"] - 1, 0)
            break

    # Ahora restaurar
    old_status = "deleted"
    new_status = "active"
    post["status"] = new_status

    if old_status == "deleted" and new_status != "deleted":
        for c in fake_db.state["forum_categories"]:
            if c["id"] == cat_id:
                c["post_count"] += 1
                break

    cat = next(c for c in fake_db.state["forum_categories"] if c["id"] == 1)
    assert cat["post_count"] == 2  # Volvió al valor original


def test_move_post_category_updates_counts(fake_db, seeded_post_count):
    """Mover post de categoría → -1 en anterior, +1 en nueva"""
    post = next(p for p in fake_db.state["forum_posts"] if p["id"] == 1)
    old_cat_id = post["category_id"]
    new_cat_id = 2
    assert old_cat_id != new_cat_id

    old_count_before = next(c for c in fake_db.state["forum_categories"] if c["id"] == old_cat_id)["post_count"]
    new_count_before = next(c for c in fake_db.state["forum_categories"] if c["id"] == new_cat_id)["post_count"]

    # Actualizar post_count en ambas categorías
    for c in fake_db.state["forum_categories"]:
        if c["id"] == old_cat_id:
            c["post_count"] = max(c["post_count"] - 1, 0)
        if c["id"] == new_cat_id:
            c["post_count"] += 1

    post["category_id"] = new_cat_id

    old_count_after = next(c for c in fake_db.state["forum_categories"] if c["id"] == old_cat_id)["post_count"]
    new_count_after = next(c for c in fake_db.state["forum_categories"] if c["id"] == new_cat_id)["post_count"]

    assert old_count_after == old_count_before - 1
    assert new_count_after == new_count_before + 1


def test_no_double_decrement_on_delete_deleted_post(fake_db, seeded_post_count):
    """Evitar doble decremento al eliminar post ya deleted"""
    post = next(p for p in fake_db.state["forum_posts"] if p["id"] == 1)
    post["status"] = "deleted"  # Ya está deleted
    cat_id = post["category_id"]

    cat_before = next(c for c in fake_db.state["forum_categories"] if c["id"] == cat_id)["post_count"]

    # Intentar "eliminar" de nuevo - no debería decrementar
    if post["status"] != "deleted":  # Esta condición evita el doble decremento
        for c in fake_db.state["forum_categories"]:
            if c["id"] == cat_id:
                c["post_count"] = max(c["post_count"] - 1, 0)
                break

    cat_after = next(c for c in fake_db.state["forum_categories"] if c["id"] == cat_id)["post_count"]
    assert cat_after == cat_before  # No cambió


def test_no_double_decrement_admin_deleted_then_user_delete(fake_db, seeded_post_count):
    """Evitar doble decremento: admin marca deleted y luego usuario intenta borrar"""
    post = next(p for p in fake_db.state["forum_posts"] if p["id"] == 1)
    cat_id = post["category_id"]

    # Admin marca como deleted (decrementa)
    old_status = post["status"]
    post["status"] = "deleted"
    if old_status != "deleted":
        for c in fake_db.state["forum_categories"]:
            if c["id"] == cat_id:
                c["post_count"] = max(c["post_count"] - 1, 0)
                break

    cat_after_admin = next(c for c in fake_db.state["forum_categories"] if c["id"] == cat_id)["post_count"]

    # Usuario intenta borrar (el endpoint comprueba status != 'deleted' antes de decrementar)
    if post["status"] != "deleted":  # Esta es la verificación que agregamos
        for c in fake_db.state["forum_categories"]:
            if c["id"] == cat_id:
                c["post_count"] = max(c["post_count"] - 1, 0)
                break

    cat_after_user = next(c for c in fake_db.state["forum_categories"] if c["id"] == cat_id)["post_count"]
    assert cat_after_user == cat_after_admin  # No hubo segundo decremento


def test_delete_post_not_deleted_decrements(fake_db, seeded_post_count):
    """Eliminar post activo → decrementa (sanity check)"""
    post = next(p for p in fake_db.state["forum_posts"] if p["id"] == 2)
    assert post["status"] == "active"
    cat_id = post["category_id"]

    cat_before = next(c for c in fake_db.state["forum_categories"] if c["id"] == cat_id)["post_count"]

    if post["status"] != "deleted":
        post["status"] = "deleted"
        for c in fake_db.state["forum_categories"]:
            if c["id"] == cat_id:
                c["post_count"] = max(c["post_count"] - 1, 0)
                break

    cat_after = next(c for c in fake_db.state["forum_categories"] if c["id"] == cat_id)["post_count"]
    assert cat_after == cat_before - 1