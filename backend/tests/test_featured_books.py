"""Tests para la funcionalidad de Libros Destacados del Mes.

Endpoints:
- GET   /api/featured-books          (público: lista destacados del mes actual)
- GET   /api/admin/featured-books    (admin: configuración del mes actual)
- PUT   /api/admin/featured-books    (admin: reemplazar selección completa)
- DELETE /api/admin/featured-books/{book_id}  (admin: quitar uno)

Validaciones cubiertas:
1. Usuario normal puede consultar destacados (GET público).
2. Usuario normal NO puede modificar (PUT/DELETE rechazados 403).
3. Autor NO puede modificar salvo que sea admin.
4. Admin puede guardar lista de destacados.
5. Admin puede quitar un destacado.
6. Admin puede cambiar el orden.
7. No se pueden seleccionar más de 20.
8. No se puede destacar un libro no publicado.
9. Home muestra destacados en orden correcto.
10. Con 0 destacados la Home funciona correctamente.
11. Con 20 destacados la Home funciona correctamente.
12. No se rompe funcionalidad existente.
"""

from datetime import datetime, timezone
import server

API = "/api/featured-books"
API_ADMIN = "/api/admin/featured-books"


def _current_month_year():
    now = datetime.now(timezone.utc)
    return now.month, now.year


# ── 1. Usuario normal puede consultar destacados (GET público) ────────────────
def test_1_usuario_normal_puede_consultar(as_uploader):
    r = as_uploader.get(API)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── 2. Usuario normal NO puede modificar (PUT rechazado 403) ──────────────────
def test_2_usuario_normal_no_puede_modificar_put(as_uploader):
    r = as_uploader.put(API_ADMIN, json={"book_ids": [10]})
    assert r.status_code == 403


# ── 3. Autor NO puede modificar (PUT rechazado 403) ──────────────────────────
def test_3_autor_no_puede_modificar(as_autor):
    r = as_autor.put(API_ADMIN, json={"book_ids": [10]})
    assert r.status_code == 403


# ── 4. No autenticado NO puede modificar ─────────────────────────────────────
def test_4_no_autenticado_no_puede_modificar(client):
    r = client.put(API_ADMIN, json={"book_ids": [10]})
    assert r.status_code == 401


# ── 5. Admin puede guardar lista de destacados ───────────────────────────────
def test_5_admin_puede_guardar(as_admin, fake_db):
    r = as_admin.put(API_ADMIN, json={"book_ids": [10, 40]})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    month, year = _current_month_year()
    featured = [f for f in fake_db.state["featured_books"] if f["month"] == month and f["year"] == year]
    assert len(featured) == 2
    assert featured[0]["book_id"] == 10
    assert featured[0]["display_order"] == 0
    assert featured[1]["book_id"] == 40
    assert featured[1]["display_order"] == 1


# ── 6. Admin puede quitar un destacado ───────────────────────────────────────
def test_6_admin_puede_quitar(as_admin, fake_db):
    # Primero guardar algunos
    as_admin.put(API_ADMIN, json={"book_ids": [10, 40]})
    # Quitar el libro 40
    r = as_admin.delete(f"{API_ADMIN}/40")
    assert r.status_code == 200
    month, year = _current_month_year()
    featured = [f for f in fake_db.state["featured_books"] if f["month"] == month and f["year"] == year]
    assert len(featured) == 1
    assert featured[0]["book_id"] == 10


# ── 7. Admin puede cambiar el orden ──────────────────────────────────────────
def test_7_admin_puede_cambiar_orden(as_admin, fake_db):
    as_admin.put(API_ADMIN, json={"book_ids": [10, 40]})
    # Invertir el orden
    r = as_admin.put(API_ADMIN, json={"book_ids": [40, 10]})
    assert r.status_code == 200
    month, year = _current_month_year()
    featured = sorted(
        [f for f in fake_db.state["featured_books"] if f["month"] == month and f["year"] == year],
        key=lambda f: f["display_order"],
    )
    assert featured[0]["book_id"] == 40
    assert featured[0]["display_order"] == 0
    assert featured[1]["book_id"] == 10
    assert featured[1]["display_order"] == 1


# ── 8. No se pueden seleccionar más de 20 ────────────────────────────────────
def test_8_maximo_20(as_admin):
    # Crear 21 IDs de libros ficticios (no existen en FakeDb)
    ids_21 = list(range(100, 121))  # 21 IDs que no existen
    r = as_admin.put(API_ADMIN, json={"book_ids": ids_21})
    assert r.status_code == 400
    assert "20" in r.json()["detail"]


# ── 9. No se puede destacar un libro no publicado ────────────────────────────
def test_9_no_puede_destacar_no_publicado(as_admin):
    # Book 20 tiene published=0
    r = as_admin.put(API_ADMIN, json={"book_ids": [20]})
    assert r.status_code == 400
    assert "publicado" in r.json()["detail"].lower()


# ── 10. No se puede destacar un libro inexistente ────────────────────────────
def test_10_no_puede_destacar_inexistente(as_admin):
    r = as_admin.put(API_ADMIN, json={"book_ids": [9999]})
    assert r.status_code == 400
    assert "no encontrado" in r.json()["detail"].lower()


# ── 11. Con 0 destacados la Home funciona correctamente ──────────────────────
def test_11_cero_destacados_funciona(client):
    r = client.get(API)
    assert r.status_code == 200
    assert r.json() == []


# ── 12. Con 20 destacados funciona correctamente ─────────────────────────────
def test_12_veinte_destacados_funciona(as_admin, fake_db):
    # Publicar libros adicionales para tener 20 publicados
    for i in range(60, 80):
        fake_db.state["books"][i] = {
            "id": i,
            "title": f"Libro {i}",
            "author_name": "Autor",
            "content": "contenido",
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-01T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 1,
        }

    # 20 libros: 10, 40, 60-77
    ids_20 = [10, 40] + list(range(60, 78))
    r = as_admin.put(API_ADMIN, json={"book_ids": ids_20})
    assert r.status_code == 200
    assert r.json()["count"] == 20

    # Verificar que el GET público retorna exactamente 20
    r2 = as_admin.get(API)
    assert r2.status_code == 200
    assert len(r2.json()) == 20


# ── 13. Orden se respeta al consultar ────────────────────────────────────────
def test_13_orden_se_respeta(as_admin):
    as_admin.put(API_ADMIN, json={"book_ids": [40, 10]})
    r = as_admin.get(API)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["id"] == 40
    assert data[0]["display_order"] == 0
    assert data[1]["id"] == 10
    assert data[1]["display_order"] == 1


# ── 14. PUT reemplaza completamente (no acumula) ─────────────────────────────
def test_14_put_reemplaza_no_acumula(as_admin, fake_db):
    as_admin.put(API_ADMIN, json={"book_ids": [10, 40]})
    as_admin.put(API_ADMIN, json={"book_ids": [10]})
    month, year = _current_month_year()
    featured = [f for f in fake_db.state["featured_books"] if f["month"] == month and f["year"] == year]
    assert len(featured) == 1
    assert featured[0]["book_id"] == 10


# ── 15. Duplicados en book_ids se eliminan ───────────────────────────────────
def test_15_duplicados_se_eliminan(as_admin, fake_db):
    r = as_admin.put(API_ADMIN, json={"book_ids": [10, 10, 40]})
    assert r.status_code == 200
    assert r.json()["count"] == 2
    month, year = _current_month_year()
    featured = [f for f in fake_db.state["featured_books"] if f["month"] == month and f["year"] == year]
    assert len(featured) == 2


# ── 16. DELETE de libro no destacado devuelve 404 ────────────────────────────
def test_16_delete_no_destacado_404(as_admin):
    r = as_admin.delete(f"{API_ADMIN}/9999")
    assert r.status_code == 404


# ── 17. Usuario normal no puede consultar admin endpoint ──────────────────────
def test_17_usuario_normal_no_puede_consultar_admin(as_uploader):
    r = as_uploader.get(API_ADMIN)
    assert r.status_code == 403
