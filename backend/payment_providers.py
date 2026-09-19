# -*- coding: utf-8 -*-
"""
payment_providers.py — Capa de abstracción de proveedores de pago.

Define la interfaz común (PaymentProvider) e implementaciones concretas:
- PaddleProvider: productos digitales (internacional, multimoneda)
- CulqiProvider: productos físicos en Perú (PEN)

Ningún otro módulo debe acoplarse directamente a Paddle o Culqi.
El routing se hace en commerce_service / server.py mediante get_provider().
"""
import hashlib
import hmac
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE MONEDAS
# ══════════════════════════════════════════════════════════════════════════════
# Monedas soportadas por Paddle (2024-2025).
# Paddle maneja internamente la conversión y checkout localizado.
# El sistema debe aceptar estas monedas y tratar correctamente sus decimales.

PADDLE_CURRENCY_CONFIG = {
    # 2 decimales
    "USD": {"decimals": 2, "symbol": "US$"},
    "EUR": {"decimals": 2, "symbol": "\u20ac"},
    "GBP": {"decimals": 2, "symbol": "\u00a3"},
    "PEN": {"decimals": 2, "symbol": "S/"},
    "MXN": {"decimals": 2, "symbol": "MX$"},
    "BRL": {"decimals": 2, "symbol": "R$"},
    "ARS": {"decimals": 2, "symbol": "AR$"},
    "COP": {"decimals": 2, "symbol": "CO$"},
    "CAD": {"decimals": 2, "symbol": "CA$"},
    "AUD": {"decimals": 2, "symbol": "A$"},
    "CHF": {"decimals": 2, "symbol": "CHF"},
    "PLN": {"decimals": 2, "symbol": "z\u0142"},
    "SEK": {"decimals": 2, "symbol": "kr"},
    "DKK": {"decimals": 2, "symbol": "kr"},
    "NOK": {"decimals": 2, "symbol": "kr"},
    "CZK": {"decimals": 2, "symbol": "K\u010d"},
    "HUF": {"decimals": 2, "symbol": "Ft"},
    "RON": {"decimals": 2, "symbol": "lei"},
    "SGD": {"decimals": 2, "symbol": "S$"},
    "HKD": {"decimals": 2, "symbol": "HK$"},
    "NZD": {"decimals": 2, "symbol": "NZ$"},
    "TRY": {"decimals": 2, "symbol": "\u20ba"},
    "INR": {"decimals": 2, "symbol": "\u20b9"},
    "TWD": {"decimals": 2, "symbol": "NT$"},
    "ZAR": {"decimals": 2, "symbol": "R"},
    "ILS": {"decimals": 2, "symbol": "\u20aa"},
    "THB": {"decimals": 2, "symbol": "\u0e3f"},
    "CNY": {"decimals": 2, "symbol": "\u00a5"},
    "UAH": {"decimals": 2, "symbol": "\u20b4"},
    # 0 decimales
    "CLP": {"decimals": 0, "symbol": "$"},
    "JPY": {"decimals": 0, "symbol": "\u00a5"},
    "KRW": {"decimals": 0, "symbol": "\u20a9"},
    "VND": {"decimals": 0, "symbol": "\u20ab"},
}

# Las monedas habilitadas para checkout digital se derivan de PADDLE_CURRENCY_CONFIG.
# Si Paddle agrega monedas, se habilitan automáticamente.
ENABLED_DIGITAL_CURRENCIES = list(PADDLE_CURRENCY_CONFIG.keys())


def get_currency_symbol(currency: str) -> str:
    """Retorna el símbolo de la moneda para display."""
    cfg = PADDLE_CURRENCY_CONFIG.get(currency)
    if cfg:
        return cfg["symbol"]
    return currency


def get_currency_decimals(currency: str) -> int:
    """Retorna la cantidad de decimales para una moneda."""
    cfg = PADDLE_CURRENCY_CONFIG.get(currency)
    if cfg is None:
        raise ValueError(f"Moneda no soportada: {currency}")
    return cfg["decimals"]


def is_currency_enabled(currency: str) -> bool:
    """Verifica si una moneda está habilitada para comercio digital."""
    return currency in PADDLE_CURRENCY_CONFIG


def format_amount_for_provider(amount: Decimal, currency: str) -> int:
    """
    Convierte un monto Decimal a entero para el proveedor de pago,
    usando los decimales correctos por moneda.

    Ejemplos:
        PEN (2 decimales): 25.90  -> 2590
        CLP (0 decimales): 50000  -> 50000
        JPY (0 decimales): 1000   -> 1000
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    currency = (currency or "USD").upper()
    decimals = get_currency_decimals(currency)
    factor = 10 ** decimals
    scaled = amount * factor
    return int(scaled.to_integral_value(rounding=ROUND_HALF_UP))


# ══════════════════════════════════════════════════════════════════════════════
# ABSTRACCIÓN: PaymentProvider
# ══════════════════════════════════════════════════════════════════════════════

class PaymentProvider(ABC):
    """
    Interfaz base para proveedores de pago.

    Cada implementación concreta debe soportar:
    - create_checkout: crear una sesión de pago
    - verify_webhook: verificar autenticidad del webhook
    - parse_webhook_event: extraer datos normalizados del evento
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del proveedor (e.g., 'paddle', 'culqi')."""

    @abstractmethod
    def create_checkout(self, order_number: str, amount: Decimal, currency: str,
                        description: str, email: str, metadata: dict = None) -> dict:
        """
        Crea un checkout/redirección de pago.

        Returns:
            {
                "success": True,
                "checkout_url": "https://...",
                "provider_order_id": "...",
                "provider_token": "..."
            }
            o
            {"success": False, "error": "..."}
        """

    @abstractmethod
    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        """Verifica la autenticidad/firma de un webhook."""

    @abstractmethod
    def parse_webhook_event(self, headers: dict, body: bytes) -> dict:
        """
        Parsea y normaliza un evento de webhook.

        Returns:
            {
                "provider_event_id": "...",
                "event_type": "payment_completed|...",
                "order_number": "...",
                "provider_order_id": "...",
                "provider_payment_id": "...",
                "amount": Decimal,
                "currency": "...",
                "status": "approved|rejected|cancelled|pending",
                "raw": {...}
            }
        """


# ══════════════════════════════════════════════════════════════════════════════
# PADDLE — Productos Digitales (Internacional)
# ══════════════════════════════════════════════════════════════════════════════

class PaddleProvider(PaymentProvider):
    """
    Paddle para productos digitales.

    Paddle maneja:
    - Checkout localizado (múltiples monedas, impuestos)
    - Webhooks con firma HMAC
    - Soporte internacional

    Docs: https://developer.paddle.com/
    """

    def __init__(self):
        self.api_key = os.getenv("PADDLE_API_KEY", "")
        self.client_token = os.getenv("PADDLE_CLIENT_TOKEN", "")
        self.webhook_secret = os.getenv("PADDLE_WEBHOOK_SECRET", "")
        self.environment = os.getenv("PADDLE_ENVIRONMENT", "sandbox")

        if self.environment == "production":
            self.api_base = "https://api.paddle.com"
            self.checkout_base = "https://checkout.paddle.com"
        else:
            self.api_base = "https://sandbox-api.paddle.com"
            self.checkout_base = "https://sandbox-checkout.paddle.com"

    @property
    def name(self) -> str:
        return "paddle"

    def _is_configured(self) -> list:
        """Retorna lista de variables faltantes."""
        missing = []
        if not self.api_key:
            missing.append("PADDLE_API_KEY")
        if not self.webhook_secret:
            missing.append("PADDLE_WEBHOOK_SECRET")
        return missing

    def create_checkout(self, order_number: str, amount: Decimal, currency: str,
                        description: str, email: str, metadata: dict = None) -> dict:
        """
        Crea un checkout de Paddle Billing.

        Usa la API de Paddle Billing (no Classic):
        - POST /transactions en api.paddle.com
        - Genera una URL de checkout

        Items: usa non-catalog price (no requiere precios pre-creados en Paddle).
        Monto en la unidad más baja de la moneda (centavos para 2 dec, unidad entera para 0 dec).
        """
        missing = self._is_configured()
        if missing:
            return {"success": False, "error": f"Paddle no configurado: {', '.join(missing)}"}

        amount_int = format_amount_for_provider(amount, currency)

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return_url = f"{frontend_url}/checkout/result"

        payload = {
            "items": [{
                "quantity": 1,
                "price": {
                    "description": description,
                    "name": description,
                    "tax_mode": "account_setting",
                    "unit_price": {
                        "amount": str(amount_int),
                        "currency_code": currency,
                    },
                    "product": {
                        "name": description[:200],
                        "tax_category": "ebooks",
                    },
                },
            }],
            "currency_code": currency,
            "collection_mode": "automatic",
            "return_url": return_url,
            "custom_data": {
                "order_number": order_number,
                **(metadata or {}),
            },
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.api_base}/transactions",
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "Paddle-Version": "3",
                    "User-Agent": "AeternumBackend/2.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            # Paddle Billing retorna HTTP 201 con { "data": {...} }
            data = result.get("data", {})
            if data.get("id"):
                checkout_url = data.get("checkout", {}).get("url", "")
                return {
                    "success": True,
                    "checkout_url": checkout_url,
                    "provider_order_id": str(data.get("id", "")),
                    "provider_token": data.get("id", ""),
                }
            else:
                error = result.get("error", {})
                return {
                    "success": False,
                    "error": error.get("message", "Error desconocido de Paddle"),
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
                "error": f"Error HTTP {e.code} de Paddle",
                "details": body,
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"Error de conexión con Paddle: {e.reason}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error inesperado al crear checkout: {str(e)}",
            }

    def get_transaction_status(self, transaction_id: str) -> dict:
        """
        Consulta el estado de una transacción directamente vía API de Paddle.
        Usado como fallback cuando el webhook no llega.
        """
        if not self.api_key or not transaction_id:
            return {"success": False, "error": "API key o transaction_id no disponible"}

        try:
            req = urllib.request.Request(
                f"{self.api_base}/transactions/{transaction_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Paddle-Version": "3",
                    "User-Agent": "AeternumBackend/2.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))

            data = result.get("data", {})
            paddle_status = data.get("status", "")

            status_map = {
                "completed": "approved",
                "paid": "approved",
                "ready": "pending",
                "pending": "pending",
                "cancelled": "cancelled",
                "canceled": "cancelled",
                "failed": "rejected",
            }
            status = status_map.get(paddle_status, "pending")

            print(f"[PAYMENT DEBUG] Paddle transaction request", flush=True)
            print(f"[PAYMENT DEBUG] transaction_id={transaction_id}", flush=True)
            print(f"[PAYMENT DEBUG] Paddle HTTP status=200", flush=True)
            print(f"[PAYMENT DEBUG] Paddle transaction status={paddle_status}", flush=True)
            print(f"[PAYMENT DEBUG] mapped internal status={status}", flush=True)

            details = data.get("details", {})
            amount = Decimal("0")
            if details:
                totals = details.get("totals", {})
                if totals:
                    amount = Decimal(str(totals.get("total", "0")))

            currency = ""
            checkout = data.get("checkout", {})
            if checkout:
                currency = checkout.get("currency_code", "")

            payment_id = ""
            payments = data.get("payments", [])
            if payments:
                payment_id = str(payments[0].get("id", ""))

            return {
                "success": True,
                "status": status,
                "paddle_status": paddle_status,
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": currency,
                "provider_payment_id": payment_id,
            }

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            print(f"[PAYMENT DEBUG] Paddle API ERROR", flush=True)
            print(f"[PAYMENT DEBUG] HTTP status={e.code}", flush=True)
            print(f"[PAYMENT DEBUG] error type=HTTPError", flush=True)
            return {"success": False, "error": f"HTTP {e.code}: {body[:300]}"}
        except Exception as e:
            print(f"[PAYMENT DEBUG] Paddle API ERROR", flush=True)
            print(f"[PAYMENT DEBUG] error type={type(e).__name__}", flush=True)
            return {"success": False, "error": str(e)}

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        """
        Verifica la firma del webhook de Paddle.

        Paddle v1 usa HMAC-SHA256:
        - Header: Paddle-Signature
        - Formato: ts=timestamp;h1=hex_digest
        - Input: timestamp:body
        """
        if not self.webhook_secret:
            return False

        signature_header = headers.get("paddle-signature", "")
        if not signature_header:
            return False

        parts = {}
        for item in signature_header.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                parts[key.strip()] = value.strip()

        ts = parts.get("ts", "")
        h1 = parts.get("h1", "")

        if not ts or not h1:
            return False

        # Verificar que el timestamp no sea muy antiguo (15 minutos)
        # Paddle puede enviar webhooks con delay; ser tolerante
        try:
            ts_int = int(ts)
            if abs(time.time() - ts_int) > 900:
                return False
        except ValueError:
            return False

        # Calcular firma esperada
        signed_payload = f"{ts}:{body.decode('utf-8')}"
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(h1, expected)

    def parse_webhook_event(self, headers: dict, body: bytes) -> dict:
        """
        Parsea un evento de webhook de Paddle.

        Eventos relevantes:
        - transaction.completed -> pago aprobado
        - transaction.updated -> cambio de estado
        - transaction.payment_failed -> pago fallido
        """
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            return {"error": "JSON inválido"}

        event_type = data.get("event_type", "")
        entity = data.get("data", {})

        # Extraer datos de la transacción
        transaction_id = str(entity.get("id", ""))
        order_number = ""
        custom_data = entity.get("custom_data", {})
        if custom_data:
            order_number = custom_data.get("order_number", "")

        # Paddle envía el monto en centavos (o unidad entera para 0 dec)
        # Necesitamos el monto y moneda
        amount = Decimal("0")
        currency = ""

        # El checkout tiene la info del precio
        checkout = entity.get("checkout", {})
        if checkout:
            currency = checkout.get("currency_code", "")

        # Para el monto, usar transaction_details o invoice
        details = entity.get("details", {})
        if details:
            totals = details.get("totals", {})
            if totals:
                # Paddle envía el monto total en la unidad más baja
                total_str = str(totals.get("total", "0"))
                amount = Decimal(total_str)

        # Mapear estado de Paddle a nuestro formato
        status = "pending"
        if event_type == "transaction.completed":
            status = "approved"
        elif event_type == "transaction.payment_failed":
            status = "rejected"
        elif event_type == "transaction.cancelled":
            status = "cancelled"
        elif entity.get("status") == "completed":
            status = "approved"
        elif entity.get("status") == "failed":
            status = "rejected"

        # Payment ID
        payment_id = ""
        payments = entity.get("payments", [])
        if payments:
            payment_id = str(payments[0].get("id", ""))

        return {
            "provider_event_id": str(entity.get("id", "")),
            "event_type": event_type,
            "order_number": order_number,
            "provider_order_id": transaction_id,
            "provider_payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": status,
            "raw": data,
        }


# ══════════════════════════════════════════════════════════════════════════════
# CULQI — Productos Físicos (Perú)
# ══════════════════════════════════════════════════════════════════════════════

class CulqiProvider(PaymentProvider):
    """
    Culqi para productos físicos en Perú.

    Culqi maneja:
    - Tokenización de tarjetas (frontend)
    - Cobro con token (backend)
    - Webhooks con firma HMAC

    Docs: https://docs.culqi.com/
    """

    def __init__(self):
        self.public_key = os.getenv("CULQI_PUBLIC_KEY", "")
        self.secret_key = os.getenv("CULQI_SECRET_KEY", "")
        self.webhook_secret = os.getenv("CULQI_WEBHOOK_SECRET", "")
        self.environment = os.getenv("CULQI_ENVIRONMENT", "sandbox")

        if self.environment == "production":
            self.api_base = "https://api.culqi.com"
        else:
            self.api_base = "https://sandbox-api.culqi.com"

    @property
    def name(self) -> str:
        return "culqi"

    def _is_configured(self) -> list:
        """Retorna lista de variables faltantes."""
        missing = []
        if not self.secret_key:
            missing.append("CULQI_SECRET_KEY")
        return missing

    def create_checkout(self, order_number: str, amount: Decimal, currency: str,
                        description: str, email: str, metadata: dict = None) -> dict:
        """
        Crea un cobro en Culqi.

        Culqi funciona con tokenización:
        1. Frontend tokeniza la tarjeta con CULQI_PUBLIC_KEY
        2. Backend crea el cargo con el token

        Este método retorna los datos necesarios para el frontend.
        El cargo real se hace después de recibir el token del frontend.
        """
        missing = self._is_configured()
        if missing:
            return {"success": False, "error": f"Culqi no configurado: {', '.join(missing)}"}

        # Culqi usa centavos para PEN (2 decimales)
        amount_int = format_amount_for_provider(amount, currency)

        return {
            "success": True,
            "checkout_type": "token",
            "public_key": self.public_key,
            "amount": amount_int,
            "currency": currency,
            "description": description,
            "email": email,
            "order_number": order_number,
            "metadata": metadata or {},
        }

    def charge(self, token_id: str, amount: int, currency: str,
               description: str, email: str, order_number: str,
               metadata: dict = None) -> dict:
        """
        Realiza un cobro usando un token de Culqi.

        POST /v2/charges
        """
        missing = self._is_configured()
        if missing:
            return {"success": False, "error": f"Culqi no configurado: {', '.join(missing)}"}

        payload = {
            "amount": amount,
            "currency_code": currency,
            "description": description,
            "email": email,
            "token_id": token_id,
            "metadata": {
                "order_number": order_number,
                **(metadata or {}),
            },
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.api_base}/v2/charges",
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.secret_key}",
                    "User-Agent": "AeternumBackend/2.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            if result.get("data", {}).get("id"):
                charge_data = result["data"]
                return {
                    "success": True,
                    "provider_order_id": str(charge_data.get("order_id", "")),
                    "provider_payment_id": str(charge_data.get("id", "")),
                    "provider_token": charge_data.get("id", ""),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("user_message", "Error al procesar cobro"),
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
                "error": f"Error HTTP {e.code} de Culqi",
                "details": body,
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"Error de conexión con Culqi: {e.reason}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error inesperado al cobrar: {str(e)}",
            }

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        """
        Verifica la firma del webhook de Culqi.

        Culqi usa HMAC-SHA256:
        - Header: Culqi-Signature
        - Input: body secreto
        """
        if not self.webhook_secret:
            return False

        signature = headers.get("culqi-signature", "")
        if not signature:
            return False

        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def parse_webhook_event(self, headers: dict, body: bytes) -> dict:
        """
        Parsea un evento de webhook de Culqi.

        Eventos relevantes:
        - charge.completed -> cobro exitoso
        - charge.failed -> cobro fallido
        - charge.created -> cobro creado
        """
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            return {"error": "JSON inválido"}

        event_type = data.get("type", "")
        entity = data.get("data", {})

        charge_id = str(entity.get("id", ""))
        order_number = ""
        metadata = entity.get("metadata", {})
        if metadata:
            order_number = metadata.get("order_number", "")

        # Mapear estado
        amount = Decimal(str(entity.get("amount", 0)))
        currency = entity.get("currency_code", "PEN")

        status = "pending"
        if event_type == "charge.completed":
            status = "approved"
        elif event_type == "charge.failed":
            status = "rejected"
        elif event_type == "charge.created":
            status = "pending"
        elif entity.get("outcome", {}).get("code") == "000":
            status = "approved"

        return {
            "provider_event_id": charge_id,
            "event_type": event_type,
            "order_number": order_number,
            "provider_order_id": str(entity.get("order_id", "")),
            "provider_payment_id": charge_id,
            "amount": amount,
            "currency": currency,
            "status": status,
            "raw": data,
        }


# ══════════════════════════════════════════════════════════════════════════════
# FACTORY / REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

# Instancias singleton
_paddle_provider = None
_culqi_provider = None


def get_paddle_provider() -> PaddleProvider:
    """Retorna la instancia singleton de PaddleProvider."""
    global _paddle_provider
    if _paddle_provider is None:
        _paddle_provider = PaddleProvider()
    return _paddle_provider


def get_culqi_provider() -> CulqiProvider:
    """Retorna la instancia singleton de CulqiProvider."""
    global _culqi_provider
    if _culqi_provider is None:
        _culqi_provider = CulqiProvider()
    return _culqi_provider


def get_provider_for_order(order_type: str) -> PaymentProvider:
    """
    Retorna el proveedor adecuado según el tipo de orden.

    - digital_purchase, digital_rental -> Paddle
    - physical_purchase -> Culqi
    """
    if order_type in ("digital_purchase", "digital_rental"):
        return get_paddle_provider()
    elif order_type == "physical_purchase":
        return get_culqi_provider()
    else:
        raise ValueError(f"Tipo de orden desconocido: {order_type}")


def get_provider_by_name(name: str) -> PaymentProvider:
    """Retorna un proveedor por su nombre."""
    providers = {
        "paddle": get_paddle_provider,
        "culqi": get_culqi_provider,
    }
    factory = providers.get(name)
    if factory is None:
        raise ValueError(f"Proveedor desconocido: {name}")
    return factory()


# ══════════════════════════════════════════════════════════════════════════════
# COMPATIBILIDAD: funciones que reemplazan flow_service
# ══════════════════════════════════════════════════════════════════════════════

# Re-exportar para compatibilidad con código existente
CURRENCY_CONFIG = PADDLE_CURRENCY_CONFIG
CURRENCY_SYMBOLS = {code: cfg["symbol"] for code, cfg in PADDLE_CURRENCY_CONFIG.items()}
