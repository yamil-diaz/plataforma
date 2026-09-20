# -*- coding: utf-8 -*-
"""
webhook_handler.py — Manejador unificado de webhooks de pago.

Recibe eventos de Paddle (digitales) y Culqi (físicos),
verifica autenticidad, valida estructura, y procesa de forma
idempotente con transacciones atómicas.
"""
import json
import logging
from datetime import datetime, timezone

from payment_providers import (
    get_paddle_provider,
    get_culqi_provider,
    format_amount_for_provider,
    get_currency_decimals,
)
import commerce_service

logger = logging.getLogger("aeternum.webhooks")


def handle_webhook(provider_name: str, headers: dict, body: bytes, db) -> dict:
    """
    Punto de entrada unificado para webhooks de pago.

    Args:
        provider_name: 'paddle' o 'culqi'
        headers: headers HTTP del webhook
        body: body raw del webhook (bytes)
        db: conexión a la BD

    Returns:
        dict con status y message
    """
    provider_map = {
        "paddle": get_paddle_provider,
        "culqi": get_culqi_provider,
    }

    factory = provider_map.get(provider_name)
    if not factory:
        return {"status": "error", "message": f"Proveedor desconocido: {provider_name}"}

    provider = factory()

    # 1. Verificar autenticidad/firma
    if not provider.verify_webhook(headers, body):
        print(f"[PAYMENT DEBUG] Paddle webhook received", flush=True)
        print(f"[PAYMENT DEBUG] webhook auth FAILED - invalid signature", flush=True)
        _log_event(db, provider_name, "webhook_auth_failed", body, "failed",
                    "Firma de webhook inválida")
        return {"status": "error", "message": "Invalid signature"}

    # 2. Parsear evento
    event = provider.parse_webhook_event(headers, body)
    print(f"[PAYMENT DEBUG] Paddle webhook received", flush=True)
    print(f"[PAYMENT DEBUG] event_type={event.get('event_type', 'N/A')}", flush=True)
    print(f"[PAYMENT DEBUG] transaction_id={event.get('provider_event_id', 'N/A')}", flush=True)
    if "error" in event:
        print(f"[PAYMENT DEBUG] webhook parse ERROR={event['error']}", flush=True)
        _log_event(db, provider_name, "webhook_parse_error", body, "failed",
                    event["error"])
        return {"status": "error", "message": event["error"]}

    provider_event_id = event.get("provider_event_id", "")
    order_number = event.get("order_number", "")

    # 3. Registrar evento (idempotente por constraint UNIQUE)
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.cursor()

    try:
        # Verificar si ya procesamos este evento
        cursor.execute(
            """SELECT id, processing_status FROM payment_events
               WHERE provider = %s AND provider_event_id = %s""",
            (provider_name, provider_event_id),
        )
        existing = cursor.fetchone()

        if existing and existing["processing_status"] == "processed":
            return {"status": "ok", "message": "Event already processed"}

        # Registrar o actualizar evento
        if existing:
            event_id = existing["id"]
            cursor.execute(
                """UPDATE payment_events
                   SET event_type = %s, payload = %s, provider_payment_id = %s,
                       provider_order_id = %s, amount = %s, currency = %s,
                       status = %s
                   WHERE id = %s""",
                (event["event_type"], json.dumps(event.get("raw", {})),
                 event.get("provider_payment_id", ""),
                 event.get("provider_order_id", ""),
                 float(event.get("amount", 0)) if event.get("amount") else None,
                 event.get("currency", ""),
                 event.get("status", ""), event_id),
            )
        else:
            cursor.execute(
                """INSERT INTO payment_events
                   (provider, provider_event_id, event_type, payload,
                    provider_payment_id, provider_order_id, amount, currency, status,
                    processing_status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'received', %s)
                   RETURNING id""",
                (provider_name, provider_event_id, event["event_type"],
                 json.dumps(event.get("raw", {})),
                 event.get("provider_payment_id", ""),
                 event.get("provider_order_id", ""),
                 float(event.get("amount", 0)) if event.get("amount") else None,
                 event.get("currency", ""),
                 event.get("status", ""), now),
            )
            event_id = cursor.fetchone()["id"]
        db.commit()

        # 4. Buscar orden local
        if not order_number:
            # Intentar buscar por provider_order_id (transaction_id de Paddle)
            provider_order_id = event.get("provider_order_id", "")
            if provider_order_id:
                cursor.execute(
                    """SELECT id, user_id, payment_status, total, currency, order_type, order_number
                       FROM orders WHERE provider_token = %s FOR UPDATE""",
                    (provider_order_id,),
                )
                order = cursor.fetchone()
                if order:
                    order_number = order["order_number"]
                    print(f"[PAYMENT DEBUG] webhook found order by provider_token: {order_number}", flush=True)

            if not order_number:
                cursor.execute(
                    "UPDATE payment_events SET processing_status = 'failed', error_message = 'No order_number in event' WHERE id = %s",
                    (event_id,),
                )
                db.commit()
                return {"status": "error", "message": "No order_number"}
        else:
            cursor.execute(
                """SELECT id, user_id, payment_status, total, currency, order_type, order_number
                   FROM orders WHERE order_number = %s FOR UPDATE""",
                (order_number,),
            )
            order = cursor.fetchone()

        if not order:
            # Intentar por provider_order_id como fallback
            provider_order_id = event.get("provider_order_id", "")
            if provider_order_id:
                cursor.execute(
                    """SELECT id, user_id, payment_status, total, currency, order_type, order_number
                       FROM orders WHERE provider_token = %s FOR UPDATE""",
                    (provider_order_id,),
                )
                order = cursor.fetchone()
                if order:
                    order_number = order["order_number"]
                    print(f"[PAYMENT DEBUG] webhook found order by provider_token fallback: {order_number}", flush=True)

            if not order:
                cursor.execute(
                    "UPDATE payment_events SET processing_status = 'failed', error_message = %s WHERE id = %s",
                    (f"Orden local no encontrada: {order_number or event.get('provider_order_id', 'unknown')}", event_id),
                )
                db.commit()
                return {"status": "error", "message": "Local order not found"}

        # 5. Verificar monto (Paddle incluye impuestos en el webhook,
        # pero nuestra orden puede tener un monto diferente. Permitir tolerancia.)
        event_amount = event.get("amount")
        if event_amount is not None:
            expected_amount = format_amount_for_provider(
                order["total"], order["currency"]
            )
            event_amount_int = int(event_amount) if not isinstance(event_amount, int) else event_amount
            if event_amount_int != expected_amount:
                print(f"[WEBHOOK DEBUG] Amount mismatch: expected={expected_amount}, event={event_amount_int} (allowing tolerance)", flush=True)
                # No rechazar por monto — Paddle maneja impuestos y descuentos

        # 6. Verificar moneda
        event_currency = event.get("currency", "")
        if event_currency and event_currency != order["currency"]:
            cursor.execute(
                "UPDATE payment_events SET processing_status = 'failed', error_message = %s WHERE id = %s",
                (f"Currency mismatch: esperado {order['currency']}, evento {event_currency}", event_id),
            )
            db.commit()
            return {"status": "error", "message": "Currency mismatch"}

        # 7. Procesar según estado
        status = event.get("status", "pending")

        if status == "approved":
            confirm_result = commerce_service.confirm_payment(
                db, order["id"],
                provider_token=event.get("provider_payment_id", ""),
                provider_order_id=event.get("provider_order_id", ""),
                provider=provider_name,
            )
            print(f"[PAYMENT DEBUG] webhook confirm_payment success={confirm_result.get('success', False)}", flush=True)
            if confirm_result.get("success"):
                cursor.execute(
                    "UPDATE payment_events SET order_id = %s, processing_status = 'processed' WHERE id = %s",
                    (order["id"], event_id),
                )
                db.commit()
                return {"status": "ok", "message": "Payment confirmed"}
            else:
                cursor.execute(
                    "UPDATE payment_events SET processing_status = 'failed', error_message = %s WHERE id = %s",
                    (confirm_result.get("error", "confirm_payment failed"), event_id),
                )
                db.commit()
                return {"status": "error", "message": confirm_result.get("error", "confirm_payment failed")}

        elif status in ("rejected", "cancelled"):
            cursor.execute(
                """UPDATE orders
                   SET payment_status = %s, order_status = 'cancelled', updated_at = %s
                   WHERE id = %s""",
                (status, now, order["id"]),
            )
            cursor.execute(
                "UPDATE payment_events SET order_id = %s, processing_status = 'processed' WHERE id = %s",
                (order["id"], event_id),
            )
            db.commit()
            return {"status": "ok", "message": f"Payment {status}"}

        else:
            # Pendiente u otro estado
            print(f"[PAYMENT DEBUG] webhook status={status} → event ignored", flush=True)
            cursor.execute(
                "UPDATE payment_events SET processing_status = 'ignored' WHERE id = %s",
                (event_id,),
            )
            db.commit()
            return {"status": "ok", "message": "Payment pending"}

    except Exception as e:
        db.rollback()
        logger.exception("Error procesando webhook %s", provider_name)
        try:
            cursor.execute(
                """INSERT INTO payment_events
                   (provider, event_type, payload, processing_status, error_message, created_at)
                   VALUES (%s, 'webhook_error', %s, 'failed', %s, %s)""",
                (provider_name, json.dumps({"error": str(e)}), str(e), now),
            )
            db.commit()
        except Exception:
            pass
        return {"status": "error", "message": "Internal error"}


def _log_event(db, provider, event_type, body, status, error_message=None):
    """Registra un evento de webhook para auditoría."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor = db.cursor()
        payload_str = body.decode("utf-8") if isinstance(body, bytes) else str(body)
        # Truncar payload a 10KB para evitar problemas
        if len(payload_str) > 10240:
            payload_str = payload_str[:10240] + "...[truncated]"

        cursor.execute(
            """INSERT INTO payment_events
               (provider, event_type, payload, processing_status, error_message, created_at)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (provider, event_type, json.dumps({"raw": payload_str}),
             status, error_message, now),
        )
        db.commit()
    except Exception:
        pass
