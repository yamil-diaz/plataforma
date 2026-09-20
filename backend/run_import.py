#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_import.py — Orquestador principal de importación masiva de libros.

Soporta DOS fuentes:
  1. PDFs locales (directorio de archivos)
  2. Project Gutenberg (catálogo JSON con gutenberg_ids)

Ejecuta un lote controlado con pausas entre libros para no saturar Render.

Uso:
  # Importar desde catálogo Gutenberg
  python run_import.py --source gutenberg --catalog catalog.json --execute

  # Importar desde directorio de PDFs
  python run_import.py --source pdfs --dir ./mis_pdfs --execute

  # Dry-run (sin inserción)
  python run_import.py --source gutenberg --catalog catalog.json --dry-run

  # Configurar lote
  python run_import.py --source gutenberg --catalog catalog.json --execute --batch-size 3 --rate-limit 3

El proceso es REANUDABLE: si se interrumpe, al ejecutar de nuevo omite los libros ya procesados.
"""

import os
import sys
import json
import time
import uuid
import shutil
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
import psycopg2.extras
from storage_config import STORAGE_DIR, STORAGE_BOOKS, STORAGE_COVERS, STORAGE_TEMP, ensure_storage_directories
from hash_utils import calcular_hash_archivo, calcular_hash_texto

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_import")


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def get_db():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL", ""),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def load_existing_hashes() -> Set[str]:
    hashes: Set[str] = set()
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT source_hash FROM books WHERE source_hash IS NOT NULL")
                for row in cur.fetchall():
                    h = row["source_hash"]
                    if h:
                        hashes.add(h)
        finally:
            conn.close()
    except Exception as e:
        logger.warning("No se pudieron cargar hashes: %s", e)
    return hashes


def load_existing_title_author() -> Set[Tuple[str, str]]:
    pairs: Set[Tuple[str, str]] = set()
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT LOWER(TRIM(title)) as t, LOWER(TRIM(author_name)) as a FROM books")
                for row in cur.fetchall():
                    if row["t"] and row["a"]:
                        pairs.add((row["t"], row["a"]))
        finally:
            conn.close()
    except Exception as e:
        logger.warning("No se pudieron cargar títulos/autores: %s", e)
    return pairs


# ---------------------------------------------------------------------------
# Manifest (reanudable)
# ---------------------------------------------------------------------------

class Manifest:
    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {
            "import_id": None,
            "started_at": None,
            "total": 0,
            "status": "pending",
            "items": {},
        }
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.data["items"] = {}

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        shutil.move(tmp, self.path)

    def start(self, total: int):
        self.data["import_id"] = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        self.data["started_at"] = datetime.now(timezone.utc).isoformat()
        self.data["total"] = total
        self.data["status"] = "in_progress"
        self.save()

    def key_for(self, item: Dict) -> str:
        """Generate unique key for an item."""
        if "gutenberg_id" in item:
            return f"gutenberg:{item['gutenberg_id']}"
        if "path" in item:
            return f"pdf:{item['path']}"
        return f"title:{item.get('title', '')}:{item.get('author', '')}"

    def is_done(self, key: str, item_hash: str = None) -> bool:
        entry = self.data["items"].get(key)
        if not entry:
            return False
        if item_hash and entry.get("hash") != item_hash:
            return False
        return entry.get("status") in ("imported", "rejected", "duplicate")

    def record(self, key: str, result: Dict):
        self.data["items"][key] = result
        self.save()

    def finish(self, summary: Dict):
        self.data["status"] = "completed"
        self.data["summary"] = summary
        self.save()


# ---------------------------------------------------------------------------
# Gutenberg import
# ---------------------------------------------------------------------------

def clean_gutenberg_text(text: str) -> str:
    """Remove common Gutenberg headers, footers and illustration markers.
    
    These are NOT content — they are metadata/artifacts that trigger
    the pathological content detector (e.g. [Illustration] repeated 100+ times).
    """
    import re
    lines = text.split('\n')
    cleaned = []
    in_header = True
    for line in lines:
        stripped = line.strip()
        # Skip Gutenberg header block
        if in_header:
            if stripped.startswith('*** START OF') or stripped.startswith('*** START THE'):
                in_header = False
                continue
            if stripped.startswith('*** END OF') or stripped.startswith('*** END THE'):
                break
            # Skip known header lines
            if any(stripped.startswith(p) for p in [
                'The Project Gutenberg eBook of',
                'The Project Gutenberg Etext of',
                'The Project Gutenberg EBook of',
                'This eBook is for the use of',
                'at www.gutenberg.org.',
                'of the Project Gutenberg License',
                'with almost no restrictions',
                'you will have to check the laws',
                'before using this eBook.',
                'updated editions will replace',
                'the old one',
                'the Project Gutenberg Literary Archive',
                'Foundation is a 501(c)(3)',
                'additional terms will be added',
                'Gutenberg is a registered trademark',
                'If you do not charge anything',
                'you must comply with the',
                'located in the United States',
                'you are located outside',
                'U.S. laws alone can sovereign',
                'International copyright laws',
                'We do not claim a right',
                'may apply to the work',
                'including copyright laws.',
                'MOST PEOPLE START AT',
                'This website includes information',
                'how to make donations',
                'how to help produce',
                'subscribe to our email newsletter',
                'Please take a look at',
                'TRANSCRIBER\'S NOTE',
                'Produced by',
                'E-text prepared by',
                'Text file produced by',
                'HTML file produced by',
                'End of the Project Gutenberg',
                'END OF THE PROJECT GUTENBERG',
                '*** END OF THIS PROJECT GUTENBERG',
                '*** END OF THE PROJECT GUTENBERG',
            ]):
                continue
            # Skip blank/header-looking lines at the start
            if not stripped or len(stripped) < 5:
                continue
            # Once we hit real content, stop header mode
            in_header = False

        # Remove [Illustration] and [Illustration: ...] markers
        if re.match(r'^\[Illustration', stripped):
            continue
        
        # Remove empty bracket lines or orphan closing brackets
        if stripped == ']' or stripped == ']]':
            continue
        
        # Remove lines that are just brackets with underscores (copyright markers)
        if re.match(r'^\[_', stripped):
            continue

        cleaned.append(line)
    
    # Remove Gutenberg footer block at the end
    result = '\n'.join(cleaned)
    footer_patterns = [
        r'\*\*\* END OF (?:THE |THIS )?PROJECT GUTENBERG',
        r'The Project Gutenberg eBook of',
        r'End of the Project Gutenberg',
        r'This eBook was converted',
    ]
    for pat in footer_patterns:
        idx = re.search(pat, result, re.IGNORECASE)
        if idx:
            result = result[:idx.start()]
    
    return result.strip()


def import_gutenberg(item: Dict, existing_hashes: Set[str], existing_ta: Set[Tuple[str, str]], dry_run: bool) -> Dict:
    """Import a single Gutenberg book. Returns result dict."""
    import lectura

    gid = item["gutenberg_id"]
    title = item["title"]
    author = item["author"]
    category = item.get("category", "General")
    cover_url = item.get("cover_url")
    t0 = time.time()

    result = {"title": title, "author": author, "source": "gutenberg", "gutenberg_id": gid}

    # 1. Check title+author duplicate
    ta_key = (title.lower().strip(), author.lower().strip())
    if ta_key in existing_ta:
        result["status"] = "duplicate"
        result["error"] = f"Ya existe '{title}' de '{author}'"
        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    # 2. Download text
    import urllib.request
    import urllib.error

    api_url = f"https://gutendex.com/books/{gid}"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "AeternumLibrary/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"API error: {e}"
        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    formats = data.get("formats", {})
    text_url = formats.get("text/plain; charset=utf-8") or formats.get("text/plain")
    if not text_url:
        text_url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"

    # Try to get cover from Gutenberg if not provided
    if not item.get("cover_url") and data.get("cover_image"):
        cover_url = data["cover_image"]

    try:
        req = urllib.request.Request(text_url, headers={"User-Agent": "AeternumLibrary/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError:
        alt_url = f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt"
        try:
            req = urllib.request.Request(alt_url, headers={"User-Agent": "AeternumLibrary/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"Download error: {e}"
            result["duration_seconds"] = round(time.time() - t0, 2)
            return result
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Download error: {e}"
        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    # Clean Gutenberg artifacts (headers, footers, [Illustration] markers)
    content = clean_gutenberg_text(content)

    # 3. Validate content
    validacion = lectura.validar_contenido_libro(content, None, fuente="gutenberg")
    if not validacion["valid"]:
        result["status"] = "rejected"
        result["error"] = "; ".join(validacion["errors"])
        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    # 4. Paginate
    paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(content)
    if not paginas:
        result["status"] = "rejected"
        result["error"] = "No se generaron páginas"
        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    result["page_count"] = len(paginas)

    # 5. Hash
    source_hash = calcular_hash_texto(content)
    result["source_hash"] = source_hash

    if source_hash in existing_hashes:
        result["status"] = "duplicate"
        result["error"] = f"Hash duplicado: {source_hash[:16]}..."
        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    if dry_run:
        result["status"] = "imported"
        result["book_id"] = -1
        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    # 6. Insert
    conn = get_db()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc).isoformat()
            cur.execute(
                """
                INSERT INTO books (title, author_name, content, category, price,
                    pdf_path, views, likes, average_rating, total_reviews,
                    published, created_at, source, source_url, source_id,
                    source_format, source_hash, cover_image_url)
                VALUES (%s, %s, %s, %s, 0, NULL, 0, 0, 0.0, 0, 1, %s,
                    'gutenberg', %s, %s, 'txt', %s, %s)
                RETURNING id
                """,
                (title, author, content, category, now,
                 f"https://www.gutenberg.org/ebooks/{gid}", str(gid),
                 source_hash, cover_url),
            )
            book_id = cur.fetchone()["id"]

            cap_ids = {}
            for cap in capitulos:
                cur.execute(
                    "INSERT INTO chapters (book_id, title, start_page) VALUES (%s, %s, %s) RETURNING id",
                    (book_id, cap["title"], cap["page"]),
                )
                cap_ids[cap["page"]] = cur.fetchone()["id"]

            if paginas:
                filas = [(book_id, i, texto, cap_ids.get(i)) for i, texto in enumerate(paginas, start=1)]
                cur.executemany(
                    "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s, %s, %s, %s)",
                    filas,
                )

            cur.execute("UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s", (len(paginas), now, book_id))

        conn.commit()
        result["status"] = "imported"
        result["book_id"] = book_id
        existing_hashes.add(source_hash)
        existing_ta.add(ta_key)
    except Exception as e:
        conn.rollback()
        result["status"] = "error"
        result["error"] = f"DB error: {e}"
    finally:
        conn.close()

    result["duration_seconds"] = round(time.time() - t0, 2)
    return result


# ---------------------------------------------------------------------------
# PDF import (reutiliza import_masiva.MassImporter)
# ---------------------------------------------------------------------------

def import_pdfs(source_dir: str, manifest: Manifest, existing_hashes: Set[str], dry_run: bool, batch_size: int, rate_limit: float) -> Dict[str, Any]:
    """Import PDFs from a directory using the existing MassImporter."""
    from import_masiva import MassImporter

    importer = MassImporter(
        manifest=manifest,
        batch_size=batch_size,
        rate_limit=rate_limit,
    )

    pdf_files = importer.scan_directory(source_dir)
    if not pdf_files:
        logger.warning("No se encontraron PDFs en: %s", source_dir)
        return {"total": 0, "imported": 0, "rejected": 0, "errors": 0, "skipped": 0}

    manifest.start(len(pdf_files))

    imported = 0
    rejected = 0
    errors = 0
    skipped = 0
    start_all = time.time()

    for i, pdf_info in enumerate(pdf_files, 1):
        fp = pdf_info["path"]
        key = manifest.key_for({"path": fp})

        if manifest.is_done(key, pdf_info["sha256"]):
            logger.info("[%d/%d] OMITIDO: %s", i, len(pdf_files), os.path.basename(fp))
            skipped += 1
            continue

        logger.info("[%d/%d] Procesando: %s (%.1f MB)", i, len(pdf_files), os.path.basename(fp), pdf_info["size"] / 1024 / 1024)

        result = importer._process_single(pdf_info, existing_hashes, dry_run)
        manifest.record(key, {
            "title": result.title,
            "author": result.author,
            "source": "pdf",
            "path": fp,
            "status": result.status,
            "book_id": result.book_id,
            "error": result.error,
            "page_count": result.page_count,
            "hash": result.sha256,
            "duration_seconds": result.duration_seconds,
        })

        if result.status == "imported":
            imported += 1
        elif result.status == "rejected":
            rejected += 1
        elif result.status == "error":
            errors += 1
        else:
            skipped += 1

        if i % batch_size == 0 and i < len(pdf_files):
            time.sleep(rate_limit)

    total_time = time.time() - start_all
    return {
        "total": len(pdf_files),
        "imported": imported,
        "rejected": rejected,
        "errors": errors,
        "skipped": skipped,
        "duration_seconds": round(total_time, 1),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Orquestador de importación masiva de libros")
    parser.add_argument("--source", required=True, choices=["gutenberg", "pdfs"], help="Fuente de libros")
    parser.add_argument("--catalog", help="Ruta al catálogo JSON (para Gutenberg)")
    parser.add_argument("--dir", help="Directorio con PDFs (para PDFs)")
    parser.add_argument("--output", default=None, help="Ruta del reporte JSON")
    parser.add_argument("--batch-size", type=int, default=5, help="Lotes entre pausas")
    parser.add_argument("--rate-limit", type=float, default=2.0, help="Segundos entre lotes")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Solo simular (default)")
    parser.add_argument("--execute", action="store_true", help="Ejecutar inserción real")
    args = parser.parse_args()

    dry_run = not args.execute

    if args.source == "gutenberg":
        if not args.catalog or not os.path.isfile(args.catalog):
            logger.error("Para Gutenberg, especifica --catalog con un JSON válido")
            sys.exit(1)
        with open(args.catalog, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        output_path = args.output or os.path.join(os.path.dirname(args.catalog), "import_report.json")
        manifest_path = os.path.join(os.path.dirname(args.catalog), "import_manifest.json")
    else:
        if not args.dir or not os.path.isdir(args.dir):
            logger.error("Para PDFs, especifica --dir con un directorio válido")
            sys.exit(1)
        output_path = args.output or os.path.join(args.dir, "import_report.json")
        manifest_path = os.path.join(args.dir, "import_manifest.json")
        catalog = None

    ensure_storage_directories()
    manifest = Manifest(manifest_path)
    existing_hashes = load_existing_hashes()
    existing_ta = load_existing_title_author()

    logger.info("=" * 60)
    logger.info("IMPORTACIÓN MASIVA DE LIBROS")
    logger.info("Fuente: %s", args.source.upper())
    logger.info("Modo: %s", "DRY-RUN" if dry_run else "EXECUTE")
    logger.info("Hashes existentes: %d | Títulos existentes: %d", len(existing_hashes), len(existing_ta))
    logger.info("=" * 60)

    start = time.time()

    if args.source == "gutenberg":
        manifest.start(len(catalog))
        imported = 0
        rejected = 0
        errors = 0
        duplicates = 0
        skipped = 0

        for i, item in enumerate(catalog, 1):
            key = manifest.key_for(item)
            if manifest.is_done(key):
                logger.info("[%d/%d] OMITIDO: %s", i, len(catalog), item.get("title", "?"))
                skipped += 1
                continue

            logger.info("[%d/%d] %s (Gutenberg #%d)", i, len(catalog), item.get("title", "?"), item.get("gutenberg_id", "?"))
            result = import_gutenberg(item, existing_hashes, existing_ta, dry_run)
            manifest.record(key, result)

            if result["status"] == "imported":
                imported += 1
                logger.info("  [OK] ID %s — %s", result.get("book_id"), item.get("title"))
            elif result["status"] == "duplicate":
                duplicates += 1
                logger.info("  [SKIP] Duplicado — %s", result.get("error", ""))
            elif result["status"] == "rejected":
                rejected += 1
                logger.info("  [REJECT] %s", result.get("error", ""))
            elif result["status"] == "error":
                errors += 1
                logger.info("  [ERROR] %s", result.get("error", ""))

            if i % args.batch_size == 0 and i < len(catalog):
                time.sleep(args.rate_limit)

        summary = {
            "total": len(catalog),
            "imported": imported,
            "duplicates": duplicates,
            "rejected": rejected,
            "errors": errors,
            "skipped": skipped,
        }
    else:
        summary = import_pdfs(args.dir, manifest, existing_hashes, dry_run, args.batch_size, args.rate_limit)

    elapsed = time.time() - start
    summary["duration_seconds"] = round(elapsed, 1)
    manifest.finish(summary)

    report = {
        "mode": "dry-run" if dry_run else "execute",
        "source": args.source,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESUMEN DE IMPORTACIÓN")
    logger.info("=" * 60)
    logger.info("TOTAL:     %d", summary.get("total", 0))
    logger.info("IMPORTADOS: %d", summary.get("imported", 0))
    if "duplicates" in summary:
        logger.info("DUPLICADOS: %d", summary.get("duplicates", 0))
    logger.info("RECHAZADOS: %d", summary.get("rejected", 0))
    logger.info("ERRORES:   %d", summary.get("errors", 0))
    logger.info("OMITIDOS:  %d", summary.get("skipped", 0))
    logger.info("TIEMPO:    %.1fs", elapsed)
    logger.info("=" * 60)
    logger.info("Reporte: %s", output_path)
    logger.info("Manifest: %s", manifest_path)

    return 0 if summary.get("errors", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
