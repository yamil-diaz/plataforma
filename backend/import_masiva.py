#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_masiva.py — Importador masivo de libros PDF.

Modo seguro, transaccional, reanudable y verificable.

Uso:
  python import_masiva.py --source-dir ./mis_pdfs --dry-run
  python import_masiva.py --source-dir ./mis_pdfs --execute
  python import_masiva.py --source-dir ./mis_pdfs --execute --batch-size 3 --rate-limit 3

El manifest JSON se guarda al lado del source-dir para reanudación.
"""

import os
import sys
import json
import hashlib
import shutil
import time
import uuid
import logging
import argparse
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Set, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
import psycopg2.extras
from storage_config import STORAGE_BOOKS, STORAGE_DIR
from hash_utils import calcular_hash_archivo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("import_masiva")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class ImportStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTED = "imported"
    REJECTED = "rejected"
    ERROR = "error"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# ImportedFile — per-file tracking record
# ---------------------------------------------------------------------------

@dataclass
class ImportedFile:
    path: str
    sha256: str
    status: str = ImportStatus.PENDING
    book_id: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
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
    def __init__(self, manifest_path: str, source_dir: str):
        self.path = manifest_path
        self.data: Dict[str, Any] = {
            "import_id": None,
            "source_dir": source_dir,
            "started_at": None,
            "total_files": 0,
            "status": "pending",
            "files": {},
        }
        if os.path.exists(manifest_path):
            self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Manifest corrupto, creando nuevo: %s", e)
            self.data["files"] = {}

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        shutil.move(tmp, self.path)

    def start(self, total_files: int):
        self.data["import_id"] = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        self.data["started_at"] = datetime.now(timezone.utc).isoformat()
        self.data["total_files"] = total_files
        self.data["status"] = "in_progress"
        self.save()

    def is_processed(self, filepath: str, sha256: str) -> bool:
        entry = self.data["files"].get(filepath)
        if not entry:
            return False
        if entry.get("sha256") != sha256:
            logger.info("Archivo reemplazado (hash cambió): %s", os.path.basename(filepath))
            return False
        return entry.get("status") in (ImportStatus.IMPORTED, ImportStatus.REJECTED)

    def record(self, result: ImportedFile):
        self.data["files"][result.path] = result.to_dict()
        self.save()

    def finish(self, summary: Dict[str, Any]):
        self.data["status"] = "completed"
        self.data["summary"] = summary
        self.save()

    @property
    def pending_files(self) -> List[str]:
        return [
            fp for fp, entry in self.data["files"].items()
            if entry.get("status") in (ImportStatus.PENDING, ImportStatus.ERROR)
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# calcular_hash se mantiene como alias para compatibilidad con tests existentes.
# La implementación real delega a hash_utils.calcular_hash_archivo.
calcular_hash = calcular_hash_archivo


def get_db():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL", ""),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# ---------------------------------------------------------------------------
# MassImporter
# ---------------------------------------------------------------------------

class MassImporter:
    def __init__(
        self,
        manifest: Manifest,
        category: str = "General",
        price: float = 0.0,
        batch_size: int = 5,
        rate_limit: float = 2.0,
    ):
        self.manifest = manifest
        self.category = category
        self.price = price
        self.batch_size = batch_size
        self.rate_limit = rate_limit

    def scan_directory(self, source_dir: str) -> List[Dict[str, Any]]:
        pdf_files = []
        for root, _, files in os.walk(source_dir):
            for fname in sorted(files):
                if fname.lower().endswith(".pdf"):
                    full = os.path.join(root, fname)
                    pdf_files.append({
                        "path": full,
                        "filename": fname,
                        "size": os.path.getsize(full),
                        "sha256": calcular_hash(full),
                    })
        return pdf_files

    def run(self, source_dir: str, dry_run: bool = True) -> Dict[str, Any]:
        pdf_files = self.scan_directory(source_dir)

        if not pdf_files:
            logger.warning("No se encontraron archivos PDF en: %s", source_dir)
            return {"total": 0, "imported": 0, "rejected": 0, "errors": 0, "skipped": 0}

        self.manifest.start(len(pdf_files))

        existing_hashes = self._load_existing_hashes()
        logger.info("Hashes existentes en BD: %d", len(existing_hashes))

        results: List[ImportedFile] = []
        imported = 0
        rejected = 0
        errors = 0
        skipped = 0
        start_all = time.time()

        for i, pdf_info in enumerate(pdf_files, 1):
            fp = pdf_info["path"]

            if self.manifest.is_processed(fp, pdf_info["sha256"]):
                logger.info("[%d/%d] OMITIDO (ya procesado): %s", i, len(pdf_files), pdf_info["filename"])
                entry = self.manifest.data["files"].get(fp)
                if entry and entry.get("status") == ImportStatus.IMPORTED:
                    imported += 1
                else:
                    skipped += 1
                continue

            logger.info("[%d/%d] Procesando: %s (%.1f MB)", i, len(pdf_files), pdf_info["filename"], pdf_info["size"] / 1024 / 1024)

            file_result = self._process_single(pdf_info, existing_hashes, dry_run)
            results.append(file_result)
            self.manifest.record(file_result)

            if file_result.status == ImportStatus.IMPORTED:
                imported += 1
            elif file_result.status == ImportStatus.REJECTED:
                rejected += 1
            elif file_result.status == ImportStatus.ERROR:
                errors += 1
            else:
                skipped += 1

            if i % self.batch_size == 0 and i < len(pdf_files):
                logger.info("Pausa entre lotes (%.1fs)...", self.rate_limit)
                time.sleep(self.rate_limit)

        total_time = time.time() - start_all
        summary = {
            "total": len(pdf_files),
            "imported": imported,
            "rejected": rejected,
            "errors": errors,
            "skipped": skipped,
            "duration_seconds": round(total_time, 1),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.manifest.finish(summary)
        return summary

    def _load_existing_hashes(self) -> Set[str]:
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

    def _process_single(self, pdf_info: Dict, existing_hashes: Set[str], dry_run: bool) -> ImportedFile:
        fp = pdf_info["path"]
        result = ImportedFile(path=fp, sha256=pdf_info["sha256"])
        t0 = time.time()

        try:
            # 1. Validate PDF file (magic bytes + size + pypdf open + pages > 0)
            ok, err = self._validate_pdf_file(pdf_info)
            if not ok:
                result.status = ImportStatus.REJECTED
                result.error = err
                return result

            # 2. Full content pipeline (extracción + validación central)
            import lectura
            procesado = lectura.procesar_contenido_para_publicacion(pdf_path=fp, fuente="pdf")
            validacion = procesado["validacion"]
            if not validacion["valid"]:
                result.status = ImportStatus.REJECTED
                result.error = "; ".join(validacion["errors"])
                return result

            content = procesado["content"]
            paginas = procesado["paginas"]
            capitulos = procesado["capitulos"]
            result.page_count = len(paginas)

            # 3. Doble verificación: detectar_contenido_patologico explícito
            #    (defensa en profundidad además de la validación interna del pipeline)
            diagnostico = lectura.detectar_contenido_patologico(content, paginas)
            if diagnostico["pathological"]:
                result.status = ImportStatus.REJECTED
                result.error = f"Contenido patológico: {diagnostico['reason']}"
                return result

            # 4. Extraer metadatos del PDF
            result.title, result.author = self._extract_metadata(fp, pdf_info["filename"])

            # 5. Verificar page_count: páginas extraídas == pypdf page count
            from pypdf import PdfReader
            reader = PdfReader(fp)
            real_page_count = len(reader.pages)
            if real_page_count != len(paginas):
                result.status = ImportStatus.REJECTED
                result.error = (
                    f"Inconsistencia de páginas: pypdf reporta {real_page_count}, "
                    f"la extracción generó {len(paginas)}"
                )
                return result

            # 6. Verificar que hay contenido real en al menos una página
            if not any(len(p.strip()) >= 50 for p in paginas):
                result.status = ImportStatus.REJECTED
                result.error = "Ninguna página tiene contenido apreciable (>= 50 chars)"
                return result

            # 7. Dedup check by source_hash contra BD
            if pdf_info["sha256"] in existing_hashes:
                result.status = ImportStatus.REJECTED
                result.error = f"Duplicado: ya existe un libro con hash {pdf_info['sha256'][:16]}..."
                return result

            if dry_run:
                result.status = ImportStatus.IMPORTED
                result.book_id = -1
                result.processed_at = datetime.now(timezone.utc).isoformat()
                return result

            # 8. Real import (transacción por libro, rollback si falla)
            book_id = self._insert_book(
                result.title, result.author, content, pdf_info,
                paginas, capitulos, pdf_info["sha256"],
            )
            result.book_id = book_id
            result.status = ImportStatus.IMPORTED
            result.processed_at = datetime.now(timezone.utc).isoformat()
            existing_hashes.add(pdf_info["sha256"])
            logger.info("  -> Libro insertado con ID %d: %s", book_id, result.title)

        except Exception as e:
            result.status = ImportStatus.ERROR
            result.error = f"{type(e).__name__}: {e}"
            logger.error("  -> Error: %s", result.error)

        finally:
            result.duration_seconds = round(time.time() - t0, 2)

        return result

    def _validate_pdf_file(self, pdf_info: Dict) -> Tuple[bool, str]:
        fp = pdf_info["path"]

        if not os.path.isfile(fp):
            return False, "Archivo no encontrado"

        if pdf_info["size"] > MAX_FILE_SIZE_BYTES:
            return False, f"Archivo excede {MAX_FILE_SIZE_MB}MB ({pdf_info['size']} bytes)"

        with open(fp, "rb") as f:
            header = f.read(1024)
        if b"%PDF" not in header:
            return False, "No es un PDF válido (sin magic bytes %PDF)"

        try:
            from pypdf import PdfReader
            reader = PdfReader(fp)
            if len(reader.pages) == 0:
                return False, "PDF sin páginas"
        except Exception as e:
            return False, f"PDF corrupto: no se puede abrir con pypdf ({e})"

        return True, ""

    def _extract_metadata(self, pdf_path: str, filename: str) -> Tuple[str, str]:
        title = None
        author = None
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            meta = reader.metadata
            if meta:
                title = getattr(meta, "title", None) or (meta.get("/Title") if hasattr(meta, "get") else None)
                author = getattr(meta, "author", None) or (meta.get("/Author") if hasattr(meta, "get") else None)
        except Exception:
            pass

        title = (title or "").strip()
        author = (author or "").strip()
        if not title:
            title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        if not author:
            author = "Autor Desconocido"
        return title, author

    def _insert_book(
        self,
        title: str,
        author: str,
        content: str,
        pdf_info: Dict,
        paginas: List[str],
        capitulos: List[Dict],
        source_hash: str,
    ) -> int:
        fp = pdf_info["path"]

        # Copiar PDF a STORAGE_BOOKS con nombre UUID único
        unique_name = f"{uuid.uuid4()}_{pdf_info['filename']}"
        final_path = os.path.join(STORAGE_BOOKS, unique_name)
        shutil.copy2(fp, final_path)

        # Verificar que el archivo se copió correctamente
        if not os.path.isfile(final_path):
            raise RuntimeError(f"Fallo al copiar PDF a {final_path}")

        # Verificar que el hash del archivo copiado coincide con el original
        hash_copiado = calcular_hash_archivo(final_path)
        if hash_copiado != source_hash:
            os.remove(final_path)
            raise RuntimeError(
                f"Hash mismatch tras copia: original={source_hash[:16]}... "
                f"copiado={hash_copiado[:16]}..."
            )

        conn = get_db()
        try:
            conn.autocommit = False
            with conn.cursor() as cur:
                now = datetime.now(timezone.utc).isoformat()

                cur.execute(
                    """
                    INSERT INTO books (title, author_name, content, category, price,
                        pdf_path, views, likes, average_rating, total_reviews,
                        published, created_at, source, source_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0.0, 0, 1, %s, 'import', %s)
                    RETURNING id
                    """,
                    (title, author, content, self.category, self.price,
                     final_path, now, source_hash),
                )
                book_id = cur.fetchone()["id"]

                if capitulos:
                    cap_ids = {}
                    for cap in capitulos:
                        cur.execute(
                            "INSERT INTO chapters (book_id, title, start_page) VALUES (%s, %s, %s) RETURNING id",
                            (book_id, cap["title"], cap["page"]),
                        )
                        cap_ids[cap["page"]] = cur.fetchone()["id"]
                else:
                    cap_ids = {}

                if paginas:
                    filas = [
                        (book_id, i, texto, cap_ids.get(i))
                        for i, texto in enumerate(paginas, start=1)
                    ]
                    cur.executemany(
                        "INSERT INTO book_pages (book_id, page_number, content, chapter_id) VALUES (%s, %s, %s, %s)",
                        filas,
                    )

                cur.execute(
                    "UPDATE books SET page_count = %s, paginated_at = %s WHERE id = %s",
                    (len(paginas), now, book_id),
                )

            conn.commit()
            return book_id

        except Exception:
            conn.rollback()
            if os.path.isfile(final_path):
                try:
                    os.remove(final_path)
                except OSError:
                    pass
            raise
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    results: List[ImportedFile],
    summary: Dict[str, Any],
    total_time: float,
    dry_run: bool,
) -> Dict[str, Any]:
    report = {
        "mode": "dry-run" if dry_run else "execute",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_time_seconds": round(total_time, 1),
        "summary": summary,
        "files": [],
    }
    for r in results:
        report["files"].append({
            "file": os.path.basename(r.path),
            "sha256": r.sha256,
            "title": r.title,
            "author": r.author,
            "page_count": r.page_count,
            "status": r.status,
            "book_id": r.book_id,
            "error": r.error,
            "duration_seconds": r.duration_seconds,
        })
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Importador masivo seguro de libros PDF",
    )
    parser.add_argument("--source-dir", required=True, help="Directorio con PDFs")
    parser.add_argument("--output", default=None, help="Ruta del reporte JSON")
    parser.add_argument("--category", default="General", help="Categoría por defecto")
    parser.add_argument("--price", type=float, default=0.0, help="Precio por defecto")
    parser.add_argument("--batch-size", type=int, default=5, help="Lotes entre pausas")
    parser.add_argument("--rate-limit", type=float, default=2.0, help="Segundos entre lotes")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Solo simular (default)")
    parser.add_argument("--execute", action="store_true", help="Ejecutar inserción real")
    args = parser.parse_args()

    if not os.path.isdir(args.source_dir):
        logger.error("Directorio no encontrado: %s", args.source_dir)
        sys.exit(1)

    dry_run = not args.execute

    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(args.source_dir, "import_report.json")

    manifest_path = os.path.join(args.source_dir, "import_manifest.json")
    manifest = Manifest(manifest_path, args.source_dir)

    importer = MassImporter(
        manifest=manifest,
        category=args.category,
        price=args.price,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
    )

    logger.info("=" * 60)
    logger.info("IMPORTADOR MASIVO DE LIBROS")
    logger.info("Modo: %s", "DRY-RUN (sin inserción)" if dry_run else "EXECUTE (inserción real)")
    logger.info("Fuente: %s", args.source_dir)
    logger.info("Lote: %d | Pausa: %.1fs", args.batch_size, args.rate_limit)
    logger.info("=" * 60)

    start = time.time()
    summary = importer.run(args.source_dir, dry_run=dry_run)
    elapsed = time.time() - start

    report = generate_report(
        results=[
            ImportedFile(**entry)
            for entry in manifest.data["files"].values()
        ],
        summary=summary,
        total_time=elapsed,
        dry_run=dry_run,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("=" * 60)
    logger.info("REPORTE: %s", output_path)
    logger.info("Total: %d | Importados: %d | Rechazados: %d | Errores: %d | Omitidos: %d",
                summary["total"], summary["imported"], summary["rejected"],
                summary["errors"], summary["skipped"])
    logger.info("Tiempo total: %.1fs", elapsed)
    logger.info("=" * 60)

    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
