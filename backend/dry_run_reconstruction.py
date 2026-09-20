#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dry_run_reconstruction.py — Simulación DRY-RUN de reconstrucción del catálogo.

MUESTRA exactamente qué tablas y registros serían afectados.
NO EJECUTA DELETE/UPDATE/INSERT en producción.
NO MODIFICA DATOS.

Uso:
  python dry_run_reconstruction.py --database-url "postgresql://..." --strategy maintain-ids
  python dry_run_reconstruction.py --database-url "postgresql://..." --strategy new-ids

Estrategias de IDs:
  - maintain-ids: mantener IDs actuales, reemplazar contenido
  - new-ids: crear nuevos IDs para libros reconstruidos
  - hybrid: mantener IDs para libros con datos de usuario, nuevos IDs para el resto
"""

import os
import sys
import argparse
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import psycopg2
import psycopg2.extras


@dataclass
class TableImpact:
    """Impacto en una tabla."""
    table_name: str
    total_rows: int
    rows_affected: int
    rows_preserved: int
    action: str  # 'rebuild', 'preserve', 'rebuild_with_fk_update', 'rebuild_with_new_ids'
    description: str


def get_db_connection(database_url: str):
    """Crea conexión a BD."""
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)


def analyze_books(conn) -> List[Dict[str, Any]]:
    """Analiza todos los libros en la BD."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, author_name, category, pdf_path, page_count, 
               paginated_at, source, source_id, source_hash, published,
               views, likes, average_rating, total_reviews, created_at
        FROM books
        ORDER BY id
    """)
    return cursor.fetchall()


def analyze_table_dependencies(conn, book_ids: List[int]) -> Dict[str, Dict[str, Any]]:
    """Analiza dependencias de las tablas hijas."""
    if not book_ids:
        return {}
    
    placeholders = ','.join(['%s'] * len(book_ids))
    cursor = conn.cursor()
    
    results = {}
    
    # book_pages
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count, MIN(page_number) as min_page, MAX(page_number) as max_page
        FROM book_pages WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['book_pages'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # chapters
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count
        FROM chapters WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['chapters'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # reviews
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count
        FROM reviews WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['reviews'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # reading_progress
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count, COUNT(DISTINCT user_id) as users
        FROM reading_progress WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['reading_progress'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # reading_sessions
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count, COUNT(DISTINCT user_id) as users
        FROM reading_sessions WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['reading_sessions'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # reading_daily_pages
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count, COUNT(DISTINCT user_id) as users, COUNT(DISTINCT day) as days
        FROM reading_daily_pages WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['reading_daily_pages'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # book_interactions
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count, COUNT(DISTINCT user_id) as users
        FROM book_interactions WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['book_interactions'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # featured_books
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count
        FROM featured_books WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['featured_books'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # forum_posts (book_id nullable, ON DELETE SET NULL)
    cursor.execute(f"""
        SELECT book_id, COUNT(*) as count
        FROM forum_posts WHERE book_id IN ({placeholders})
        GROUP BY book_id
    """, tuple(book_ids))
    results['forum_posts'] = {row['book_id']: dict(row) for row in cursor.fetchall()}
    
    # competitions (referencia por título, no FK)
    cursor.execute("""
        SELECT id, title, book_title FROM competitions
    """)
    competitions = cursor.fetchall()
    results['competitions'] = {c['book_title']: dict(c) for c in competitions}
    
    return results


def count_total_rows(conn, table: str, book_ids: Optional[List[int]] = None) -> int:
    """Cuenta filas totales en una tabla."""
    cursor = conn.cursor()
    if book_ids:
        placeholders = ','.join(['%s'] * len(book_ids))
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE book_id IN ({placeholders})", tuple(book_ids))
    else:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
    return cursor.fetchone()['cnt']


def simulate_reconstruction(
    conn,
    strategy: str,
    source_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Simula la reconstrucción según la estrategia elegida."""
    
    books = analyze_books(conn)
    book_ids = [b['id'] for b in books]
    
    if source_filter:
        books = [b for b in books if b.get('source') == source_filter]
        book_ids = [b['id'] for b in books]
    
    deps = analyze_table_dependencies(conn, book_ids)
    
    print(f"\n{'='*80}")
    print(f"SIMULACIÓN DRY-RUN - Estrategia: {strategy}")
    print(f"Filtro source: {source_filter or 'todos'}")
    print(f"Libros totales en BD: {len(analyze_books(conn))}")
    print(f"Libros a procesar: {len(books)}")
    print(f"{'='*80}")
    
    impacts = []
    
    # 1. books
    impacts.append(TableImpact(
        table_name="books",
        total_rows=len(analyze_books(conn)),
        rows_affected=len(books),
        rows_preserved=len(analyze_books(conn)) - len(books),
        action="rebuild" if strategy == "new-ids" else "update_in_place",
        description="Libros objetivo de reconstrucción. Con new-ids se insertan nuevos y se marcan viejos; con maintain-ids se actualizan en sitio."
    ))
    
    # 2. book_pages
    total_pages = sum(d.get('count', 0) for d in deps.get('book_pages', {}).values())
    impacts.append(TableImpact(
        table_name="book_pages",
        total_rows=count_total_rows(conn, 'book_pages', book_ids),
        rows_affected=total_pages,
        rows_preserved=0,
        action="rebuild" if strategy == "new-ids" else "delete_and_recreate",
        description="Páginas de libros objetivo. Se eliminan y regeneran con nuevo contenido. FK CASCADE desde books."
    ))
    
    # 3. chapters
    total_chapters = sum(d.get('count', 0) for d in deps.get('chapters', {}).values())
    impacts.append(TableImpact(
        table_name="chapters",
        total_rows=count_total_rows(conn, 'chapters', book_ids),
        rows_affected=total_chapters,
        rows_preserved=0,
        action="rebuild" if strategy == "new-ids" else "delete_and_recreate",
        description="Capítulos detectados. Se regeneran con nueva detección. FK CASCADE desde books."
    ))
    
    # 4. reviews (PRESERVAR)
    total_reviews = sum(d.get('count', 0) for d in deps.get('reviews', {}).values())
    impacts.append(TableImpact(
        table_name="reviews",
        total_rows=count_total_rows(conn, 'reviews', book_ids),
        rows_affected=0,
        rows_preserved=total_reviews,
        action="preserve",
        description="Reseñas de usuarios. DEBEN CONSERVARSE. FK CASCADE desde books - si se borran libros, se borran reseñas. Con maintain-ids se conservan automáticamente; con new-ids requieren migración de book_id."
    ))
    
    # 5. reading_progress (PRESERVAR)
    total_progress = sum(d.get('count', 0) for d in deps.get('reading_progress', {}).values())
    unique_users_progress = sum(d.get('users', 0) for d in deps.get('reading_progress', {}).values())
    impacts.append(TableImpact(
        table_name="reading_progress",
        total_rows=count_total_rows(conn, 'reading_progress', book_ids),
        rows_affected=0,
        rows_preserved=total_progress,
        action="preserve" if strategy == "maintain-ids" else "rebuild_with_fk_update",
        description=f"Progreso de {unique_users_progress} usuarios. DEBE CONSERVARSE. Con maintain-ids intacto; con new-ids requiere UPDATE de book_id."
    ))
    
    # 6. reading_sessions (PRESERVAR)
    total_sessions = sum(d.get('count', 0) for d in deps.get('reading_sessions', {}).values())
    unique_users_sessions = sum(d.get('users', 0) for d in deps.get('reading_sessions', {}).values())
    impacts.append(TableImpact(
        table_name="reading_sessions",
        total_rows=count_total_rows(conn, 'reading_sessions', book_ids),
        rows_affected=0,
        rows_preserved=total_sessions,
        action="preserve" if strategy == "maintain-ids" else "rebuild_with_fk_update",
        description=f"Sesiones activas de {unique_users_sessions} usuarios. DEBE CONSERVARSE."
    ))
    
    # 7. reading_daily_pages (PRESERVAR)
    total_daily = sum(d.get('count', 0) for d in deps.get('reading_daily_pages', {}).values())
    unique_users_daily = sum(d.get('users', 0) for d in deps.get('reading_daily_pages', {}).values())
    unique_days = sum(d.get('days', 0) for d in deps.get('reading_daily_pages', {}).values())
    impacts.append(TableImpact(
        table_name="reading_daily_pages",
        total_rows=count_total_rows(conn, 'reading_daily_pages', book_ids),
        rows_affected=0,
        rows_preserved=total_daily,
        action="preserve" if strategy == "maintain-ids" else "rebuild_with_fk_update",
        description=f"Meta diaria: {unique_users_daily} usuarios, {unique_days} días. DEBE CONSERVARSE."
    ))
    
    # 8. book_interactions (PRESERVAR)
    total_interactions = sum(d.get('count', 0) for d in deps.get('book_interactions', {}).values())
    unique_users_interactions = sum(d.get('users', 0) for d in deps.get('book_interactions', {}).values())
    impacts.append(TableImpact(
        table_name="book_interactions",
        total_rows=count_total_rows(conn, 'book_interactions', book_ids),
        rows_affected=0,
        rows_preserved=total_interactions,
        action="preserve" if strategy == "maintain-ids" else "rebuild_with_fk_update",
        description=f"Likes/dislikes de {unique_users_interactions} usuarios. DEBE CONSERVARSE. UNIQUE(book_id, user_id)."
    ))
    
    # 9. featured_books (REEVALUAR)
    total_featured = sum(d.get('count', 0) for d in deps.get('featured_books', {}).values())
    impacts.append(TableImpact(
        table_name="featured_books",
        total_rows=count_total_rows(conn, 'featured_books', book_ids),
        rows_affected=total_featured,
        rows_preserved=0,
        action="rebuild" if strategy == "new-ids" else "delete_and_recreate",
        description="Libros destacados. Se recrean tras reconstrucción. FK CASCADE desde books."
    ))
    
    # 10. forum_posts (PRESERVAR - SET NULL)
    total_forum = sum(d.get('count', 0) for d in deps.get('forum_posts', {}).values())
    impacts.append(TableImpact(
        table_name="forum_posts",
        total_rows=count_total_rows(conn, 'forum_posts', book_ids),
        rows_affected=0,
        rows_preserved=total_forum,
        action="preserve",
        description="Posts del foro que referencian libros. ON DELETE SET NULL - si se borra libro, book_id pasa a NULL. DEBE CONSERVARSE."
    ))
    
    # 11. competitions (REEVALUAR - sin FK real)
    book_titles_in_competitions = set(deps.get('competitions', {}).keys())
    titles_in_books = set(b['title'] for b in books)
    matching = book_titles_in_competitions & titles_in_books
    impacts.append(TableImpact(
        table_name="competitions",
        total_rows=len(deps.get('competitions', {})),
        rows_affected=len(matching),
        rows_preserved=len(deps.get('competitions', {})) - len(matching),
        action="manual_review",
        description=f"Competencias que referencian libros por título. {len(matching)} coinciden. Sin FK - requiere revisión manual tras reconstrucción."
    ))
    
    # 12. rayos_transactions (PRESERVAR - book_id nullable)
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT COUNT(*) as cnt FROM rayos_transactions WHERE book_id IN ({','.join(['%s']*len(book_ids))})
    """, tuple(book_ids))
    total_rayos = cursor.fetchone()['cnt']
    impacts.append(TableImpact(
        table_name="rayos_transactions",
        total_rows=total_rayos,
        rows_affected=0,
        rows_preserved=total_rayos,
        action="preserve" if strategy == "maintain-ids" else "rebuild_with_fk_update",
        description="Transacciones de Rayos con book_id. FK user_id CASCADE, book_id nullable. DEBE CONSERVARSE."
    ))
    
    # Imprimir tabla de impactos
    print(f"\n{'Tabla':<30} {'Total':>8} {'Afec.':>8} {'Conserv.':>8} {'Acción':<30} {'Descripción'}")
    print("-" * 120)
    for imp in impacts:
        print(f"{imp.table_name:<30} {imp.total_rows:>8} {imp.rows_affected:>8} {imp.rows_preserved:>8} {imp.action:<30} {imp.description[:50]}")
    
    # Resumen por categoría
    print(f"\n{'='*80}")
    print("RESUMEN POR CATEGORÍA")
    print(f"{'='*80}")
    
    categoria_A = [i for i in impacts if i.action in ('rebuild', 'delete_and_recreate', 'update_in_place')]
    categoria_B = [i for i in impacts if i.action in ('preserve', 'rebuild_with_fk_update')]
    categoria_C = [i for i in impacts if i.action == 'preserve' and 'forum' in i.table_name.lower()]
    categoria_D = [i for i in impacts if i.action in ('rebuild', 'manual_review') and i.table_name in ('featured_books', 'competitions')]
    
    print(f"\nA. CATÁLOGO (reconstruir):")
    for i in categoria_A:
        print(f"   {i.table_name}: {i.rows_affected} filas afectadas")
    
    print(f"\nB. DATOS DE USUARIO (conservar):")
    for i in categoria_B:
        if i.table_name not in ('forum_posts',):
            print(f"   {i.table_name}: {i.rows_preserved} filas conservadas")
    
    print(f"\nC. FORO (conservar):")
    for i in categoria_C:
        print(f"   {i.table_name}: {i.rows_preserved} filas conservadas")
    
    print(f"\nD. ADMINISTRATIVOS (reevaluar):")
    for i in categoria_D:
        print(f"   {i.table_name}: {i.rows_affected} filas afectadas, {i.rows_preserved} conservadas")
    
    # Análisis de IDs
    print(f"\n{'='*80}")
    print(f"ANÁLISIS DE ESTRATEGIA DE IDs: {strategy}")
    print(f"{'='*80}")
    
    if strategy == "maintain-ids":
        print("""
OPCIÓN A: MANTENER IDs ACTUALES
--------------------------------
✅ Ventajas:
   - Reviews, progreso, sesiones, interacciones, Rayos: SE CONSERVAN AUTOMÁTICAMENTE
   - No requiere UPDATE masivo de FKs en tablas hijas
   - URLs existentes (/books/123) siguen funcionando
   - Referencias históricas intactas
   - Frontend no necesita cambios
   - Competencias por título: funcionan si títulos no cambian

❌ Riesgos:
   - Libros corruptos actuales mantienen su ID (potencial confusión)
   - IDs no contiguos si se eliminan algunos
   - Si un libro se elimina completamente, su ID queda huérfano
   
🔧 Implementación:
   1. UPDATE books SET content=..., pdf_path=..., page_count=..., paginated_at=... WHERE id=X
   2. DELETE FROM book_pages WHERE book_id=X; INSERT nuevas páginas
   3. DELETE FROM chapters WHERE book_id=X; INSERT nuevos capítulos
   4. featured_books: DELETE e INSERT con mismo book_id
""")
    elif strategy == "new-ids":
        print("""
OPCIÓN B: NUEVOS IDs PARA LIBROS RECONSTRUIDOS
----------------------------------------------
✅ Ventajas:
   - Limpieza total: IDs nuevos, sin "fantasmas" de libros corruptos
   - Posibilidad de renombrar/reorganizar catálogo limpio
   
❌ Riesgos CRÍTICOS:
   - Reviews: REQUIERE UPDATE masivo de book_id (ON DELETE CASCADE destruiría datos)
   - reading_progress: REQUIERE UPDATE masivo
   - reading_sessions: REQUIERE UPDATE masivo  
   - reading_daily_pages: REQUIERE UPDATE masivo
   - book_interactions: REQUIERE UPDATE masivo (UNIQUE constraint!)
   - rayos_transactions: REQUIERE UPDATE masivo
   - featured_books: REQUIERE UPDATE masivo
   - forum_posts: book_id pasa a NULL automáticamente (ON DELETE SET NULL) - PIERDE VINCULACIÓN
   - URLs rotas: /books/123 ya no existe
   - Frontend cache roto
   - Competencias por título: rotas si títulos cambian
   
🔧 Implementación (MUY COMPLEJA):
   1. Mapear old_id -> new_id para cada libro
   2. INSERT nuevos libros con nuevos IDs
   3. UPDATE reviews SET book_id=new_id WHERE book_id=old_id
   4. UPDATE reading_progress SET book_id=new_id WHERE book_id=old_id
   5. ... (todas las tablas con FK a books)
   6. SOLO ENTONCES: DELETE FROM books WHERE id IN (old_ids)
   
⚠️  NO RECOMENDADO sin plan de migración exhaustivo y ventana de mantenimiento.
""")
    elif strategy == "hybrid":
        print("""
OPCIÓN C: HÍBRIDA (RECOMENDADA)
-------------------------------
Estrategia:
   - Libros CON datos de usuario (reviews, progreso, likes): maintain-ids
   - Libros SIN datos de usuario: new-ids (o maintain-ids, da igual)
   - Libros corruptos puros: new-ids con marca de "reemplazado"

✅ Mejores de ambos mundos:
   - Usuarios no pierden su historial
   - Limpieza de IDs donde no duele
   - Menos UPDATEs masivos
   
🔧 Implementación:
   1. Clasificar cada libro: has_user_data = bool(reviews|progress|interactions)
   2. Si has_user_data: maintain-ids (UPDATE in place)
   3. Si no has_user_data: new-ids (INSERT nuevo, DELETE viejo)
   4. featured_books: actualizar book_id según mapeo
   5. Competencias: revisión manual
""")
    
    return {
        "strategy": strategy,
        "books_processed": len(books),
        "impacts": [vars(i) for i in impacts],
        "recommendation": "hybrid" if strategy == "hybrid" else ("maintain-ids" if strategy == "maintain-ids" else "NOT_RECOMMENDED")
    }


def main():
    parser = argparse.ArgumentParser(description="Simulación DRY-RUN de reconstrucción del catálogo")
    parser.add_argument("--database-url", required=True, help="PostgreSQL DATABASE_URL")
    parser.add_argument("--strategy", choices=["maintain-ids", "new-ids", "hybrid"], default="hybrid",
                       help="Estrategia de IDs")
    parser.add_argument("--source-filter", help="Filtrar solo libros de esta fuente (gutenberg, local, seed, pdf, etc.)")
    
    args = parser.parse_args()
    
    try:
        conn = get_db_connection(args.database_url)
    except Exception as e:
        print(f"Error conectando a BD: {e}")
        return 1
    
    try:
        result = simulate_reconstruction(conn, args.strategy, args.source_filter)
        print(f"\n{'='*80}")
        print("RECOMENDACIÓN FINAL")
        print(f"{'='*80}")
        print(f"Estrategia recomendada: {result['recommendation']}")
        print("Ver análisis arriba para justificación.")
        print("\n⚠️  ESTO ES SOLO SIMULACIÓN - NO SE MODIFICÓ NADA")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())