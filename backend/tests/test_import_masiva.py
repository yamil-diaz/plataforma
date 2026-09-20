#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests unitarios para import_masiva.py."""

import os
import sys
import json
import tempfile
import shutil
import hashlib
import time
from unittest.mock import patch, MagicMock

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from import_masiva import (
    Manifest,
    ImportedFile,
    ImportStatus,
    MassImporter,
    calcular_hash,
    generate_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def manifest_path(tmp_dir):
    return os.path.join(tmp_dir, "import_manifest.json")


@pytest.fixture
def sample_pdf(tmp_dir):
    """Create a minimal valid PDF file for testing."""
    pdf_path = os.path.join(tmp_dir, "test_book.pdf")
    # Minimal valid PDF with %PDF header and one page
    content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    with open(pdf_path, "wb") as f:
        f.write(content)
    return pdf_path


@pytest.fixture
def non_pdf_file(tmp_dir):
    p = os.path.join(tmp_dir, "not_a_pdf.txt")
    with open(p, "w") as f:
        f.write("This is not a PDF")
    return p


@pytest.fixture
def corrupt_pdf(tmp_dir):
    p = os.path.join(tmp_dir, "corrupt.pdf")
    with open(p, "wb") as f:
        f.write(b"%PDF-1.4\nthis is not valid pdf content at all")
    return p


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------

class TestManifest:
    def test_create_new_manifest(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        assert m.data["files"] == {}
        assert m.data["status"] == "pending"

    def test_start_manifest(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(10)
        assert m.data["total_files"] == 10
        assert m.data["status"] == "in_progress"
        assert m.data["import_id"] is not None
        assert os.path.exists(manifest_path)

    def test_save_and_load_manifest(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(5)
        m.record(ImportedFile(path="test.pdf", sha256="abc123", status=ImportStatus.IMPORTED, book_id=42))
        m.save()

        m2 = Manifest(manifest_path, tmp_dir)
        assert m2.data["total_files"] == 5
        assert m2.data["files"]["test.pdf"]["sha256"] == "abc123"
        assert m2.data["files"]["test.pdf"]["status"] == "imported"

    def test_is_processed_new_file(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        assert m.is_processed("new.pdf", "hash1") is False

    def test_is_processed_already_imported(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        m.record(ImportedFile(path="test.pdf", sha256="abc", status=ImportStatus.IMPORTED))
        assert m.is_processed("test.pdf", "abc") is True

    def test_is_processed_already_rejected(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        m.record(ImportedFile(path="test.pdf", sha256="abc", status=ImportStatus.REJECTED, error="bad"))
        assert m.is_processed("test.pdf", "abc") is True

    def test_is_processed_hash_changed(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        m.record(ImportedFile(path="test.pdf", sha256="old_hash", status=ImportStatus.IMPORTED))
        assert m.is_processed("test.pdf", "new_hash") is False

    def test_is_processed_error_status_not_skipped(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        m.record(ImportedFile(path="test.pdf", sha256="abc", status=ImportStatus.ERROR))
        assert m.is_processed("test.pdf", "abc") is False

    def test_finish_manifest(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        m.finish({"imported": 1, "rejected": 0})
        assert m.data["status"] == "completed"
        assert m.data["summary"]["imported"] == 1

    def test_pending_files(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(3)
        m.record(ImportedFile(path="a.pdf", sha256="h1", status=ImportStatus.IMPORTED))
        m.record(ImportedFile(path="b.pdf", sha256="h2", status=ImportStatus.ERROR))
        m.record(ImportedFile(path="c.pdf", sha256="h3", status=ImportStatus.PENDING))
        assert sorted(m.pending_files) == ["b.pdf", "c.pdf"]

    def test_corrupt_manifest_creates_new(self, manifest_path, tmp_dir):
        with open(manifest_path, "w") as f:
            f.write("{invalid json!!!")
        m = Manifest(manifest_path, tmp_dir)
        assert m.data["files"] == {}


# ---------------------------------------------------------------------------
# ImportedFile tests
# ---------------------------------------------------------------------------

class TestImportedFile:
    def test_to_dict_minimal(self):
        f = ImportedFile(path="test.pdf", sha256="abc")
        d = f.to_dict()
        assert d["path"] == "test.pdf"
        assert d["sha256"] == "abc"
        assert "book_id" not in d  # None fields excluded

    def test_to_dict_full(self):
        f = ImportedFile(
            path="test.pdf", sha256="abc",
            status=ImportStatus.IMPORTED, book_id=42,
            title="Test", author="Author", page_count=10,
        )
        d = f.to_dict()
        assert d["book_id"] == 42
        assert d["title"] == "Test"
        assert d["page_count"] == 10


# ---------------------------------------------------------------------------
# Hash tests
# ---------------------------------------------------------------------------

class TestHash:
    def test_hash_consistency(self, sample_pdf):
        h1 = calcular_hash(sample_pdf)
        h2 = calcular_hash(sample_pdf)
        assert h1 == h2

    def test_hash_different_files(self, sample_pdf, non_pdf_file):
        h1 = calcular_hash(sample_pdf)
        h2 = calcular_hash(non_pdf_file)
        assert h1 != h2

    def test_hash_format(self, sample_pdf):
        h = calcular_hash(sample_pdf)
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# PDF validation tests (via MassImporter._validate_pdf_file)
# ---------------------------------------------------------------------------

class TestPdfValidation:
    def test_nonexistent_file(self):
        result, err = MassImporter.__new__(MassImporter)._validate_pdf_file({
            "path": "/nonexistent/file.pdf", "size": 100, "sha256": "x",
        })
        assert result is False
        assert "no encontrado" in err

    def test_not_pdf_magic_bytes(self, non_pdf_file):
        size = os.path.getsize(non_pdf_file)
        result, err = MassImporter.__new__(MassImporter)._validate_pdf_file({
            "path": non_pdf_file, "size": size, "sha256": "x",
        })
        assert result is False
        assert "magic bytes" in err

    def test_oversized_file(self, sample_pdf):
        size = 60 * 1024 * 1024  # 60MB
        result, err = MassImporter.__new__(MassImporter)._validate_pdf_file({
            "path": sample_pdf, "size": size, "sha256": "x",
        })
        assert result is False
        assert "50MB" in err

    def test_corrupt_pdf(self, corrupt_pdf):
        size = os.path.getsize(corrupt_pdf)
        result, err = MassImporter.__new__(MassImporter)._validate_pdf_file({
            "path": corrupt_pdf, "size": size, "sha256": "x",
        })
        # Either fails validation or pypdf can't parse it
        # The exact behavior depends on pypdf version
        assert result is False or "corrupto" in err.lower() or "error" in err.lower()


# ---------------------------------------------------------------------------
# Metadata extraction tests
# ---------------------------------------------------------------------------

class TestMetadataExtraction:
    def test_fallback_to_filename(self, sample_pdf):
        importer = MassImporter.__new__(MassImporter)
        title, author = importer._extract_metadata(sample_pdf, "mi_libro_prueba.pdf")
        assert title == "Mi Libro Prueba"
        assert author == "Autor Desconocido"


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------

class TestReport:
    def test_report_structure(self):
        results = [
            ImportedFile(
                path="a.pdf", sha256="h1",
                status=ImportStatus.IMPORTED, book_id=1,
                title="Book A", author="Auth A", page_count=10,
                duration_seconds=1.5,
            ),
            ImportedFile(
                path="b.pdf", sha256="h2",
                status=ImportStatus.REJECTED, error="Invalid PDF",
                duration_seconds=0.3,
            ),
        ]
        summary = {"total": 2, "imported": 1, "rejected": 1, "errors": 0, "skipped": 0}
        report = generate_report(results, summary, total_time=2.0, dry_run=False)

        assert report["mode"] == "execute"
        assert report["summary"]["imported"] == 1
        assert len(report["files"]) == 2
        assert report["files"][0]["status"] == "imported"
        assert report["files"][0]["book_id"] == 1
        assert report["files"][1]["status"] == "rejected"
        assert report["files"][1]["error"] == "Invalid PDF"

    def test_report_dry_run_mode(self):
        report = generate_report([], {"total": 0, "imported": 0, "rejected": 0, "errors": 0, "skipped": 0}, 0.0, True)
        assert report["mode"] == "dry-run"


# ---------------------------------------------------------------------------
# Scan directory tests
# ---------------------------------------------------------------------------

class TestScanDirectory:
    def test_finds_pdfs(self, tmp_dir, sample_pdf):
        # Create a non-PDF file too
        txt = os.path.join(tmp_dir, "readme.txt")
        with open(txt, "w") as f:
            f.write("not a pdf")

        importer = MassImporter.__new__(MassImporter)
        files = importer.scan_directory(tmp_dir)
        assert len(files) == 1
        assert files[0]["filename"] == "test_book.pdf"
        assert files[0]["size"] > 0
        assert len(files[0]["sha256"]) == 64

    def test_empty_directory(self, tmp_dir):
        importer = MassImporter.__new__(MassImporter)
        files = importer.scan_directory(tmp_dir)
        assert len(files) == 0

    def test_nested_directories(self, tmp_dir, sample_pdf):
        subdir = os.path.join(tmp_dir, "subdir")
        os.makedirs(subdir)
        nested_pdf = os.path.join(subdir, "nested.pdf")
        shutil.copy2(sample_pdf, nested_pdf)

        importer = MassImporter.__new__(MassImporter)
        files = importer.scan_directory(tmp_dir)
        assert len(files) == 2  # sample_pdf + nested.pdf


# ---------------------------------------------------------------------------
# hash_utils tests
# ---------------------------------------------------------------------------

class TestHashUtils:
    def test_calcular_hash_archivo_consistency(self, sample_pdf):
        from hash_utils import calcular_hash_archivo
        h1 = calcular_hash_archivo(sample_pdf)
        h2 = calcular_hash_archivo(sample_pdf)
        assert h1 == h2

    def test_calcular_hash_archivo_different_files(self, sample_pdf, non_pdf_file):
        from hash_utils import calcular_hash_archivo
        h1 = calcular_hash_archivo(sample_pdf)
        h2 = calcular_hash_archivo(non_pdf_file)
        assert h1 != h2

    def test_calcular_hash_archivo_format(self, sample_pdf):
        from hash_utils import calcular_hash_archivo
        h = calcular_hash_archivo(sample_pdf)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_calcular_hash_texto_consistency(self):
        from hash_utils import calcular_hash_texto
        h1 = calcular_hash_texto("Hola mundo")
        h2 = calcular_hash_texto("Hola mundo")
        assert h1 == h2

    def test_calcular_hash_texto_different_inputs(self):
        from hash_utils import calcular_hash_texto
        h1 = calcular_hash_texto("Texto uno")
        h2 = calcular_hash_texto("Texto dos")
        assert h1 != h2

    def test_calcular_hash_texto_strips_whitespace(self):
        from hash_utils import calcular_hash_texto
        h1 = calcular_hash_texto("  Hola  ")
        h2 = calcular_hash_texto("Hola")
        assert h1 == h2

    def test_calcular_hash_texto_none_safe(self):
        from hash_utils import calcular_hash_texto
        h = calcular_hash_texto(None)
        assert len(h) == 64

    def test_calcular_hash_archivo_is_also_available_via_import_masiva(self, sample_pdf):
        from import_masiva import calcular_hash
        from hash_utils import calcular_hash_archivo
        assert calcular_hash(sample_pdf) == calcular_hash_archivo(sample_pdf)


# ---------------------------------------------------------------------------
# Manifest SHA-256 resume tests
# ---------------------------------------------------------------------------

class TestManifestResume:
    def test_resume_skips_imported_with_same_hash(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(2)
        m.record(ImportedFile(path="a.pdf", sha256="hash_a", status=ImportStatus.IMPORTED))
        assert m.is_processed("a.pdf", "hash_a") is True

    def test_resume_reprocesses_when_hash_changes(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(2)
        m.record(ImportedFile(path="a.pdf", sha256="old_hash", status=ImportStatus.IMPORTED))
        assert m.is_processed("a.pdf", "new_hash") is False

    def test_resume_skips_rejected_with_same_hash(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        m.record(ImportedFile(path="a.pdf", sha256="hash_a", status=ImportStatus.REJECTED, error="bad"))
        assert m.is_processed("a.pdf", "hash_a") is True

    def test_resume_reprocesses_error_status(self, manifest_path, tmp_dir):
        m = Manifest(manifest_path, tmp_dir)
        m.start(1)
        m.record(ImportedFile(path="a.pdf", sha256="hash_a", status=ImportStatus.ERROR, error="fail"))
        assert m.is_processed("a.pdf", "hash_a") is False


# ---------------------------------------------------------------------------
# Pathological content detection integration tests
# ---------------------------------------------------------------------------

class TestPathologicalDetection:
    def test_detectar_contenido_patologico_rejects_empty(self):
        import lectura
        info = lectura.detectar_contenido_patologico("", [])
        assert info["pathological"] is True

    def test_detectar_contenido_patologico_accepts_normal(self):
        import lectura
        page1 = (
            "Capitulo primero. La historia comienza en una tierra lejana donde los reinos "
            "luchaban por el poder y la supremacia militar. Los ejercitos marchaban sin descanso "
            "mientras los lideres planeaban sus estrategias en los consejos nocturnos. Las ciudades "
            "fortificadas resistian los asedios durante meses mientras la poblacion civil sufriendo "
            "la escasez de alimentos y medicinas esperaba un final que nunca parecia llegar pronto."
        )
        page2 = (
            "Capitulo segundo. Los personajes principales viajan hacia el norte buscando respuestas "
            "a sus preguntas existenciales sobre el sentido de la vida y la muerte. El filosofo "
            "los acompana con sus enseñanzas ancestrales mientras el paisaje cambia gradualmente "
            "de las llanuras verdes a las montanas nevadas. El frio intenso obliga al grupo a "
            "refugiarse en una cabaña abandonada donde encuentran un antiguo manuscrito olvidado."
        )
        text = page1 + "\n\n" + page2
        paginas = [page1, page2]
        info = lectura.detectar_contenido_patologico(text, paginas)
        assert info["pathological"] is False

    def test_detectar_contenido_patologico_rejects_repeated_pages(self):
        import lectura
        repeated = "Esta pagina se repite una y otra vez con el mismo texto exacto. " * 5
        paginas = [repeated, repeated]
        info = lectura.detectar_contenido_patologico(repeated * 2, paginas)
        assert info["pathological"] is True
