"""
Script para leer imágenes usando Google Gemini API REST.
Uso: python read_image.py <ruta_imagen>
"""
import sys
import os
import base64
import json
import urllib.request
from pathlib import Path


def read_image(image_path: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "ERROR: GEMINI_API_KEY no está configurada."

    path = Path(image_path)
    if not path.exists():
        return f"ERROR: No se encontró la imagen: {image_path}"

    with open(path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/png")

    # Listar modelos disponibles primero
    models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(models_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            models_data = json.loads(resp.read().decode())
            flash_models = [m["name"] for m in models_data.get("models", []) if "flash" in m["name"].lower() and "generateContent" in m.get("supportedGenerationMethods", [])]
            if flash_models:
                model_name = flash_models[0]
            else:
                all_models = [m["name"] for m in models_data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
                model_name = all_models[0] if all_models else "gemini-1.5-flash"
    except Exception:
        model_name = "gemini-1.5-flash"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [
                {"text": "Describe esta imagen en detalle. Si es una interfaz web, lista todos los textos, botones, precios, opciones y datos visibles. Sé exacto con números, nombres y textos."},
                {"inline_data": {"mime_type": mime_type, "data": image_data}}
            ]
        }]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"ERROR HTTP {e.code}: {body}"
    except Exception as e:
        return f"ERROR: {str(e)}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python read_image.py <ruta_imagen>")
        sys.exit(1)
    print(read_image(sys.argv[1]))
