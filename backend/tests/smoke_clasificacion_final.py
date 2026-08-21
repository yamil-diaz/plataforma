# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import diag_catalog as dc

dc.SIN_INFO_PDF = False
FALLOS = []

def libro(id_, estado, pdf_fisico=None, extraccion=None, dups=(), content_length=None,
          n_pages=0, page_count=0, published=1, pdf_path=None, autor="A"):
    if pdf_fisico is None:
        pdf_fisico = {"ruta": None, "existe": False, "tamano": None, "tipo": "SIN_PDF_PATH", "magic_pdf": False}
    if extraccion is None:
        extraccion = {"ok": False, "longitud": None, "errores": []}
    return {
        "id": id_, "title": f"T{id_}", "author_name": autor, "published": published,
        "page_count": page_count, "content_length": content_length, "pdf_path": pdf_path,
        "n_book_pages": n_pages, "n_chapters": 0, "estado": estado,
        "pdf_fisico": pdf_fisico, "extraccion": extraccion,
        "grupo_duplicados": [], "copia_superior_id": None,
    }

def check(nombre, libro_, dups, esperado):
    clase, fuente, motivo = dc.clasificar_final(libro_, dups)
    ok = clase == esperado
    if not ok:
        FALLOS.append(f"{nombre}: esperado {esperado}, got {clase} ({motivo})")
    else:
        print(f"OK {nombre} -> {clase}")

seed_estado = {"placeholder": False, "pathological": True, "basura": False, "vacío": False,
               "errors": ["fabricado"], "content_length": 10000, "short_content": False,
               "repetition_ratio": 1.0}
check("1 seed sin PDF", libro(18, seed_estado), (), "REPROCESAR_DESDE_CONTENIDO")
check("5 seed con PDF no extraible", libro(18, seed_estado,
      pdf_fisico={"ruta": "/x/18.pdf", "existe": True, "tamano": 200, "tipo": "PDF_MAGIC_OK", "magic_pdf": True},
      pdf_path="/x/18.pdf"), (), "REPROCESAR_DESDE_CONTENIDO")

placeholder = {"placeholder": True, "pathological": False, "basura": False, "vacío": False,
               "errors": ["placeholder"], "content_length": 29, "short_content": True, "repetition_ratio": None}
check("3 placeholder sin PDF", libro(133, placeholder), (), "ELIMINAR")
check("3 placeholder con PDF no extraible", libro(133, placeholder,
      pdf_fisico={"ruta": "/x/133.pdf", "existe": True, "tamano": 500000, "tipo": "PDF_MAGIC_OK", "magic_pdf": True},
      pdf_path="/x/133.pdf"), (), "REPROCESAR_DESDE_PDF")

valido = {"placeholder": False, "pathological": False, "basura": False, "vacío": False,
          "errors": [], "content_length": 6000, "short_content": False, "repetition_ratio": None}
check("1 pdf existe + extraccion ok", libro(150, valido,
      pdf_fisico={"ruta": "/x/150.pdf", "existe": True, "tamano": 900, "tipo": "PDF_MAGIC_OK", "magic_pdf": True},
      extraccion={"ok": True, "longitud": 5800, "errores": []}, pdf_path="/x/150.pdf"), (), "REPROCESAR_DESDE_PDF")

contaminado = {"placeholder": False, "pathological": True, "basura": False, "vacío": False,
               "errors": ["duplicación"], "content_length": 20000, "short_content": False,
               "repetition_ratio": 0.36}
check("8 obra real contaminada (145) sin PDF", libro(145, contaminado), (), "REVISAR")
fabricado_puro = {"placeholder": False, "pathological": True, "basura": False, "vacío": False,
                  "errors": ["duplicación"], "content_length": 10000, "short_content": False,
                  "repetition_ratio": 1.0}
check("6 fabricado puro sin fuente", libro(199, fabricado_puro), (), "ELIMINAR")

check("7 duplicado", libro(133, valido, n_pages=5, page_count=5), {133, 159}, "REVISAR")
check("2 valido paginado SALVAR", libro(3, valido, n_pages=4, page_count=4), (), "SALVAR")
check("2 valido sin paginar", libro(3, valido, n_pages=0, page_count=0), (), "REPROCESAR_DESDE_CONTENIDO")
check("REVISAR anomalias", libro(82, {**valido, "errors": ["sospechoso"]}), (), "REVISAR")

print()
if FALLOS:
    for f in FALLOS:
        print("FALLO:", f)
    sys.exit(1)
print("TODOS LOS ESCENARIOS OK")