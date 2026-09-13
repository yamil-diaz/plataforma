# -*- coding: utf-8 -*-
"""
flow_service.py — Integración con Flow (pasarela de pagos).

Documentación oficial: https://developers.flow.cl/api

API:
- Sandbox: https://sandbox.flow.cl/api
- Producción: https://www.flow.cl/api

Autenticación:
- apiKey como parámetro en el body/query
- Firma HMAC-SHA256 con SecretKey
- Parámetro de firma: s
- Formato de firma: key + value concatenados (sin =, sin &)
"""
import hashlib
import hmac
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from decimal import Decimal, ROUND_HALF_UP

FLOW_API_KEY = os.getenv("FLOW_API_KEY", "")
FLOW_SECRET_KEY = os.getenv("FLOW_SECRET_KEY", "")
FLOW_BASE_URL = os.getenv("FLOW_BASE_URL", "https://sandbox.flow.cl/api")
FLOW_RETURN_URL = os.getenv("FLOW_RETURN_URL", "https://aeternumlibrary.com/checkout/result")
FLOW_CONFIRMATION_URL = os.getenv("FLOW_CONFIRMATION_URL", "https://aeternumlibrary.com/api/flow/webhook")

# ── Configuración centralizada de monedas ─────────────────────────────────────
# Cada moneda define:
#   decimals:    cantidad de decimales para la unidad más baja (ej: 2 → centavos)
#   symbol:      símbolo para display
#   flow_tested: True si Flow la ha probado en sandbox/producción para esta cuenta
#
# Para habilitar una moneda nueva:
#   1. Agregar entrada en CURRENCY_CONFIG con flow_tested=False
#   2. Agregarla a ENABLED_DIGITAL_CURRENCIES
#   3. Probar en sandbox Flow
#   4. Marcar flow_tested=True

CURRENCY_CONFIG = {
    "PEN": {"decimals": 2, "symbol": "S/",  "flow_tested": True},
    "CLP": {"decimals": 0, "symbol": "$",   "flow_tested": True},
    "MXN": {"decimals": 2, "symbol": "MX$", "flow_tested": True},
    "EUR": {"decimals": 2, "symbol": "\u20ac", "flow_tested": False},
    "USD": {"decimals": 2, "symbol": "US$", "flow_tested": False},
}

# Monedas habilitadas para comercio digital.
# Solo las que aparecen aquí pueden usarse en checkout.
# Para activar EUR/USD: agregar a esta lista Y confirmar en sandbox Flow.
ENABLED_DIGITAL_CURRENCIES = ["PEN", "CLP", "MXN"]

# Símbolos para display (derivado de CURRENCY_CONFIG)
CURRENCY_SYMBOLS = {code: cfg["symbol"] for code, cfg in CURRENCY_CONFIG.items()}


def _get_flow_config():
    """Retorna la configuración de Flow. Falta si hay variables sin configurar."""
    missing = []
    if not FLOW_API_KEY:
        missing.append("FLOW_API_KEY")
    if not FLOW_SECRET_KEY:
        missing.append("FLOW_SECRET_KEY")
    return missing


def _compute_signature(params: dict) -> str:
    """
    Calcula la firma HMAC-SHA256 para Flow API.

    Según documentación oficial:
    1. Ordenar parámetros alfabéticamente por nombre
    2. Concatenar: key + value (sin =, sin &)
    3. HMAC-SHA256 con SecretKey

    Ejemplo: params = {"amount": "5000", "apiKey": "XXX", "currency": "CLP"}
    → "amount5000apiKeyXXXcurrencyCLP"
    → hmac.new(secretKey, to_sign, sha256).hexdigest()
    """
    sorted_params = sorted(params.items())
    to_sign = "".join(f"{k}{v}" for k, v in sorted_params)
    return hmac.new(
        FLOW_SECRET_KEY.encode("utf-8"),
        to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_payment(
    order_number: str,
    amount: int,
    subject: str,
    email: str,
    currency: str = "PEN",
    return_url: str = None,
    confirmation_url: str = None,
) -> dict:
    """
    Crea una orden de pago en Flow API.

    Args:
        order_number: commerceOrder — ID único de la orden en Aeternum
        amount: Monto en la unidad más baja de la moneda (ej: 5000 = $50.00 CLP, 2590 = S/25.90 PEN)
        subject: Descripción de la orden
        email: Email del pagador
        currency: Código de moneda (PEN, CLP, MXN)
        return_url: URL de retorno después del pago
        confirmation_url: URL de notificación webhook

    Returns:
        dict con token, url (ya concatenada con ?token=), flowOrder, o error
    """
    missing = _get_flow_config()
    if missing:
        return {"success": False, "error": f"Flow no configurado: {', '.join(missing)}"}

    params = {
        "apiKey": FLOW_API_KEY,
        "commerceOrder": order_number,
        "subject": subject,
        "currency": currency,
        "amount": str(amount),
        "email": email,
        "urlConfirmation": confirmation_url or FLOW_CONFIRMATION_URL,
        "urlReturn": return_url or FLOW_RETURN_URL,
    }

    signature = _compute_signature(params)
    params["s"] = signature

    url = f"{FLOW_BASE_URL}/payment/create"

    try:
        encoded_data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=encoded_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "AeternumBackend/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Flow retorna: {"url": "...", "token": "...", "flowOrder": ...}
        if result.get("token") and result.get("url"):
            return {
                "success": True,
                "token": result["token"],
                "url": f"{result['url']}?token={result['token']}",
                "flowOrder": result.get("flowOrder"),
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Error desconocido de Flow"),
                "details": result,
            }

    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        return {
            "success": False,
            "error": f"Error HTTP {e.code} de Flow",
            "details": body,
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"Error de conexión con Flow: {e.reason}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error inesperado al crear pago: {str(e)}",
        }


def verify_payment(token: str) -> dict:
    """
    Consulta el estado de un pago en Flow usando /payment/getStatus.

    Args:
        token: Token de la transacción enviado por Flow

    Returns:
        dict con success y data (flowOrder, commerceOrder, status, amount, currency, etc.)
    """
    missing = _get_flow_config()
    if missing:
        return {"success": False, "error": f"Flow no configurado: {', '.join(missing)}"}

    params = {
        "apiKey": FLOW_API_KEY,
        "token": token,
    }

    signature = _compute_signature(params)
    params["s"] = signature

    url = f"{FLOW_BASE_URL}/payment/getStatus?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AeternumBackend/1.0",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        return {"success": True, "data": result}

    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        return {
            "success": False,
            "error": f"Error HTTP {e.code} al consultar pago",
            "details": body,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error al consultar pago: {str(e)}",
        }


def is_payment_approved(payment_data: dict) -> bool:
    """Determina si un pago de Flow está aprobado. status=2 es pagado."""
    return payment_data.get("status") == 2


def is_payment_rejected(payment_data: dict) -> bool:
    """Determina si un pago fue rechazado o cancelado. status=3 o status=4."""
    return payment_data.get("status") in (3, 4)


def get_payment_status_code(payment_data: dict) -> str:
    """
    Convierte el estado numérico de Flow a texto.
    1=pendiente, 2=aprobado, 3=rechazado, 4=cancelado
    """
    status_map = {
        1: "pending",
        2: "approved",
        3: "rejected",
        4: "cancelled",
    }
    return status_map.get(payment_data.get("status"), "unknown")


def format_amount_for_flow(amount: Decimal, currency: str = "PEN") -> int:
    """
    Convierte un monto Decimal a entero para Flow, usando los decimales
    correctos por moneda.

    PEN (2 decimales): 25.90  → 2590
    CLP (0 decimales): 50000  → 50000
    MXN (2 decimales): 150.50 → 15050
    EUR (2 decimales): 10.50  → 1050
    USD (2 decimales): 25.00  → 2500

    Raises:
        ValueError si la moneda no está en CURRENCY_CONFIG.
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    currency = (currency or "PEN").upper()
    if currency not in CURRENCY_CONFIG:
        raise ValueError(f"Moneda no soportada para Flow: {currency}")
    factor = 10 ** CURRENCY_CONFIG[currency]["decimals"]
    scaled = amount * factor
    return int(scaled.to_integral_value(rounding=ROUND_HALF_UP))


def get_currency_symbol(currency: str) -> str:
    """Retorna el símbolo de la moneda para display."""
    return CURRENCY_SYMBOLS.get(currency, currency)


def get_currency_decimals(currency: str) -> int:
    """Retorna la cantidad de decimales para una moneda. Lanza ValueError si no existe."""
    if currency not in CURRENCY_CONFIG:
        raise ValueError(f"Moneda no configurada: {currency}")
    return CURRENCY_CONFIG[currency]["decimals"]


def is_currency_enabled(currency: str) -> bool:
    """Verifica si una moneda está habilitada para comercio digital."""
    return currency in ENABLED_DIGITAL_CURRENCIES
