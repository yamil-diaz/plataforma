# -*- coding: utf-8 -*-
"""
Tests para demostrar que el seed automático de libros NO se ejecuta en producción.

FASE 4 — Corrección pre-FASE 4: desactivar seed automático en producción.

Verifica:
1. En producción (ENV=production o RENDER=true), IS_PRODUCTION es True.
2. En desarrollo, IS_PRODUCTION es False.
3. init_db() contiene la condición 'not IS_PRODUCTION' para el seed de libros.
"""

import os
import sys
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# database.py requiere DATABASE_URL a nivel de módulo, así que siempre
# necesitamos tenerlo disponible al recargar.
DB_URL = "postgresql://postgres:test@localhost:5432/test_db"


class TestISProductionDetection:
    """Verifica que IS_PRODUCTION se detecta correctamente."""

    def test_render_true_activa_is_production(self, monkeypatch):
        """RENDER=true debe activar IS_PRODUCTION."""
        monkeypatch.setenv("RENDER", "true")
        monkeypatch.delenv("ENV", raising=False)
        monkeypatch.setenv("DATABASE_URL", DB_URL)

        import database
        import importlib
        importlib.reload(database)

        assert database.IS_PRODUCTION is True

    def test_env_production_activa_is_production(self, monkeypatch):
        """ENV=production debe activar IS_PRODUCTION."""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.delenv("RENDER", raising=False)
        monkeypatch.setenv("DATABASE_URL", DB_URL)

        import database
        import importlib
        importlib.reload(database)

        assert database.IS_PRODUCTION is True

    def test_sin_env_no_es_production(self, monkeypatch):
        """Sin ENV ni RENDER, IS_PRODUCTION debe ser False."""
        monkeypatch.delenv("ENV", raising=False)
        monkeypatch.delenv("RENDER", raising=False)
        monkeypatch.setenv("DATABASE_URL", DB_URL)

        import database
        import importlib
        importlib.reload(database)

        assert database.IS_PRODUCTION is False

    def test_render_false_no_es_production(self, monkeypatch):
        """RENDER=false no debe activar IS_PRODUCTION."""
        monkeypatch.setenv("RENDER", "false")
        monkeypatch.delenv("ENV", raising=False)
        monkeypatch.setenv("DATABASE_URL", DB_URL)

        import database
        import importlib
        importlib.reload(database)

        assert database.IS_PRODUCTION is False


class TestSeedCondition:
    """Verifica que la condición del seed incluye IS_PRODUCTION."""

    def test_seed_condicion_incluye_is_production(self):
        """init_db() debe incluir 'not IS_PRODUCTION' antes del seed de libros."""
        import inspect
        import database

        source = inspect.getsource(database.init_db)
        assert "not IS_PRODUCTION" in source, \
            "init_db() debe incluir 'not IS_PRODUCTION' en la condición del seed"

    def test_seed_solo_ejecuta_en_desarrollo(self):
        """La condición debe ser 'count == 0 and not IS_PRODUCTION'."""
        import inspect
        import database

        source = inspect.getsource(database.init_db)
        # Buscar la línea exacta de la condición
        assert "count == 0 and not IS_PRODUCTION" in source, \
            "La condición debe ser 'count == 0 and not IS_PRODUCTION'"

    def test_seed_no_ejecuta_en_produccion(self):
        """En producción, el seed NO debe ejecutarse aunque books esté vacío."""
        import inspect
        import database

        source = inspect.getsource(database.init_db)
        # Verificar la condición exacta
        assert "if count == 0 and not IS_PRODUCTION:" in source, \
            "La condición debe ser 'if count == 0 and not IS_PRODUCTION:'"


class TestSeedExistingData:
    """Verifica que los 4 libros seed existentes son conocidos."""

    def test_seed_data_exists_in_code(self):
        """Los 4 libros seed deben estar definidos en init_db()."""
        import inspect
        import database

        source = inspect.getsource(database.init_db)
        assert "El Principito" in source
        assert "Cien Años de Soledad" in source
        assert "Don Quijote de la Mancha" in source
        assert "1984" in source

    def test_seed_source标记(self):
        """Los libros seed deben tener source='seed'."""
        import inspect
        import database

        source = inspect.getsource(database.init_db)
        assert "'seed'" in source
