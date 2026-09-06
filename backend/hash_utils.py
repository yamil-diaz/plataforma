# -*- coding: utf-8 -*-
"""
hash_utils.py — Funciones centralizadas de hashing SHA-256.

Única fuente de verdad para cómputo de hashes en todo el proyecto.
Todos los importadores, endpoints y herramientas deben usar estas funciones
en lugar de calcular hashes por su cuenta.
"""
import hashlib


def calcular_hash_archivo(filepath: str) -> str:
    """SHA-256 del contenido binario de un archivo.

    Usado para: PDFs, imágenes, cualquier archivo en disco.
    El hash se calcula sobre el archivo TAL CUAL está en disco,
    sin transformación previa.
    """
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def calcular_hash_texto(text: str) -> str:
    """SHA-256 de contenido textual normalizado.

    Usado para: libros de Gutenberg, contenido de texto plano.
    Normalización: strip() para eliminar whitespace trailing,
    encode UTF-8 para consistencia.
    """
    normalizado = (text or "").strip()
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()
