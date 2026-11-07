# -*- coding: utf-8 -*-
"""
commerce_seller_service.py — Extensión de commerce_service.py para Seller Platform (FASE 2).

Funciones para:
- Calcular y registrar comisiones de vendedores
- Gestionar balances y payouts
- Dashboard y estadísticas de vendedor
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import json

logger = logging.getLogger("aeternum.commerce")


def calculate_commissions(cursor, order_id: int, order: dict) -> str:
    """Calcula y registra comisiones de vendedores. Idempotente."""
    now = datetime.now(timezone.utc).isoformat()

    # Verificar si ya fue procesado
    cursor.execute(
        "SELECT id FROM order_effects WHERE order_id = %s AND effect_type = 'commissions_calculated'",
        (order_id,),
    )
    if cursor.fetchone():
        logger.debug(f"Commissions already calculated for order {order_id}")
        return "already_applied"

    # Obtener items de la orden con vendedor
    cursor.execute(
        """SELECT oi.id, oi.book_id, oi.unit_price, oi.quantity, b.seller_id, COALESCE(b.commission_percentage, 30.0) as commission_percentage
           FROM order_items oi
           LEFT JOIN books b ON oi.book_id = b.id
           WHERE oi.order_id = %s""",
        (order_id,),
    )
    items = cursor.fetchall()

    commission_ids = []
    total_commissions = Decimal("0")

    for item in items:
        seller_id = item.get("seller_id")
        if not seller_id:
            logger.debug(f"Book {item.get('book_id')} has no seller assigned — skipping commission")
            continue  # Libros sin vendedor asignado (admin)

        commission_pct = Decimal(str(item.get("commission_percentage", 30)))
        unit_price = Decimal(str(item["unit_price"]))
        qty = item.get("quantity", 1)
        item_total = unit_price * qty
        commission_amount = (item_total * commission_pct / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        try:
            cursor.execute(
                """INSERT INTO seller_commissions
                   (order_id, seller_id, book_id, commission_percentage, order_total,
                    commission_amount, currency, status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                   RETURNING id""",
                (order_id, seller_id, item["book_id"], float(commission_pct),
                 float(item_total), float(commission_amount), order.get("currency", "PEN"), now),
            )
            comm_id = cursor.fetchone()["id"]
            commission_ids.append(str(comm_id))
            total_commissions += commission_amount

            # Actualizar balance del vendedor (INSERT or UPDATE)
            cursor.execute(
                """INSERT INTO seller_balances (seller_id, currency, total_earned, pending_amount, updated_at)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (seller_id, currency) DO UPDATE
                   SET total_earned = total_earned + %s,
                       pending_amount = pending_amount + %s,
                       updated_at = %s""",
                (seller_id, order.get("currency", "PEN"), float(commission_amount),
                 float(commission_amount), now,
                 float(commission_amount), float(commission_amount), now),
            )
            logger.info(f"Commission {comm_id} calculated for seller {seller_id}: {commission_amount}")

        except Exception as e:
            logger.error(f"Error calculating commission for book {item['book_id']}: {e}")
            continue

    # Registrar efecto
    try:
        cursor.execute(
            """INSERT INTO order_effects
               (order_id, effect_type, created_at, metadata)
               VALUES (%s, 'commissions_calculated', %s, %s)""",
            (order_id, now, json.dumps({"commission_ids": commission_ids, "total": float(total_commissions)})),
        )
        logger.info(f"Order {order_id}: {len(commission_ids)} commissions calculated (total: {total_commissions})")
    except Exception as e:
        logger.error(f"Error registering commission effect for order {order_id}: {e}")

    return "applied"


def get_seller_dashboard(cursor, seller_id: int) -> dict:
    """Obtiene estadísticas de vendedor."""
    try:
        # Estadísticas
        cursor.execute(
            """SELECT 
               COUNT(DISTINCT sc.order_id) as total_orders,
               COUNT(*) as total_commissions,
               COALESCE(SUM(sc.commission_amount), 0) as total_earned,
               COALESCE(SUM(CASE WHEN sc.status = 'pending' THEN sc.commission_amount ELSE 0 END), 0) as pending,
               COALESCE(SUM(CASE WHEN sc.status = 'paid' THEN sc.commission_amount ELSE 0 END), 0) as paid,
               sb.currency
               FROM seller_commissions sc
               LEFT JOIN seller_balances sb ON sc.seller_id = sb.seller_id
               WHERE sc.seller_id = %s
               GROUP BY sb.currency""",
            (seller_id,),
        )
        stats = cursor.fetchone() or {}

        # Comisiones recientes
        cursor.execute(
            """SELECT sc.id, sc.order_id, sc.book_id, sc.commission_amount, sc.currency, sc.status, sc.created_at,
               b.title as book_title, o.order_number
               FROM seller_commissions sc
               LEFT JOIN books b ON sc.book_id = b.id
               LEFT JOIN orders o ON sc.order_id = o.id
               WHERE sc.seller_id = %s
               ORDER BY sc.created_at DESC
               LIMIT 20""",
            (seller_id,),
        )
        commissions = cursor.fetchall()

        return {
            "success": True,
            "stats": {
                "total_orders": stats.get("total_orders", 0),
                "total_commissions": stats.get("total_commissions", 0),
                "total_earned": float(stats.get("total_earned", 0)),
                "pending": float(stats.get("pending", 0)),
                "paid": float(stats.get("paid", 0)),
                "currency": stats.get("currency", "PEN"),
            },
            "commissions": commissions,
        }
    except Exception as e:
        logger.error(f"Error getting seller dashboard for seller {seller_id}: {e}")
        return {"success": False, "error": str(e)}


def create_payout_request(cursor, seller_id: int, amount: Decimal, currency: str = "PEN", 
                         payment_method: str = "bank_transfer") -> dict:
    """Crea solicitud de payout."""
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        # Verificar saldo disponible
        cursor.execute(
            """SELECT pending_amount FROM seller_balances 
               WHERE seller_id = %s AND currency = %s""",
            (seller_id, currency),
        )
        balance = cursor.fetchone()
        if not balance or Decimal(str(balance["pending_amount"])) < amount:
            return {"success": False, "error": "Insufficient balance"}

        # Generar número de payout
        import random
        import string
        payout_number = f"PAYOUT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"

        # Crear payout
        cursor.execute(
            """INSERT INTO seller_payouts
               (seller_id, payout_number, amount, currency, status, payment_method, created_at)
               VALUES (%s, %s, %s, %s, 'pending', %s, %s)
               RETURNING id""",
            (seller_id, payout_number, float(amount), currency, payment_method, now),
        )
        payout_id = cursor.fetchone()["id"]

        # Reducir saldo pendiente
        cursor.execute(
            """UPDATE seller_balances
               SET pending_amount = pending_amount - %s, updated_at = %s
               WHERE seller_id = %s AND currency = %s""",
            (float(amount), now, seller_id, currency),
        )

        logger.info(f"Payout request {payout_number} created for seller {seller_id}: {amount} {currency}")

        return {
            "success": True,
            "payout_id": payout_id,
            "payout_number": payout_number,
            "amount": float(amount),
            "currency": currency,
            "status": "pending",
        }
    except Exception as e:
        logger.error(f"Error creating payout request: {e}")
        return {"success": False, "error": str(e)}


def get_seller_payouts(cursor, seller_id: int) -> dict:
    """Obtiene historial de payouts del vendedor."""
    try:
        cursor.execute(
            """SELECT id, payout_number, amount, currency, status, payment_method, created_at, completed_at
               FROM seller_payouts
               WHERE seller_id = %s
               ORDER BY created_at DESC""",
            (seller_id,),
        )
        payouts = cursor.fetchall()
        return {"success": True, "payouts": payouts}
    except Exception as e:
        logger.error(f"Error getting seller payouts: {e}")
        return {"success": False, "error": str(e)}
