#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_gutenberg_batch.py — Importador masivo de libros desde Project Gutenberg.

Descarga textos de dominio público, los valida, y los inserta en la BD
usando el mismo pipeline que import_masiva.py pero para contenido textual.

Uso:
  python import_gutenberg_batch.py --catalog catalog.json --execute
  python import_gutenberg_batch.py --catalog catalog.json --dry-run
  python import_gutenberg_batch.py --catalog catalog.json --execute --batch-size 3

El catálogo JSON lista los libros a importar con su metadata.
"""

import os
import sys
import json
import time
import uuid
import hashlib
import shutil
import logging
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Set, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
import psycopg2.extras
from storage_config import STORAGE_DIR, STORAGE_BOOKS, STORAGE_COVERS, STORAGE_TEMP
from hash_utils import calcular_hash_texto

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("import_gutenberg")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GUTENDEX_API = "https://gutendex.com/books"
REQUEST_TIMEOUT = 30


class ImportStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    IMPORTED = "imported"
    REJECTED = "rejected"
    ERROR = "error"
    SKIPPED = "skipped"
    DUPLICATE = "duplicate"


# ---------------------------------------------------------------------------
# CatalogEntry — un libro en el catálogo
# ---------------------------------------------------------------------------

@dataclass
class CatalogEntry:
    title: str
    author: str
    gutenberg_id: int
    category: str = "General"
    cover_url: Optional[str] = None
    language: str = "es"
    # Tracking fields
    status: str = ImportStatus.PENDING
    book_id: Optional[int] = None
    source_hash: Optional[str] = None
    page_count: Optional[int] = None
    error: Optional[str] = None
    processed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Manifest — JSON-based resume tracking
# ---------------------------------------------------------------------------

class Manifest:
    def __init__(self, manifest_path: str):
        self.path = manifest_path
        self.data: Dict[str, Any] = {
            "import_id": None,
            "started_at": None,
            "total_entries": 0,
            "status": "pending",
            "entries": {},
        }
        if os.path.exists(manifest_path):
            self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Manifest corrupto, creando nuevo: %s", e)
            self.data["entries"] = {}

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        shutil.move(tmp, self.path)

    def start(self, total: int):
        self.data["import_id"] = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        self.data["started_at"] = datetime.now(timezone.utc).isoformat()
        self.data["total_entries"] = total
        self.data["status"] = "in_progress"
        self.save()

    def is_processed(self, gutenberg_id: int) -> bool:
        key = str(gutenberg_id)
        entry = self.data["entries"].get(key)
        if not entry:
            return False
        return entry.get("status") in (ImportStatus.IMPORTED, ImportStatus.REJECTED, ImportStatus.DUPLICATE)

    def record(self, entry: CatalogEntry):
        key = str(entry.gutenberg_id)
        self.data["entries"][key] = entry.to_dict()
        self.save()

    def finish(self, summary: Dict[str, Any]):
        self.data["status"] = "completed"
        self.data["summary"] = summary
        self.save()


# ---------------------------------------------------------------------------
# DB helpers
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
        logger.warning("No se pudieron cargar hashes existentes: %s", e)
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
# Gutenberg downloader
# ---------------------------------------------------------------------------

def fetch_gutenberg_text(gutenberg_id: int) -> Optional[str]:
    """Download plain text from Gutenberg via gutendex API."""
    # First get metadata to find the text URL
    api_url = f"{GUTENDEX_API}/{gutenberg_id}"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "AeternumLibrary/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error("  API error para Gutenberg %d: %s", gutenberg_id, e)
        return None

    # Find text/plain URL
    formats = data.get("formats", {})
    text_url = formats.get("text/plain; charset=utf-8") or formats.get("text/plain")
    if not text_url:
        # Fallback: try common Gutenberg URL pattern
        text_url = f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"

    # Download text
    try:
        req = urllib.request.Request(text_url, headers={"User-Agent": "AeternumLibrary/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Try with different URL pattern
            alt_url = f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt"
            try:
                req = urllib.request.Request(alt_url, headers={"User-Agent": "AeternumLibrary/1.0"})
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                    content = resp.read().decode("utf-8", errors="replace")
            except Exception as e2:
                logger.error("  Download error (alt) para Gutenberg %d: %s", gutenberg_id, e2)
                return None
        else:
            logger.error("  Download error para Gutenberg %d: %s", gutenberg_id, e)
            return None
    except Exception as e:
        logger.error("  Download error para Gutenberg %d: %s", gutenberg_id, e)
        return None

    return content


def clean_gutenberg_text(text: str) -> str:
    """Remove common Gutenberg headers, footers and illustration markers."""
    import re
    lines = text.split('\n')
    cleaned = []
    in_header = True
    for line in lines:
        stripped = line.strip()
        if in_header:
            if stripped.startswith('*** START OF') or stripped.startswith('*** START THE'):
                in_header = False
                continue
            if stripped.startswith('*** END OF') or stripped.startswith('*** END THE'):
                break
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
            ]):
                continue
            if not stripped or len(stripped) < 5:
                continue
            in_header = False
        if re.match(r'^\[Illustration', stripped):
            continue
        if stripped == ']' or stripped == ']]':
            continue
        if re.match(r'^\[_', stripped):
            continue
        cleaned.append(line)
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


def fetch_gutenberg_metadata(gutenberg_id: int) -> Dict[str, Any]:
    """Fetch metadata from gutendex API."""
    api_url = f"{GUTENDEX_API}/{gutenberg_id}"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "AeternumLibrary/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------

class GutenbergImporter:
    def __init__(
        self,
        manifest: Manifest,
        batch_size: int = 5,
        rate_limit: float = 2.0,
    ):
        self.manifest = manifest
        self.batch_size = batch_size
        self.rate_limit = rate_limit

    def run(self, catalog: List[Dict], dry_run: bool = True) -> Dict[str, Any]:
        self.manifest.start(len(catalog))
        existing_hashes = load_existing_hashes()
        existing_ta = load_existing_title_author()
        logger.info("Hashes existentes en BD: %d", len(existing_hashes))
        logger.info("Pares título+autor existentes: %d", len(existing_ta))

        imported = 0
        rejected = 0
        errors = 0
        duplicates = 0
        skipped = 0
        start_all = time.time()

        for i, item in enumerate(catalog, 1):
            entry = CatalogEntry(
                title=item["title"],
                author=item["author"],
                gutenberg_id=item["gutenberg_id"],
                category=item.get("category", "General"),
                cover_url=item.get("cover_url"),
                language=item.get("language", "es"),
            )

            # Skip if already processed
            if self.manifest.is_processed(entry.gutenberg_id):
                logger.info("[%d/%d] OMITIDO (ya procesado): %s", i, len(catalog), entry.title)
                skipped += 1
                continue

            logger.info("[%d/%d] Procesando: %s (Gutenberg #%d)", i, len(catalog), entry.title, entry.gutenberg_id)

            result = self._process_single(entry, existing_hashes, existing_ta, dry_run)
            self.manifest.record(result)

            if result.status == ImportStatus.IMPORTED:
                imported += 1
            elif result.status == ImportStatus.DUPLICATE:
                duplicates += 1
            elif result.status == ImportStatus.REJECTED:
                rejected += 1
            elif result.status == ImportStatus.ERROR:
                errors += 1
            else:
                skipped += 1

            # Batch pause
            if i % self.batch_size == 0 and i < len(catalog):
                logger.info("Pausa entre lotes (%.1fs)...", self.rate_limit)
                time.sleep(self.rate_limit)

        total_time = time.time() - start_all
        summary = {
            "total": len(catalog),
            "imported": imported,
            "duplicates": duplicates,
            "rejected": rejected,
            "errors": errors,
            "skipped": skipped,
            "duration_seconds": round(total_time, 1),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.manifest.finish(summary)
        return summary

    def _process_single(
        self,
        entry: CatalogEntry,
        existing_hashes: Set[str],
        existing_ta: Set[Tuple[str, str]],
        dry_run: bool,
    ) -> CatalogEntry:
        t0 = time.time()

        try:
            # 1. Check title+author duplicate
            ta_key = (entry.title.lower().strip(), entry.author.lower().strip())
            if ta_key in existing_ta:
                entry.status = ImportStatus.DUPLICATE
                entry.error = f"Duplicado: ya existe '{entry.title}' de '{entry.author}'"
                entry.processed_at = datetime.now(timezone.utc).isoformat()
                entry.duration_seconds = round(time.time() - t0, 2)
                return entry

            # 2. Download text from Gutenberg
            entry.status = ImportStatus.DOWNLOADING
            content = fetch_gutenberg_text(entry.gutenberg_id)
            if not content:
                entry.status = ImportStatus.ERROR
                entry.error = "No se pudo descargar el texto desde Gutenberg"
                entry.processed_at = datetime.now(timezone.utc).isoformat()
                entry.duration_seconds = round(time.time() - t0, 2)
                return entry

            # Clean Gutenberg artifacts
            content = clean_gutenberg_text(content)

            # 3. Validate content using lectura pipeline
            import lectura
            validacion = lectura.validar_contenido_libro(content, None, fuente="gutenberg")
            if not validacion["valid"]:
                entry.status = ImportStatus.REJECTED
                entry.error = "; ".join(validacion["errors"])
                entry.processed_at = datetime.now(timezone.utc).isoformat()
                entry.duration_seconds = round(time.time() - t0, 2)
                return entry

            # 4. Paginate content
            paginas, capitulos = lectura.paginar_desde_contenido_con_capitulos(content)
            if not paginas:
                entry.status = ImportStatus.REJECTED
                entry.error = "No se generaron páginas a partir del contenido"
                entry.processed_at = datetime.now(timezone.utc).isoformat()
                entry.duration_seconds = round(time.time() - t0, 2)
                return entry

            entry.page_count = len(paginas)

            # 5. Compute hash of text content
            source_hash = calcular_hash_texto(content)
            entry.source_hash = source_hash

            # 6. Check hash duplicate
            if source_hash in existing_hashes:
                entry.status = ImportStatus.DUPLICATE
                entry.error = f"Duplicado por hash: {source_hash[:16]}..."
                entry.processed_at = datetime.now(timezone.utc).isoformat()
                entry.duration_seconds = round(time.time() - t0, 2)
                return entry

            if dry_run:
                entry.status = ImportStatus.IMPORTED
                entry.book_id = -1
                entry.processed_at = datetime.now(timezone.utc).isoformat()
                entry.duration_seconds = round(time.time() - t0, 2)
                return entry

            # 7. Insert into database
            book_id = self._insert_book(entry, content, paginas, capitulos, source_hash)
            entry.book_id = book_id
            entry.status = ImportStatus.IMPORTED
            entry.processed_at = datetime.now(timezone.utc).isoformat()
            existing_hashes.add(source_hash)
            existing_ta.add(ta_key)
            logger.info("  -> Libro insertado con ID %d: %s", book_id, entry.title)

        except Exception as e:
            entry.status = ImportStatus.ERROR
            entry.error = f"{type(e).__name__}: {e}"
            logger.error("  -> Error: %s", entry.error)

        finally:
            entry.duration_seconds = round(time.time() - t0, 2)

        return entry

    def _insert_book(
        self,
        entry: CatalogEntry,
        content: str,
        paginas: List[str],
        capitulos: List[Dict],
        source_hash: str,
    ) -> int:
        conn = get_db()
        try:
            conn.autocommit = False
            with conn.cursor() as cur:
                now = datetime.now(timezone.utc).isoformat()

                cover_url = entry.cover_url

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
                    (
                        entry.title, entry.author, content, entry.category, now,
                        f"https://www.gutenberg.org/ebooks/{entry.gutenberg_id}",
                        str(entry.gutenberg_id),
                        source_hash,
                        cover_url,
                    ),
                )
                book_id = cur.fetchone()["id"]

                # Insert chapters
                cap_ids = {}
                for cap in capitulos:
                    cur.execute(
                        "INSERT INTO chapters (book_id, title, start_page) VALUES (%s, %s, %s) RETURNING id",
                        (book_id, cap["title"], cap["page"]),
                    )
                    cap_ids[cap["page"]] = cur.fetchone()["id"]

                # Insert pages
                if paginas:
                    filas = [
                        (book_id, i, texto, cap_ids.get(i))
                        for i, texto in enumerate(paginas, start=1)
                    ]
                    cur.executemany(
                        "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s, %s, %s, %s)",
                        filas,
                    )

                # Update page count
                cur.execute(
                    "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
                    (len(paginas), now, book_id),
                )

            conn.commit()
            return book_id

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Importador masivo de libros desde Project Gutenberg",
    )
    parser.add_argument("--catalog", required=True, help="Ruta al archivo JSON del catálogo")
    parser.add_argument("--output", default=None, help="Ruta del reporte JSON de salida")
    parser.add_argument("--batch-size", type=int, default=5, help="Lotes entre pausas")
    parser.add_argument("--rate-limit", type=float, default=2.0, help="Segundos entre lotes")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Solo simular (default)")
    parser.add_argument("--execute", action="store_true", help="Ejecutar inserción real")
    args = parser.parse_args()

    if not os.path.isfile(args.catalog):
        logger.error("Catálogo no encontrado: %s", args.catalog)
        sys.exit(1)

    with open(args.catalog, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    if not isinstance(catalog, list) or not catalog:
        logger.error("El catálogo debe ser un JSON array no vacío")
        sys.exit(1)

    dry_run = not args.execute
    output_path = args.output or os.path.join(os.path.dirname(args.catalog), "gutenberg_import_report.json")
    manifest_path = os.path.join(os.path.dirname(args.catalog), "gutenberg_manifest.json")

    manifest = Manifest(manifest_path)
    importer = GutenbergImporter(
        manifest=manifest,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
    )

    logger.info("=" * 60)
    logger.info("IMPORTADOR MASIVO GUTENBERG")
    logger.info("Modo: %s", "DRY-RUN (sin inserción)" if dry_run else "EXECUTE (inserción real)")
    logger.info("Catálogo: %d libros", len(catalog))
    logger.info("Lote: %d | Pausa: %.1fs", args.batch_size, args.rate_limit)
    logger.info("=" * 60)

    start = time.time()
    summary = importer.run(catalog, dry_run=dry_run)
    elapsed = time.time() - start

    report = {
        "mode": "dry-run" if dry_run else "execute",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_time_seconds": round(elapsed, 1),
        "summary": summary,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("=" * 60)
    logger.info("REPORTE: %s", output_path)
    logger.info("Total: %d | Importados: %d | Duplicados: %d | Rechazados: %d | Errores: %d",
                summary["total"], summary["imported"], summary["duplicates"],
                summary["rejected"], summary["errors"])
    logger.info("Tiempo total: %.1fs", elapsed)
    logger.info("=" * 60)

    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
