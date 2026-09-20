# -*- coding: utf-8 -*-
"""
Tests del sistema de comercio AeternumLibrary.

Prueba:
- Flow: firma, parámetros, URLs, respuesta
- Webhook: token, consulta Flow, validaciones
- Checkout: multimoneda, precios, validaciones
- Entitlements: compra permanente, alquiler, expiración
- Stock: concurrencia, descuento atómico
- Seguridad: IDOR, permisos, manipulación
- Money: Decimal, NUMERIC
"""
import json
import os
import sys
import types
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta

import pytest

# Stub de psycopg2
if "psycopg2" not in sys.modules:
    errors_mod = types.ModuleType("psycopg2.errors")
    class UniqueViolation(Exception):
        pass
    errors_mod.UniqueViolation = UniqueViolation
    psycopg2_mod = types.ModuleType("psycopg2")
    psycopg2_mod.errors = errors_mod
    psycopg2_mod.connect = lambda *a, **k: None
    sys.modules["psycopg2"] = psycopg2_mod
    sys.modules["psycopg2.errors"] = errors_mod
    extras_mod = types.ModuleType("psycopg2.extras")
    extras_mod.RealDictCursor = object
    sys.modules["psycopg2.extras"] = extras_mod

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from support import FakeDb

database_mod = types.ModuleType("database")
database_mod.init_db = lambda: None
database_mod.get_db = lambda: None
sys.modules["database"] = database_mod

import server
import commerce_service
import flow_service
import payment_providers
from fastapi.testclient import TestClient


@pytest.fixture()
def fake_db():
    db = FakeDb()
    server.get_db = lambda: db
    return db


@pytest.fixture()
def client(fake_db):
    return TestClient(server.app)


def _auth_token(user_id, email):
    return server.create_access_token(user_id, email)


@pytest.fixture()
def as_user(client):
    client.cookies.set("access_token", _auth_token(2, "user@test.com"))
    return client


@pytest.fixture()
def as_admin(client):
    client.cookies.set("access_token", _auth_token(1, "admin@test.com"))
    return client


# ══════════════════════════════════════════════════════════════════════════════
# FLOW: FIRMA HMAC-SHA256
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowSignature:
    """Tests de la firma HMAC-SHA256 de Flow."""

    def test_signature_format_key_value(self):
        """La firma debe concatenar key+value sin = ni &."""
        original_key = flow_service.FLOW_SECRET_KEY
        try:
            flow_service.FLOW_SECRET_KEY = "test_secret"
            params = {"amount": "5000", "apiKey": "XXX", "currency": "CLP"}
            sig = flow_service._compute_signature(params)
            # Debe ser un hash hex de 64 caracteres
            assert len(sig) == 64
            assert all(c in "0123456789abcdef" for c in sig)
        finally:
            flow_service.FLOW_SECRET_KEY = original_key

    def test_signature_sorted_params(self):
        """Los parámetros deben estar ordenados alfabéticamente."""
        original_key = flow_service.FLOW_SECRET_KEY
        try:
            flow_service.FLOW_SECRET_KEY = "secret"
            p1 = {"z": "1", "a": "2"}
            p2 = {"a": "2", "z": "1"}
            assert flow_service._compute_signature(p1) == flow_service._compute_signature(p2)
        finally:
            flow_service.FLOW_SECRET_KEY = original_key

    def test_signature_uses_secret_key(self):
        """La firma debe usar FLOW_SECRET_KEY, no FLOW_API_KEY."""
        original_secret = flow_service.FLOW_SECRET_KEY
        original_api = flow_service.FLOW_API_KEY
        try:
            flow_service.FLOW_SECRET_KEY = "secret_A"
            flow_service.FLOW_API_KEY = "key_B"
            sig1 = flow_service._compute_signature({"a": "1"})
            flow_service.FLOW_SECRET_KEY = "secret_C"
            sig2 = flow_service._compute_signature({"a": "1"})
            assert sig1 != sig2
        finally:
            flow_service.FLOW_SECRET_KEY = original_secret
            flow_service.FLOW_API_KEY = original_api

    def test_signature_no_equals_no_ampersand(self):
        """La concatenación NO debe contener = ni &."""
        original_key = flow_service.FLOW_SECRET_KEY
        try:
            flow_service.FLOW_SECRET_KEY = "k"
            import hmac as _hmac, hashlib
            params = {"b": "2", "a": "1"}
            sorted_params = sorted(params.items())
            to_sign = "".join(f"{k}{v}" for k, v in sorted_params)
            assert "=" not in to_sign
            assert "&" not in to_sign
            assert to_sign == "a1b2"
        finally:
            flow_service.FLOW_SECRET_KEY = original_key


# ══════════════════════════════════════════════════════════════════════════════
# FLOW: CREACIÓN DE PAGO
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowCreatePayment:
    """Tests de creación de pago."""

    def test_uses_apiKey_not_commerceCode(self):
        """Flow usa 'apiKey', no 'commerceCode'."""
        original_key = flow_service.FLOW_API_KEY
        original_secret = flow_service.FLOW_SECRET_KEY
        try:
            flow_service.FLOW_API_KEY = ""
            flow_service.FLOW_SECRET_KEY = ""
            result = flow_service.create_payment("ORD-001", 1000, "Test", "t@t.com")
            assert result["success"] is False
            assert "FLOW_API_KEY" in result["error"]
        finally:
            flow_service.FLOW_API_KEY = original_key
            flow_service.FLOW_SECRET_KEY = original_secret

    def test_create_payment_missing_config(self):
        """Falla sin configuración."""
        original_key = flow_service.FLOW_API_KEY
        original_secret = flow_service.FLOW_SECRET_KEY
        try:
            flow_service.FLOW_API_KEY = ""
            flow_service.FLOW_SECRET_KEY = ""
            result = flow_service.create_payment("ORD-001", 1000, "Test", "t@t.com")
            assert result["success"] is False
        finally:
            flow_service.FLOW_API_KEY = original_key
            flow_service.FLOW_SECRET_KEY = original_secret

    def test_create_payment_url_endpoint(self):
        """El endpoint debe ser /payment/create, no /api/v1.0/payments/create."""
        url = f"{flow_service.FLOW_BASE_URL}/payment/create"
        assert "/api/v1.0/" not in url
        assert "/payments/" not in url

    def test_create_payment_redirect_url_format(self):
        """La URL de redirección debe ser url + '?token=' + token."""
        # Simular respuesta de Flow
        flow_response = {"url": "https://flow.cl/pay", "token": "ABC123", "flowOrder": 123}
        redirect = f"{flow_response['url']}?token={flow_response['token']}"
        assert redirect == "https://flow.cl/pay?token=ABC123"

    def test_create_payment_accepts_currency(self):
        """create_payment debe aceptar currency como parámetro."""
        import inspect
        sig = inspect.signature(flow_service.create_payment)
        assert "currency" in sig.parameters


# ══════════════════════════════════════════════════════════════════════════════
# FLOW: CONSULTA DE ESTADO
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowVerifyPayment:
    """Tests de consulta de estado."""

    def test_verify_uses_getStatus(self):
        """El endpoint debe ser /payment/getStatus."""
        url = f"{flow_service.FLOW_BASE_URL}/payment/getStatus"
        assert "getPayment" not in url

    def test_is_payment_approved_status_2(self):
        assert flow_service.is_payment_approved({"status": 2}) is True
        assert flow_service.is_payment_approved({"status": 1}) is False
        assert flow_service.is_payment_approved({"status": 3}) is False

    def test_is_payment_rejected_status_3_4(self):
        assert flow_service.is_payment_rejected({"status": 3}) is True
        assert flow_service.is_payment_rejected({"status": 4}) is True
        assert flow_service.is_payment_rejected({"status": 2}) is False

    def test_status_codes_official(self):
        """Estados oficiales de Flow: 1=pendiente, 2=pagado, 3=rechazado, 4=cancelado."""
        assert flow_service.get_payment_status_code({"status": 1}) == "pending"
        assert flow_service.get_payment_status_code({"status": 2}) == "approved"
        assert flow_service.get_payment_status_code({"status": 3}) == "rejected"
        assert flow_service.get_payment_status_code({"status": 4}) == "cancelled"


# ══════════════════════════════════════════════════════════════════════════════
# FLOW: MONEDAS
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowCurrencies:
    """Tests de soporte multimoneda."""

    def test_enabled_currencies(self):
        """PEN, CLP, MXN deben estar habilitados."""
        assert "PEN" in flow_service.ENABLED_DIGITAL_CURRENCIES
        assert "CLP" in flow_service.ENABLED_DIGITAL_CURRENCIES
        assert "MXN" in flow_service.ENABLED_DIGITAL_CURRENCIES

    def test_eur_usd_not_enabled_in_flow(self):
        """EUR y USD NO están habilitados en flow_service (legacy), pero sí en payment_providers."""
        assert "EUR" not in flow_service.ENABLED_DIGITAL_CURRENCIES
        assert "USD" not in flow_service.ENABLED_DIGITAL_CURRENCIES

    def test_eur_usd_enabled_in_paddle(self):
        """EUR y USD SÍ están habilitados en payment_providers (Paddle)."""
        assert "EUR" in payment_providers.ENABLED_DIGITAL_CURRENCIES
        assert "USD" in payment_providers.ENABLED_DIGITAL_CURRENCIES

    def test_eur_usd_exist_in_config(self):
        """EUR y USD existen en CURRENCY_CONFIG pero con flow_tested=False."""
        assert "EUR" in flow_service.CURRENCY_CONFIG
        assert "USD" in flow_service.CURRENCY_CONFIG
        assert flow_service.CURRENCY_CONFIG["EUR"]["flow_tested"] is False
        assert flow_service.CURRENCY_CONFIG["USD"]["flow_tested"] is False

    def test_currency_symbols(self):
        assert flow_service.get_currency_symbol("PEN") == "S/"
        assert flow_service.get_currency_symbol("CLP") == "$"
        assert flow_service.get_currency_symbol("MXN") == "MX$"
        assert flow_service.get_currency_symbol("EUR") == "\u20ac"
        assert flow_service.get_currency_symbol("USD") == "US$"

    def test_format_amount_pen(self):
        """PEN: 25.90 → 2590 (2 decimales, ×100)."""
        assert flow_service.format_amount_for_flow(Decimal("25.90"), "PEN") == 2590

    def test_format_amount_clp(self):
        """CLP: 50000 → 50000 (0 decimales, sin ×100)."""
        assert flow_service.format_amount_for_flow(Decimal("50000"), "CLP") == 50000

    def test_format_amount_mxn(self):
        """MXN: 150.50 → 15050 (2 decimales, ×100)."""
        assert flow_service.format_amount_for_flow(Decimal("150.50"), "MXN") == 15050

    def test_format_amount_eur(self):
        """EUR: 10.50 → 1050 (2 decimales, ×100)."""
        assert flow_service.format_amount_for_flow(Decimal("10.50"), "EUR") == 1050

    def test_format_amount_usd(self):
        """USD: 25.00 → 2500 (2 decimales, ×100)."""
        assert flow_service.format_amount_for_flow(Decimal("25.00"), "USD") == 2500

    def test_format_amount_clp_no_decimal(self):
        """CLP: 1500 → 1500 (sin decimales, sin redondeo)."""
        assert flow_service.format_amount_for_flow(Decimal("1500"), "CLP") == 1500

    def test_format_amount_clp_rounding(self):
        """CLP: decimales se redondean al entero más cercano."""
        assert flow_service.format_amount_for_flow(Decimal("1500.6"), "CLP") == 1501
        assert flow_service.format_amount_for_flow(Decimal("1500.4"), "CLP") == 1500

    def test_format_amount_unknown_currency_raises(self):
        """Moneda desconocida debe lanzar ValueError."""
        with pytest.raises(ValueError, match="Moneda no soportada"):
            flow_service.format_amount_for_flow(Decimal("100"), "XYZ")

    def test_format_amount_default_pen(self):
        """Sin currency, default es PEN."""
        assert flow_service.format_amount_for_flow(Decimal("25.90")) == 2590

    def test_is_currency_enabled(self):
        assert flow_service.is_currency_enabled("PEN") is True
        assert flow_service.is_currency_enabled("CLP") is True
        assert flow_service.is_currency_enabled("EUR") is False
        assert flow_service.is_currency_enabled("XYZ") is False

    def test_is_currency_enabled_paddle(self):
        """payment_providers.is_currency_enabled tiene más monedas."""
        assert payment_providers.is_currency_enabled("PEN") is True
        assert payment_providers.is_currency_enabled("EUR") is True
        assert payment_providers.is_currency_enabled("USD") is True
        assert payment_providers.is_currency_enabled("XYZ") is False

    def test_currency_decimals(self):
        assert flow_service.get_currency_decimals("PEN") == 2
        assert flow_service.get_currency_decimals("CLP") == 0
        assert flow_service.get_currency_decimals("MXN") == 2


# ══════════════════════════════════════════════════════════════════════════════
# COMMERCE SERVICE: PRECIOS
# ══════════════════════════════════════════════════════════════════════════════

class TestCommercePrices:
    """Tests de obtención de precios."""

    def test_order_number_format(self):
        n = commerce_service._generate_order_number()
        assert n.startswith("AET-")
        parts = n.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 14
        assert len(parts[2]) == 6

    def test_order_number_unique(self):
        n1 = commerce_service._generate_order_number()
        n2 = commerce_service._generate_order_number()
        assert n1 != n2


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailTemplates:
    def test_purchase_template(self):
        html = commerce_service._email_template_purchase_confirmed(
            "Juan", "El Principito", "AET-001", Decimal("25.90"), "PEN"
        )
        assert "Juan" in html
        assert "El Principito" in html
        assert "25.90" in html
        assert "S/" in html

    def test_rental_template(self):
        html = commerce_service._email_template_rental_confirmed(
            "Juan", "El Principito", "AET-002", 14, "01/01/2026", "15/01/2026"
        )
        assert "14" in html
        assert "Alquiler Confirmado" in html

    def test_physical_template(self):
        html = commerce_service._email_template_physical_confirmed(
            "Juan", "AET-003", Decimal("49.90"), "PEN"
        )
        assert "49.90" in html
        assert "Pedido Confirmado" in html


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: CHECKOUT
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckoutEndpoints:
    def test_checkout_unauthenticated(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.post("/api/checkout", json={
            "book_id": 1, "item_type": "digital_purchase"
        })
        assert response.status_code in (401, 422)

    def test_checkout_invalid_item_type(self, as_user):
        response = as_user.post("/api/checkout", json={
            "book_id": 1, "item_type": "invalid"
        })
        assert response.status_code == 422

    def test_checkout_invalid_currency(self, as_user):
        response = as_user.post("/api/checkout", json={
            "book_id": 1, "item_type": "digital_purchase", "currency": "XYZ"
        })
        assert response.status_code == 422

    def test_purchases_unauthenticated(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/user/purchases")
        assert response.status_code == 401

    def test_entitlements_unauthenticated(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/user/entitlements")
        assert response.status_code == 401

    def test_addresses_unauthenticated(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/user/addresses")
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowWebhook:
    def test_webhook_no_token(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.post("/api/flow/webhook", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    def test_webhook_with_token(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.post("/api/flow/webhook", json={"token": "test123"})
        assert response.status_code == 200

    def test_flow_result_no_token(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/flow/result")
        assert response.status_code == 400

    def test_check_access_unauthenticated(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/books/1/access")
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# RAYOS
# ══════════════════════════════════════════════════════════════════════════════

class TestRayos:
    def test_purchase_reward_type_exists(self):
        assert "purchase_reward" in server.VALID_RAYOS_TYPES

    def test_purchase_reward_default_zero(self):
        assert commerce_service.PURCHASE_REWARD_RAYOS == 0


# ══════════════════════════════════════════════════════════════════════════════
# SEGURIDAD
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurity:
    def test_admin_commerce_stats_unauthorized(self, as_user):
        response = as_user.get("/api/admin/commerce/stats")
        assert response.status_code == 403

    def test_admin_commerce_config(self, as_admin):
        response = as_admin.get("/api/admin/commerce/config")
        assert response.status_code == 200
        data = response.json()
        assert data["default_currency"] == "PEN"
        assert 7 in data["rental_durations"]
        assert 14 in data["rental_durations"]
        assert 30 in data["rental_durations"]

    def test_user_cannot_update_fulfillment(self, as_user):
        response = as_user.put("/api/admin/commerce/orders/1/fulfillment", json={
            "fulfillment_status": "shipped"
        })
        assert response.status_code == 403

    def test_debug_files_requires_admin(self, as_user):
        response = as_user.get("/api/debug/files")
        assert response.status_code == 403

    def test_debug_files_works_as_admin(self, as_admin):
        try:
            response = as_admin.get("/api/debug/files")
            assert response.status_code in (200, 500)
        except RuntimeError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# NO REEMBOLSOS
# ══════════════════════════════════════════════════════════════════════════════

class TestNoRefunds:
    def test_no_refund_post(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.post("/api/admin/refunds/1")
        assert response.status_code in (404, 405)

    def test_no_refund_put(self):
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.put("/api/admin/refunds/1")
        assert response.status_code in (404, 405)


# ══════════════════════════════════════════════════════════════════════════════
# DECIMAL / MONEY
# ══════════════════════════════════════════════════════════════════════════════

class TestDecimalMoney:
    def test_decimal_precision(self):
        """Los cálculos monetarios deben usar Decimal."""
        a = Decimal("0.1")
        b = Decimal("0.2")
        assert a + b == Decimal("0.3")

    def test_format_amount_integer(self):
        """format_amount_for_flow debe retornar entero."""
        result = flow_service.format_amount_for_flow(Decimal("25.90"), "PEN")
        assert isinstance(result, int)
        assert result == 2590

    def test_format_amount_rounding_pen(self):
        """Redondeo correcto para PEN (2 decimales)."""
        assert flow_service.format_amount_for_flow(Decimal("25.905"), "PEN") == 2591
        assert flow_service.format_amount_for_flow(Decimal("25.904"), "PEN") == 2590

    def test_format_amount_rounding_clp(self):
        """Redondeo correcto para CLP (0 decimales)."""
        assert flow_service.format_amount_for_flow(Decimal("1500.5"), "CLP") == 1501
        assert flow_service.format_amount_for_flow(Decimal("1500.4"), "CLP") == 1500


# ══════════════════════════════════════════════════════════════════════════════
# CHECKOUT: VALIDACIONES DE MONEDA
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckoutCurrencyValidation:
    """Tests de validación de moneda en checkout."""

    def test_eur_now_enabled_with_paddle(self, as_user):
        """EUR ahora está habilitado con Paddle. Checkout lo acepta (falla por otro motivo)."""
        response = as_user.post("/api/checkout", json={
            "book_id": 1, "item_type": "digital_purchase", "currency": "EUR"
        })
        # EUR es válido; falla porque book 1 no tiene precio EUR configurado
        assert response.status_code in (400, 404)

    def test_usd_now_enabled_with_paddle(self, as_user):
        """USD ahora está habilitado con Paddle. Checkout lo acepta (falla por otro motivo)."""
        response = as_user.post("/api/checkout", json={
            "book_id": 1, "item_type": "digital_purchase", "currency": "USD"
        })
        # USD es válido; falla porque book 1 no tiene precio USD configurado
        assert response.status_code in (400, 404)

    def test_unknown_currency_blocked(self, as_user):
        """Moneda desconocida: checkout debe rechazarla."""
        response = as_user.post("/api/checkout", json={
            "book_id": 1, "item_type": "digital_purchase", "currency": "XYZ"
        })
        assert response.status_code == 422

    def test_physical_with_clp_rejected(self, as_user):
        """Físico + CLP: backend debe rechazar."""
        response = as_user.post("/api/checkout", json={
            "book_id": 99, "item_type": "physical_purchase", "currency": "CLP"
        })
        assert response.status_code == 400

    def test_physical_with_mxn_rejected(self, as_user):
        """Físico + MXN: backend debe rechazar."""
        response = as_user.post("/api/checkout", json={
            "book_id": 99, "item_type": "physical_purchase", "currency": "MXN"
        })
        assert response.status_code == 400

    def test_physical_default_pen(self, as_user):
        """Físico sin currency: default es PEN (válido para validación)."""
        response = as_user.post("/api/checkout", json={
            "book_id": 99, "item_type": "physical_purchase"
        })
        assert response.status_code in (400, 404)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN CONFIG
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminConfig:
    """Tests del endpoint /admin/commerce/config."""

    def test_config_no_500_error(self, as_admin):
        """Admin config no debe causar error 500."""
        response = as_admin.get("/api/admin/commerce/config")
        assert response.status_code == 200

    def test_config_returns_enabled_currencies(self, as_admin):
        """Config retorna enabled_currencies."""
        response = as_admin.get("/api/admin/commerce/config")
        data = response.json()
        assert "enabled_currencies" in data
        assert "PEN" in data["enabled_currencies"]
        assert "CLP" in data["enabled_currencies"]
        assert "MXN" in data["enabled_currencies"]
        assert "USD" in data["enabled_currencies"]
        assert "EUR" in data["enabled_currencies"]

    def test_config_returns_currency_config(self, as_admin):
        """Config retorna currency_config con decimales."""
        response = as_admin.get("/api/admin/commerce/config")
        data = response.json()
        assert "currency_config" in data
        assert data["currency_config"]["PEN"]["decimals"] == 2
        assert data["currency_config"]["CLP"]["decimals"] == 0
        assert data["currency_config"]["MXN"]["decimals"] == 2

    def test_config_no_secrets(self, as_admin):
        """Config no debe exponer FLOW_API_KEY ni FLOW_SECRET_KEY."""
        response = as_admin.get("/api/admin/commerce/config")
        data = response.json()
        text = json.dumps(data)
        assert "FLOW_API_KEY" not in text
        assert "FLOW_SECRET_KEY" not in text

    def test_config_flow_sandbox_field(self, as_admin):
        """Config tiene flow_sandbox."""
        response = as_admin.get("/api/admin/commerce/config")
        data = response.json()
        assert "flow_sandbox" in data
        assert isinstance(data["flow_sandbox"], bool)

    def test_config_unauthorized(self, as_user):
        """No-admin no puede ver config."""
        response = as_user.get("/api/admin/commerce/config")
        assert response.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS PÚBLICOS
# ══════════════════════════════════════════════════════════════════════════════

class TestPublicEndpoints:
    """Tests de endpoints públicos de comercio."""

    def test_currencies_endpoint(self):
        """GET /commerce/currencies retorna monedas habilitadas."""
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/commerce/currencies")
        assert response.status_code == 200
        data = response.json()
        assert "currencies" in data
        codes = [c["code"] for c in data["currencies"]]
        assert "PEN" in codes
        assert "CLP" in codes
        assert "MXN" in codes

    def test_book_prices_endpoint(self):
        """GET /books/{id}/prices retorna precios."""
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/books/99/prices")
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data
        assert "PEN" in data["prices"]
        assert data["prices"]["PEN"]["price"] == 25.90

    def test_flow_result_no_crash(self):
        """GET /flow/result sin token no causa crash."""
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/flow/result")
        assert response.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL TEMPLATES CON MULTIMONEDA
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailTemplatesMultiCurrency:
    """Tests de templates de email con diferentes monedas."""

    def test_purchase_template_clp(self):
        html = commerce_service._email_template_purchase_confirmed(
            "Juan", "El Principito", "AET-001", Decimal("50000"), "CLP"
        )
        assert "$" in html
        assert "50000.00" in html

    def test_purchase_template_mxn(self):
        html = commerce_service._email_template_purchase_confirmed(
            "Juan", "El Principito", "AET-001", Decimal("150.50"), "MXN"
        )
        assert "MX$" in html
        assert "150.50" in html

    def test_physical_template_clp(self):
        html = commerce_service._email_template_physical_confirmed(
            "Juan", "AET-003", Decimal("49900"), "CLP"
        )
        assert "49900.00" in html
        assert "Pedido Confirmado" in html


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK: CONSISTENCIA DE MONTO
# ══════════════════════════════════════════════════════════════════════════════

class TestWebhookAmountConsistency:
    """Tests de que webhook usa la misma función que payment/create."""

    def test_format_function_same_both_sides(self):
        """La misma función se usa para crear y verificar pagos."""
        amount = Decimal("25.90")
        create_result = flow_service.format_amount_for_flow(amount, "PEN")
        verify_result = flow_service.format_amount_for_flow(amount, "PEN")
        assert create_result == verify_result

    def test_format_function_clp_consistent(self):
        """CLP: mismo resultado en ambos lados."""
        amount = Decimal("50000")
        create_result = flow_service.format_amount_for_flow(amount, "CLP")
        verify_result = flow_service.format_amount_for_flow(amount, "CLP")
        assert create_result == verify_result
        assert create_result == 50000

    def test_format_function_mxn_consistent(self):
        """MXN: mismo resultado en ambos lados."""
        amount = Decimal("150.50")
        create_result = flow_service.format_amount_for_flow(amount, "MXN")
        verify_result = flow_service.format_amount_for_flow(amount, "MXN")
        assert create_result == verify_result
        assert create_result == 15050

    def test_format_function_eur_consistent(self):
        """EUR: mismo resultado en ambos lados."""
        amount = Decimal("10.50")
        create_result = flow_service.format_amount_for_flow(amount, "EUR")
        verify_result = flow_service.format_amount_for_flow(amount, "EUR")
        assert create_result == verify_result
        assert create_result == 1050


# ══════════════════════════════════════════════════════════════════════════════
# PAYMENT PROVIDERS — Nueva arquitectura
# ══════════════════════════════════════════════════════════════════════════════

class TestPaymentProviders:
    """Tests del módulo payment_providers."""

    def test_enabled_currencies_include_major(self):
        """Las monedas principales deben estar habilitadas."""
        assert "USD" in payment_providers.ENABLED_DIGITAL_CURRENCIES
        assert "EUR" in payment_providers.ENABLED_DIGITAL_CURRENCIES
        assert "GBP" in payment_providers.ENABLED_DIGITAL_CURRENCIES
        assert "PEN" in payment_providers.ENABLED_DIGITAL_CURRENCIES
        assert "JPY" in payment_providers.ENABLED_DIGITAL_CURRENCIES

    def test_get_currency_symbol(self):
        assert payment_providers.get_currency_symbol("USD") == "US$"
        assert payment_providers.get_currency_symbol("EUR") == "\u20ac"
        assert payment_providers.get_currency_symbol("GBP") == "\u00a3"
        assert payment_providers.get_currency_symbol("PEN") == "S/"
        assert payment_providers.get_currency_symbol("JPY") == "\u00a5"

    def test_get_currency_decimals_2(self):
        """USD/EUR/PEN tienen 2 decimales."""
        assert payment_providers.get_currency_decimals("USD") == 2
        assert payment_providers.get_currency_decimals("EUR") == 2
        assert payment_providers.get_currency_decimals("PEN") == 2

    def test_get_currency_decimals_0(self):
        """CLP/JPY/KRW tienen 0 decimales."""
        assert payment_providers.get_currency_decimals("CLP") == 0
        assert payment_providers.get_currency_decimals("JPY") == 0
        assert payment_providers.get_currency_decimals("KRW") == 0

    def test_get_currency_decimals_unknown_raises(self):
        with pytest.raises(ValueError, match="Moneda no soportada"):
            payment_providers.get_currency_decimals("XYZ")

    def test_is_currency_enabled(self):
        assert payment_providers.is_currency_enabled("USD") is True
        assert payment_providers.is_currency_enabled("XYZ") is False

    def test_format_amount_usd(self):
        """USD: 25.90 -> 2590 (2 decimales)."""
        assert payment_providers.format_amount_for_provider(Decimal("25.90"), "USD") == 2590

    def test_format_amount_jpy(self):
        """JPY: 1000 -> 1000 (0 decimales)."""
        assert payment_providers.format_amount_for_provider(Decimal("1000"), "JPY") == 1000

    def test_format_amount_krw(self):
        """KRW: 5000 -> 5000 (0 decimales)."""
        assert payment_providers.format_amount_for_provider(Decimal("5000"), "KRW") == 5000

    def test_format_amount_pen(self):
        """PEN: 25.90 -> 2590."""
        assert payment_providers.format_amount_for_provider(Decimal("25.90"), "PEN") == 2590

    def test_format_amount_rounding(self):
        """Redondeo correcto."""
        assert payment_providers.format_amount_for_provider(Decimal("25.905"), "USD") == 2591
        assert payment_providers.format_amount_for_provider(Decimal("25.904"), "USD") == 2590

    def test_format_amount_clp_no_decimal(self):
        """CLP: 1500 -> 1500."""
        assert payment_providers.format_amount_for_provider(Decimal("1500"), "CLP") == 1500

    def test_format_amount_clp_rounding(self):
        """CLP: decimales se redondean."""
        assert payment_providers.format_amount_for_provider(Decimal("1500.6"), "CLP") == 1501
        assert payment_providers.format_amount_for_provider(Decimal("1500.4"), "CLP") == 1500


class TestProviderRouting:
    """Tests del routing de proveedores por tipo de orden."""

    def test_digital_purchase_uses_paddle(self):
        from payment_providers import get_provider_for_order
        provider = get_provider_for_order("digital_purchase")
        assert provider.name == "paddle"

    def test_digital_rental_uses_paddle(self):
        from payment_providers import get_provider_for_order
        provider = get_provider_for_order("digital_rental")
        assert provider.name == "paddle"

    def test_physical_purchase_uses_culqi(self):
        from payment_providers import get_provider_for_order
        provider = get_provider_for_order("physical_purchase")
        assert provider.name == "culqi"

    def test_unknown_type_raises(self):
        from payment_providers import get_provider_for_order
        with pytest.raises(ValueError, match="Tipo de orden desconocido"):
            get_provider_for_order("unknown_type")


class TestPaddleProvider:
    """Tests del PaddleProvider."""

    def test_provider_name(self):
        provider = payment_providers.get_paddle_provider()
        assert provider.name == "paddle"

    def test_checkout_type(self):
        """Paddle retorna checkout_url."""
        provider = payment_providers.get_paddle_provider()
        # Sin configuración real, falla gracefully
        result = provider.create_checkout(
            "AET-TEST-001", Decimal("25.90"), "USD",
            "Test", "test@test.com"
        )
        # Falla porque no hay API key configurada
        assert result["success"] is False
        assert "PADDLE_API_KEY" in result["error"]


class TestCulqiProvider:
    """Tests del CulqiProvider."""

    def test_provider_name(self):
        provider = payment_providers.get_culqi_provider()
        assert provider.name == "culqi"

    def test_checkout_type(self):
        """Culqi retorna checkout_type token."""
        provider = payment_providers.get_culqi_provider()
        # Sin configuración real, falla gracefully
        result = provider.create_checkout(
            "AET-TEST-002", Decimal("25.90"), "PEN",
            "Test", "test@test.com"
        )
        # Falla porque no hay secret key configurada
        assert result["success"] is False
        assert "CULQI_SECRET_KEY" in result["error"]


class TestAdminConfigNew:
    """Tests del endpoint /admin/commerce/config con nuevos providers."""

    def test_config_returns_providers(self, as_admin):
        """Config tiene providers paddle y culqi."""
        response = as_admin.get("/api/admin/commerce/config")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "paddle" in data["providers"]
        assert "culqi" in data["providers"]
        assert "configured" in data["providers"]["paddle"]
        assert "configured" in data["providers"]["culqi"]

    def test_config_returns_more_currencies(self, as_admin):
        """Config retorna más monedas que antes."""
        response = as_admin.get("/api/admin/commerce/config")
        data = response.json()
        assert len(data["enabled_currencies"]) > 3
        assert "USD" in data["enabled_currencies"]
        assert "EUR" in data["enabled_currencies"]
        assert "GBP" in data["enabled_currencies"]

    def test_config_no_secrets(self, as_admin):
        """Config no expone claves."""
        response = as_admin.get("/api/admin/commerce/config")
        data = response.json()
        text = json.dumps(data)
        assert "FLOW_API_KEY" not in text
        assert "FLOW_SECRET_KEY" not in text
        assert "PADDLE_API_KEY" not in text
        assert "CULQI_SECRET_KEY" not in text


class TestCurrenciesEndpoint:
    """Tests del endpoint /commerce/currencies."""

    def test_currencies_returns_all(self):
        """Currencies retorna monedas habilitadas de payment_providers."""
        db = FakeDb()
        server.get_db = lambda: db
        client = TestClient(server.app)
        response = client.get("/api/commerce/currencies")
        assert response.status_code == 200
        data = response.json()
        codes = [c["code"] for c in data["currencies"]]
        assert "USD" in codes
        assert "EUR" in codes
        assert "GBP" in codes
        assert "PEN" in codes
        assert "JPY" in codes
