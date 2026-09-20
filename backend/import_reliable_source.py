#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_reliable_source.py — Importador de libros desde fuente confiable.

Diseñado para FASE 2A: reconstrucción controlada del catálogo.
Solo procesa UNA fuente a la vez, valida exhaustivamente, NO publica si falla.

Uso:
  python import_reliable_source.py --source gutenberg --book-id 1342 --dry-run
  python import_reliable_source.py --source local --pdf-path ./libro.pdf --dry-run

NO EJECUTAR CONTRA PRODUCCIÓN SIN APROBACIÓN EXPLÍCITA.
"""

import os
import sys
import hashlib
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Añadir backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hash_utils import calcular_hash_archivo, calcular_hash_texto

import lectura

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_reliable")


class ImportResult:
    """Resultado de importación de un libro."""
    def __init__(self):
        self.source = None
        self.source_url = None
        self.source_id = None
        self.source_format = None
        self.source_hash = None
        self.original_file_path = None
        self.original_file_size = 0
        self.title = None
        self.author = None
        self.content = None
        self.content_length = 0
        self.pages = []
        self.page_count = 0
        self.chapters = []
        self.chapter_count = 0
        self.short_pages = 0
        self.duplicate_page_hashes = 0
        self.validation_errors = []
        self.is_valid = False
        self.pdf_valid = False
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "source_url": self.source_url,
            "source_id": self.source_id,
            "source_format": self.source_format,
            "source_hash": self.source_hash,
            "original_file": self.original_file_path,
            "original_file_size": self.original_file_size,
            "title": self.title,
            "author": self.author,
            "content_length": self.content_length,
            "page_count": self.page_count,
            "chapter_count": self.chapter_count,
            "short_pages": self.short_pages,
            "duplicate_page_hashes": self.duplicate_page_hashes,
            "validation_errors": self.validation_errors,
            "is_valid": self.is_valid,
            "pdf_valid": self.pdf_valid,
        }


# calcular_hash_archivo se importa de hash_utils


def validar_archivo_pdf_local(pdf_path: str) -> Tuple[bool, list]:
    """Valida un archivo PDF local (existencia, magic bytes, páginas > 0)."""
    errors = []
    
    if not os.path.exists(pdf_path):
        errors.append(f"Archivo no encontrado: {pdf_path}")
        return False, errors
    
    if not os.path.isfile(pdf_path):
        errors.append(f"La ruta no es un archivo: {pdf_path}")
        return False, errors
    
    # Verificar magic bytes
    try:
        with open(pdf_path, "rb") as f:
            header = f.read(1024)
        if b"%PDF" not in header[:1024]:
            errors.append("Archivo no es un PDF válido (falta magic bytes %PDF)")
            return False, errors
    except Exception as e:
        errors.append(f"No se puede abrir el archivo: {e}")
        return False, errors
    
    # Verificar que tiene páginas
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        if len(reader.pages) == 0:
            errors.append("PDF sin páginas")
            return False, errors
    except Exception as e:
        errors.append(f"Error leyendo estructura PDF: {e}")
        return False, errors
    
    return True, []


def importar_desde_pdf_local(
    pdf_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    category: str = "Ficción"
) -> ImportResult:
    """Importa un libro desde un PDF local con validación completa."""
    result = ImportResult()
    result.source = "local"
    result.source_url = pdf_path
    result.source_id = os.path.basename(pdf_path)
    result.source_format = "application/pdf"
    result.original_file_path = pdf_path
    result.original_file_size = os.path.getsize(pdf_path)
    result.source_hash = calcular_hash_archivo(pdf_path)
    
    logger.info(f"Validando PDF: {pdf_path} ({result.original_file_size} bytes)")
    
    # Paso 1: Validar archivo
    pdf_valid, errors = validar_archivo_pdf_local(pdf_path)
    result.pdf_valid = pdf_valid
    if not pdf_valid:
        result.validation_errors.extend(errors)
        return result
    
    # Paso 2: Pipeline central (extracción + validación)
    logger.info("Ejecutando pipeline central de contenido...")
    try:
        procesado = lectura.procesar_contenido_para_publicacion(pdf_path=pdf_path, fuente="pdf")
    except Exception as e:
        result.validation_errors.append(f"Error en pipeline central: {e}")
        return result
    
    validacion = procesado["validacion"]
    if not validacion["valid"]:
        result.validation_errors.extend(validacion["errors"])
        result.content = procesado["content"]
        return result
    
    result.content = procesado["content"]
    result.content_length = len(result.content)
    result.pages = procesado["paginas"]
    result.page_count = len(result.pages)
    result.chapters = procesado["capitulos"]
    result.chapter_count = len(result.chapters)
    
    # Paso 3: Validaciones adicionales
    if not result.pages:
        result.validation_errors.append("No se generaron páginas")
        return result
    
    # Contar páginas cortas (< 50 chars)
    result.short_pages = sum(1 for p in result.pages if len(p.strip()) < 50)
    
    # Contar hashes de página duplicados
    page_hashes = []
    for p in result.pages:
        h = hashlib.sha256(p.encode()).hexdigest()
        page_hashes.append(h)
    from collections import Counter
    hash_counts = Counter(page_hashes)
    result.duplicate_page_hashes = sum(1 for count in hash_counts.values() if count > 1)
    
    # Extraer metadatos del PDF si no se proporcionaron
    if not title or not author:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            meta = reader.metadata
            if meta:
                if not title and meta.get("/Title"):
                    title = meta["/Title"].strip()
                if not author and meta.get("/Author"):
                    author = meta["/Author"].strip()
        except Exception:
            pass
    
    result.title = title or os.path.splitext(os.path.basename(pdf_path))[0]
    result.author = author or "Desconocido"
    
    result.is_valid = True
    return result


def importar_desde_gutenberg(
    book_id: int,
    category: str = "Clásicos"
) -> ImportResult:
    """Importa un libro desde Project Gutenberg con validación completa."""
    import urllib.request
    import json
    
    result = ImportResult()
    result.source = "gutenberg"
    result.source_id = str(book_id)
    result.source_format = "text/plain"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    # Obtener metadatos
    meta_url = f"https://gutendex.com/books/{book_id}"
    try:
        req = urllib.request.Request(meta_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            meta_data = json.loads(response.read().decode())
    except Exception as e:
        result.validation_errors.append(f"Error obteniendo metadatos: {e}")
        return result
    
    result.title = meta_data.get("title", f"Gutenberg Book {book_id}")
    authors = meta_data.get("authors", [])
    result.author = authors[0]["name"] if authors else "Project Gutenberg"
    
    # Buscar URL de texto plano
    text_url = None
    for fmt, url in meta_data.get("formats", {}).items():
        if fmt.startswith("text/plain"):
            text_url = url
            break
    
    if not text_url:
        result.validation_errors.append("No se encontró versión en texto plano")
        return result
    
    result.source_url = text_url
    
    # Descargar contenido
    try:
        req2 = urllib.request.Request(text_url, headers=headers)
        with urllib.request.urlopen(req2, timeout=60) as response:
            content = response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        result.validation_errors.append(f"Error descargando contenido: {e}")
        return result
    
    # Recortar a 100k chars (consistente con endpoint actual)
    contenido_recortado = content[:100000]
    result.source_hash = calcular_hash_texto(contenido_recortado)
    result.content = contenido_recortado
    result.content_length = len(contenido_recortado)
    
    # Pipeline: paginación + validación
    logger.info("Paginando y validando contenido de Gutenberg...")
    validacion = lectura.validar_contenido_libro(contenido_recortado, None, fuente="gutenberg")
    if not validacion["valid"]:
        result.validation_errors.extend(validacion["errors"])
        return result
    
    result.pages, result.chapters = lectura.paginar_desde_contenido_con_capitulos(contenido_recortado)
    if not result.pages:
        result.validation_errors.append("No se pudieron generar páginas")
        return result
    
    result.page_count = len(result.pages)
    result.chapter_count = len(result.chapters)
    
    # Validaciones adicionales
    result.short_pages = sum(1 for p in result.pages if len(p.strip()) < 50)
    
    page_hashes = [hashlib.sha256(p.encode()).hexdigest() for p in result.pages]
    from collections import Counter
    hash_counts = Counter(page_hashes)
    result.duplicate_page_hashes = sum(1 for count in hash_counts.values() if count > 1)
    
    result.is_valid = True
    return result


def main():
    parser = argparse.ArgumentParser(description="Importador de libros desde fuente confiable")
    parser.add_argument("--source", choices=["gutenberg", "local"], required=True,
                       help="Fuente del libro")
    parser.add_argument("--book-id", type=int, help="ID de Gutenberg (si source=gutenberg)")
    parser.add_argument("--pdf-path", help="Ruta al PDF local (si source=local)")
    parser.add_argument("--title", help="Título (opcional, para PDF local)")
    parser.add_argument("--author", help="Autor (opcional, para PDF local)")
    parser.add_argument("--category", default="Ficción", help="Categoría")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Solo simular, no insertar en BD (por defecto True)")
    parser.add_argument("--execute", action="store_true", 
                       help="Ejecutar realmente (requiere --no-dry-run implícito)")
    
    args = parser.parse_args()
    
    if args.execute:
        args.dry_run = False
    
    if args.source == "gutenberg" and not args.book_id:
        parser.error("--book-id requerido para source=gutenberg")
    if args.source == "local" and not args.pdf_path:
        parser.error("--pdf-path requerido para source=local")
    
    logger.info(f"=== INICIO IMPORTACIÓN (dry_run={args.dry_run}) ===")
    logger.info(f"Fuente: {args.source}")
    
    if args.source == "gutenberg":
        result = importar_desde_gutenberg(args.book_id, args.category)
    else:
        result = importar_desde_pdf_local(
            args.pdf_path, args.title, args.author, args.category
        )
    
    # Mostrar resultado
    print("\n" + "="*60)
    print("RESULTADO DE IMPORTACIÓN")
    print("="*60)
    for k, v in result.to_dict().items():
        print(f"  {k}: {v}")
    print("="*60)
    
    if result.is_valid:
        print("[OK] LIBRO VALIDO - Listo para publicacion")
        if not args.dry_run:
            print("[WARN] EJECUCION REAL NO IMPLEMENTADA EN ESTE SCRIPT")
            print("   Usar endpoint /admin/gutenberg/fetch o /api/books con PDF")
    else:
        print("[FAIL] LIBRO RECHAZADO")
        for err in result.validation_errors:
            print(f"   - {err}")
    
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())