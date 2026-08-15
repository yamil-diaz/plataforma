"""Pruebas del almacenamiento persistente de PDFs (STORAGE_DIR + resolver de
pdf_path + migración de legado). Usan directorios temporales; NO tocan una
base de datos real ni producción."""

import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import server  # noqa: E402


@pytest.fixture()
def storage_tmp(tmp_path):
    """Redirige STORAGE_DIR/STORAGE_BOOKS a un directorio temporal."""
    old_dir = server.STORAGE_DIR
    old_books = server.STORAGE_BOOKS
    nuevo = tmp_path / "storage"
    server.STORAGE_DIR = str(nuevo)
    server.STORAGE_BOOKS = str(nuevo / "books")
    os.makedirs(server.STORAGE_BOOKS, exist_ok=True)
    yield nuevo
    server.STORAGE_DIR = old_dir
    server.STORAGE_BOOKS = old_books


class TestResolverPdfPath:
    def test_absoluta_existente_se_usa_tal_cual(self, storage_tmp, tmp_path):
        archivo = tmp_path / "real.pdf"
        archivo.write_bytes(b"%PDF-1.7 test")
        assert server._resolver_pdf_path(str(archivo)) == str(archivo)

    def test_absoluta_inexistente_resuelve_por_nombre_en_storage(self, storage_tmp):
        destino = os.path.join(server.STORAGE_BOOKS, "abc_migrado.pdf")
        with open(destino, "wb") as f:
            f.write(b"%PDF-1.7 migrado")
        ruta_bd = "/opt/render/project/src/backend/storage/books/abc_migrado.pdf"
        assert server._resolver_pdf_path(ruta_bd) == destino

    def test_relativa_resuelve_dentro_de_storage_books(self, storage_tmp):
        destino = os.path.join(server.STORAGE_BOOKS, "relativo.pdf")
        with open(destino, "wb") as f:
            f.write(b"%PDF-1.7 relativo")
        assert server._resolver_pdf_path("relativo.pdf") == destino

    def test_inexistente_devuelve_none(self, storage_tmp):
        assert server._resolver_pdf_path("/opt/lo/que/sea.pdf") is None

    def test_vacio_o_none_devuelve_none(self, storage_tmp):
        assert server._resolver_pdf_path(None) is None
        assert server._resolver_pdf_path("") is None


class TestMigracionLegacy:
    def test_copia_archivos_y_es_idempotente(self, tmp_path, monkeypatch):
        origen = tmp_path / "origen"
        destino = tmp_path / "destino"
        for sub in ("books", "covers", "videos"):
            (origen / sub).mkdir(parents=True, exist_ok=True)
        (origen / "books" / "a.pdf").write_bytes(b"%PDF-1.7 a")
        (origen / "books" / "b.pdf").write_bytes(b"%PDF-1.7 b")
        (origen / "covers" / "c.jpg").write_bytes(b"jpg")
        (origen / "videos" / "v.mp4").write_bytes(b"mp4")
        monkeypatch.setattr(server, "DEFAULT_STORAGE_DIR", str(origen))
        monkeypatch.setattr(server, "STORAGE_DIR", str(destino))
        monkeypatch.setattr(server, "STORAGE_BOOKS", str(destino / "books"))
        server._migrar_storage_legacy()
        assert (destino / "books" / "a.pdf").read_bytes() == b"%PDF-1.7 a"
        assert (destino / "books" / "b.pdf").read_bytes() == b"%PDF-1.7 b"
        assert (destino / "covers" / "c.jpg").read_bytes() == b"jpg"
        assert (destino / "videos" / "v.mp4").read_bytes() == b"mp4"
        server._migrar_storage_legacy()
        assert len(list((destino / "books").iterdir())) == 2

    def test_no_copia_si_es_el_mismo_directorio(self, tmp_path, monkeypatch):
        mismo = tmp_path / "mismo"
        (mismo / "books").mkdir(parents=True)
        (mismo / "books" / "x.pdf").write_bytes(b"x")
        monkeypatch.setattr(server, "DEFAULT_STORAGE_DIR", str(mismo))
        monkeypatch.setattr(server, "STORAGE_DIR", str(mismo))
        server._migrar_storage_legacy()
        assert (mismo / "books" / "x.pdf").read_bytes() == b"x"

    def test_nunca_borra_archivos_de_origen(self, tmp_path, monkeypatch):
        origen = tmp_path / "origen"
        destino = tmp_path / "destino"
        (origen / "books").mkdir(parents=True)
        (origen / "books" / "a.pdf").write_bytes(b"%PDF-1.7 a")
        monkeypatch.setattr(server, "DEFAULT_STORAGE_DIR", str(origen))
        monkeypatch.setattr(server, "STORAGE_DIR", str(destino))
        monkeypatch.setattr(server, "STORAGE_BOOKS", str(destino / "books"))
        server._migrar_storage_legacy()
        assert (origen / "books" / "a.pdf").exists()


class TestDownloadConAlmacenamientoPersistente:
    def test_descarga_pdf_resuelto_en_storage(self, client, fake_db, storage_tmp):
        archivo = os.path.join(server.STORAGE_BOOKS, "libro_53.pdf")
        with open(archivo, "wb") as f:
            f.write(b"%PDF-1.7 contenido de prueba")
        fake_db.state["books"][53]["pdf_path"] = "/opt/render/legacy/libro_53.pdf"
        r = client.get("/api/books/53/download")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content == b"%PDF-1.7 contenido de prueba"

    def test_descarga_fallback_genera_pdf_de_texto_sin_pdf(self, client, fake_db, storage_tmp):
        r = client.get("/api/books/10/download")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"