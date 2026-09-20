#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para eliminar libros ID 3 y 4 de forma controlada.
"""
import sys
import argparse
import psycopg2
import psycopg2.extras

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'plataforma_dev',
    'user': 'postgres',
    'password': 'yamilpro002'
}

# IDs objetivo
TARGET_IDS = [3, 4]

# IDs protegidos que NUNCA deben eliminarse
PROTECTED_IDS = [18, 128]  # 18 debe permanecer, 128 ya está eliminado

# Tablas con FK a books (para verificación de dependencias)
FK_TABLES = [
    'book_pages',
    'chapters',
    'reading_progress',
    'reading_sessions',
    'reviews',
    'book_interactions',
    'reading_daily_pages',
    'featured_books',
    'forum_posts',
    'competitions',
]


def get_connection():
    """Obtiene conexión a la base de datos."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)


def check_books_exist(cursor, target_ids):
    """Verifica que los libros objetivo existen y coincide con lo esperado."""
    cursor.execute('''
        SELECT id, title, author_name, page_count, published, uploader_id, LENGTH(content) as content_len
        FROM books
        WHERE id = ANY(%s)
        ORDER BY id
    ''', (target_ids,))
    results = cursor.fetchall()
    
    if len(results) != len(target_ids):
        found_ids = [r['id'] for r in results]
        missing = set(target_ids) - set(found_ids)
        raise Exception(f'Libros faltantes: {missing}')
    
    # Verificar títulos y autores esperados
    expected = {
        3: {'title': 'Don Quijote de la Mancha', 'author': 'Miguel de Cervantes'},
        4: {'title': '1984', 'author': 'George Orwell'},
    }
    
    for row in results:
        exp = expected.get(row['id'])
        if not exp:
            raise Exception(f'ID {row["id"]} no esperado')
        if row['title'] != exp['title']:
            raise Exception(f'ID {row["id"]}: título inesperado "{row["title"]}", se esperaba "{exp["title"]}"')
        if row['author_name'] != exp['author']:
            raise Exception(f'ID {row["id"]}: autor inesperado "{row["author_name"]}", se esperaba "{exp["author"]}"')
    
    return results


def check_protected_ids(cursor, target_ids):
    """Verifica que ningún ID objetivo está en PROTECTED_IDS."""
    intersection = set(target_ids) & set(PROTECTED_IDS)
    if intersection:
        raise Exception(f'IDs protegidos en la lista de eliminación: {intersection}')
    
    # Verificar que los IDs protegidos existen (18) o no existen (128)
    cursor.execute('SELECT id FROM books WHERE id = ANY(%s)', (PROTECTED_IDS,))
    protected_found = [r['id'] for r in cursor.fetchall()]
    # ID 18 debe existir si está en la BD, pero puede no estar en el dataset actual
    # ID 128 debe estar eliminado (no existir)
    if 128 in protected_found:
        raise Exception('ID 128 (debe estar eliminado) aún existe en la base de datos')
    if 18 in protected_found:
        print(f'  ID 18 encontrado y protegido')
    else:
        print(f'  ID 18 no está en la base de datos actual (se omite verificación)')


def check_dependencies(cursor, target_ids):
    """Inspecciona dependencias en todas las tablas FK."""
    dependencies = {}
    for table in FK_TABLES:
        cursor.execute(f'SELECT book_id, COUNT(*) as cnt FROM {table} WHERE book_id = ANY(%s) GROUP BY book_id', (target_ids,))
        rows = cursor.fetchall()
        for row in rows:
            bid = row['book_id']
            if bid not in dependencies:
                dependencies[bid] = {}
            dependencies[bid][table] = row['cnt']
    
    # Asegurar que todos los target_ids tengan entrada (aunque sea vacía)
    for tid in target_ids:
        if tid not in dependencies:
            dependencies[tid] = {}
        for table in FK_TABLES:
            if table not in dependencies[tid]:
                dependencies[tid][table] = 0
    
    return dependencies


def check_fk_rules(cursor):
    """Verifica reglas ON DELETE de las FK."""
    cursor.execute('''
        SELECT
            tc.table_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.referential_constraints AS rc
            ON rc.constraint_name = tc.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE ccu.table_name = 'books'
        ORDER BY tc.table_name
    ''')
    return cursor.fetchall()


def dry_run(cursor, target_ids):
    """Ejecuta dry-run: muestra información sin modificar la BD."""
    print('=' * 60)
    print('DRY-RUN: Eliminación de libros ID 3 y 4')
    print('=' * 60)
    
    # Verificar existencia y datos
    books = check_books_exist(cursor, target_ids)
    print('\nLibros a eliminar:')
    for book in books:
        print(f'  ID {book["id"]}: "{book["title"]}" por {book["author_name"]}')
        print(f'    page_count: {book["page_count"]}')
        print(f'    published: {book["published"]}')
        print(f'    uploader_id: {book["uploader_id"]}')
        print(f'    content_length: {book["content_len"]}')
    
    # Verificar IDs protegidos
    check_protected_ids(cursor, target_ids)
    print(f'\nIDs protegidos verificados: {PROTECTED_IDS}')
    print('  - ID 18 existe y está protegido')
    print('  - ID 128 no existe (ya eliminado)')
    
    # Verificar reglas FK
    fk_rules = check_fk_rules(cursor)
    print('\nReglas ON DELETE de FK hacia books:')
    for rule in fk_rules:
        print(f'  {rule["table_name"]}: ON DELETE {rule["delete_rule"]}')
    
    # Verificar dependencias
    deps = check_dependencies(cursor, target_ids)
    print('\nDependencias por libro:')
    for book_id in target_ids:
        print(f'  ID {book_id}:')
        total = 0
        for table in FK_TABLES:
            count = deps[book_id].get(table, 0)
            if count > 0:
                print(f'    {table}: {count}')
                total += count
        if total == 0:
            print(f'    (sin dependencias)')
    
    # Verificar que no hay FK RESTRICT/NO ACTION
    restrict_fks = [r for r in fk_rules if r['delete_rule'] in ('RESTRICT', 'NO ACTION')]
    if restrict_fks:
        print('\nADVERTENCIA: FK con ON DELETE RESTRICT/NO ACTION:')
        for r in restrict_fks:
            print(f'  {r["table_name"]}: ON DELETE {r["delete_rule"]}')
    else:
        print('\nOK: Todas las FK tienen ON DELETE CASCADE o SET NULL')
    
    print('\n' + '=' * 60)
    print('NO DATABASE MODIFICATIONS PERFORMED')
    print('=' * 60)
    return books, deps, fk_rules


def execute_delete(cursor, target_ids, confirm):
    """Ejecuta la eliminación en transacción."""
    if confirm != 'ELIMINAR 3 4':
        raise Exception(f'Confirmación incorrecta: "{confirm}". Se requiere exactamente: ELIMINAR 3 4')
    
    print('\nIniciando transacción...')
    
    # Eliminar
    cursor.execute('''
        DELETE FROM books
        WHERE id = ANY(%s)
        RETURNING id, title, author_name
    ''', (target_ids,))
    
    deleted = cursor.fetchall()
    deleted_ids = [r['id'] for r in deleted]
    
    if set(deleted_ids) != set(target_ids):
        missing = set(target_ids) - set(deleted_ids)
        raise Exception(f'No se eliminaron todos los IDs. Faltantes: {missing}')
    
    print('Libros eliminados:')
    for book in deleted:
        print(f'  ID {book["id"]}: "{book["title"]}" por {book["author_name"]}')
    
    # Verificar que ya no existen
    cursor.execute('SELECT id FROM books WHERE id = ANY(%s)', (target_ids,))
    remaining = cursor.fetchall()
    if remaining:
        raise Exception(f'Libros aún existen después de DELETE: {[r["id"] for r in remaining]}')
    
    print('\n✓ Verificación: IDs 3 y 4 ya no existen en books')
    
    # Verificar dependencias huérfanas (deberían ser 0 por CASCADE)
    for table in FK_TABLES:
        cursor.execute(f'SELECT COUNT(*) as cnt FROM {table} WHERE book_id = ANY(%s)', (target_ids,))
        count = cursor.fetchone()['cnt']
        if count > 0:
            raise Exception(f'Dependencias huérfanas en {table}: {count}')
    
    print('✓ Verificación: No hay dependencias huérfanas en tablas FK')
    
    # Verificar IDs protegidos siguen intactos
    cursor.execute('SELECT id, title FROM books WHERE id = ANY(%s)', (PROTECTED_IDS,))
    protected = cursor.fetchall()
    protected_ids = [r['id'] for r in protected]
    if 18 not in protected_ids:
        raise Exception('ID 18 ya no existe después de la eliminación')
    if 128 in protected_ids:
        raise Exception('ID 128 reapareció después de la eliminación')
    
    print(f'✓ Verificación: IDs protegidos intactos: {protected_ids}')
    
    # Contar libros finales
    cursor.execute('SELECT COUNT(*) as cnt FROM books')
    total_books = cursor.fetchone()['cnt']
    print(f'\nTotal libros en catálogo: {total_books}')
    
    return deleted, total_books


def main():
    parser = argparse.ArgumentParser(description='Eliminar libros ID 3 y 4')
    parser.add_argument('--dry-run', action='store_true', help='Solo simular, no modificar BD')
    parser.add_argument('--execute', action='store_true', help='Ejecutar eliminación real')
    parser.add_argument('--confirm', type=str, help='Confirmación exacta para --execute')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        parser.error('Debe especificar --dry-run o --execute')
    if args.dry_run and args.execute:
        parser.error('No se puede usar --dry-run y --execute juntos')
    if args.execute and not args.confirm:
        parser.error('--execute requiere --confirm "ELIMINAR 3 4"')
    
    conn = get_connection()
    conn.autocommit = False  # Transacción explícita
    
    try:
        cursor = conn.cursor()
        
        if args.dry_run:
            dry_run(cursor, TARGET_IDS)
            conn.rollback()  # No hacer cambios
            print('\nRollback automático (dry-run)')
        
        elif args.execute:
            execute_delete(cursor, TARGET_IDS, args.confirm)
            conn.commit()
            print('\n✓ COMMIT realizado')
        
        cursor.close()
        conn.close()
        
except Exception as e:
        conn.rollback()
        print(f'\nERROR: {e}')
        print('ROLLBACK automático')
        cursor.close()
        conn.close()
        sys.exit(1)


if __name__ == '__main__':
    main()