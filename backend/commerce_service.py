# -*- coding: utf-8 -*-
"""
commerce_service.py — Lógica de negocio del comercio AeternumLibrary.

Funciones para:
- Crear órdenes
- Procesar pagos confirmados
- Gestionar entitlements (acceso digital)
- Gestionar stock físico
- Generar efectos secundarios (Rayos, notificaciones, emails)
- Verificar acceso a libros
- Consultar precios por moneda
"""
import random
import string
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta

# ── Configuración de Rayos por compra ────────────────────────────────────────
# PENDIENTE DE DECISIÓN DE NEGOCIO. Por defecto 0.
PURCHASE_REWARD_RAYOS = 0

# ── Monedas permitidas ───────────────────────────────────────────────────────
# Físicos: solo PEN/Perú
PHYSICAL_CURRENCY = "PEN"
PHYSICAL_COUNTRY = "PE"
PHYSICAL_SHIPPING_COST = Decimal("10.00")

# Alquiler: proporción del precio digital
RENTAL_PRICE_FACTOR = Decimal("0.3")


def _generate_order_number() -> str:
    """Genera un número de orden único: AET-YYYYMMDDHHMMSS-XXXXXX."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AET-{ts}-{rand}"


PEN_EXCHANGE_RATES = {
    "USD": Decimal("0.27"),
    "EUR": Decimal("0.25"),
    "GBP": Decimal("0.21"),
    "MXN": Decimal("4.6"),
    "BRL": Decimal("1.35"),
    "CLP": Decimal("250"),
    "COP": Decimal("1050"),
    "ARS": Decimal("110"),
    "CAD": Decimal("0.37"),
    "AUD": Decimal("0.41"),
}


def get_book_price(db, book_id: int, currency: str, rental_days: int = None) -> dict:
    """
    Obtiene el precio de un libro para una moneda específica.

    Args:
        rental_days: 7, 14 o 30 días. Si se omite, retorna precio base de alquiler (14 días).

    Returns:
        dict con {price: Decimal, rental_price: Decimal|None, found: bool}
    """
    cursor = db.cursor()

    # Primero intentar book_prices (precios explícitos por moneda)
    cursor.execute(
        "SELECT price, rental_price FROM book_prices WHERE book_id = %s AND currency = %s AND is_active = TRUE",
        (book_id, currency),
    )
    row = cursor.fetchone()
    if row:
        rental = row["rental_price"]
        if rental is None:
            rental = Decimal(str(row["price"])) * RENTAL_PRICE_FACTOR
            rental = rental.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rental = _apply_rental_duration(rental, rental_days)
        return {
            "price": Decimal(str(row["price"])),
            "rental_price": rental,
            "found": True,
        }

    # Fallback: si la moneda es PEN y existe books.price, usarlo
    if currency == "PEN":
        cursor.execute("SELECT price FROM books WHERE id = %s", (book_id,))
        row = cursor.fetchone()
        if row and row["price"] is not None:
            price = Decimal(str(row["price"]))
            rental = (price * RENTAL_PRICE_FACTOR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rental = _apply_rental_duration(rental, rental_days)
            return {"price": price, "rental_price": rental, "found": True}

    # Auto-conversión: si no hay precio explícito para la moneda, convertir desde PEN
    if currency != "PEN" and currency in PEN_EXCHANGE_RATES:
        cursor.execute("SELECT price FROM books WHERE id = %s", (book_id,))
        row = cursor.fetchone()
        if row and row["price"] is not None:
            pen_price = Decimal(str(row["price"]))
            rate = PEN_EXCHANGE_RATES[currency]
            converted = (pen_price * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rental = (converted * RENTAL_PRICE_FACTOR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rental = _apply_rental_duration(rental, rental_days)
            return {"price": converted, "rental_price": rental, "found": True}

    return {"price": Decimal("0"), "rental_price": None, "found": False}


def _apply_rental_duration(base_rental: Decimal, rental_days: int = None) -> Decimal:
    """Aplica factor de duración al precio base de alquiler."""
    if rental_days is None or rental_days == 14:
        return base_rental
    factors = {7: Decimal("0.6"), 30: Decimal("1.5")}
    factor = factors.get(rental_days, Decimal("1.0"))
    return (base_rental * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_order(db, user_id: int, order_type: str, currency: str,
                 items_data: list, rental_days: int = None,
                 address_id: int = None) -> dict:
    """
    Crea una orden pendiente con sus items.

    Args:
        db: Conexión a la BD
        user_id: ID del usuario
        order_type: 'digital_purchase', 'digital_rental', 'physical_purchase'
        currency: PEN, CLP, MXN
        items_data: Lista de [{book_id, item_type, quantity, unit_price: Decimal, rental_days}]
        rental_days: Días de alquiler
        address_id: ID de dirección del usuario (solo físico)

    Returns:
        dict con order_id, order_number, total, currency o error
    """
    cursor = db.cursor()
    now = datetime.now(timezone.utc).isoformat()
    order_number = _generate_order_number()

    subtotal = Decimal("0")
    for item in items_data:
        price = Decimal(str(item["unit_price"]))
        qty = item.get("quantity", 1)
        subtotal += price * qty

    shipping_cost = Decimal("0")
    if order_type == "physical_purchase":
        shipping_cost = PHYSICAL_SHIPPING_COST
    total = subtotal + shipping_cost

    try:
        cursor.execute(
            """INSERT INTO orders
               (user_id, order_number, order_type, currency, subtotal, shipping_cost,
                total, payment_status, order_status, rental_days, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', 'pending', %s, %s)
               RETURNING id""",
            (user_id, order_number, order_type, currency,
             float(subtotal), float(shipping_cost), float(total),
             rental_days, now),
        )
        order_id = cursor.fetchone()["id"]

        for item in items_data:
            price = Decimal(str(item["unit_price"]))
            qty = item.get("quantity", 1)
            item_total = price * qty
            cursor.execute(
                """INSERT INTO order_items
                   (order_id, book_id, item_type, quantity, unit_price, total_price,
                    rental_days, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (order_id, item["book_id"], item["item_type"],
                 qty, float(price), float(item_total),
                 item.get("rental_days", rental_days), now),
            )

        db.commit()
        return {
            "success": True,
            "order_id": order_id,
            "order_number": order_number,
            "total": total,
            "currency": currency,
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


def confirm_payment(db, order_id: int, provider_token: str = None,
                    provider_order_id: str = None,
                    provider_payment_id: str = None,
                    provider: str = None) -> dict:
    """
    Marca una orden como pagada y ejecuta todos los efectos secundarios.
    Transacción: UPDATE order + efectos se hacen en la misma transacción.
    Idempotente: si ya fue procesada, retorna resultado existente.
    """
    cursor = db.cursor()
    now = datetime.now(timezone.utc).isoformat()

    try:
        # Bloquear la orden para evitar carreras
        cursor.execute(
            "SELECT * FROM orders WHERE id = %s FOR UPDATE",
            (order_id,),
        )
        order = cursor.fetchone()
        if not order:
            return {"success": False, "error": "Orden no encontrada"}

        # Idempotente: si ya está pagada
        if order["payment_status"] == "approved":
            return {"success": True, "message": "Orden ya procesada", "order_id": order_id}

        if order["payment_status"] in ("cancelled", "rejected"):
            return {"success": False, "error": f"Orden en estado {order['payment_status']}"}

        # Marcar como pagada
        cursor.execute(
            """UPDATE orders
               SET payment_status = 'approved', order_status = 'confirmed',
                   provider_token = %s, provider_order_id = %s,
                   provider = COALESCE(%s, provider),
                   paid_at = %s, updated_at = %s
               WHERE id = %s""",
            (provider_token, provider_order_id,
             provider, now, now, order_id),
        )

        # Aplicar efectos dentro de la misma transacción
        effects_result = _apply_order_effects(cursor, order_id, order)

        db.commit()
        return {
            "success": True,
            "order_id": order_id,
            "order_number": order["order_number"],
            "effects": effects_result,
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


def _apply_order_effects(cursor, order_id: int, order: dict) -> dict:
    """Aplica todos los efectos secundarios. Cada efecto es idempotente por order_effects."""
    now = datetime.now(timezone.utc).isoformat()
    results = {}

    # 1. Stock (ANTES de entitlement para físicos: si stock falla, no crear entitlement)
    if order["order_type"] == "physical_purchase":
        results["stock"] = _effect_decrement_stock(cursor, order_id, order)

    # 2. Entitlement (acceso digital)
    if order["order_type"] in ("digital_purchase", "digital_rental"):
        results["entitlement"] = _effect_create_entitlement(cursor, order_id, order)

    # 3. Rayos
    results["rayos"] = _effect_reward_rayos(cursor, order_id, order)

    # 4. Notificación
    results["notification"] = _effect_create_notification(cursor, order_id, order)

    # 5. Email (no debería estar en transacción DB, pero por ahora es aceptable)
    results["email"] = _effect_send_email(cursor, order_id, order)

    return results


def _effect_create_entitlement(cursor, order_id: int, order: dict) -> str:
    """Crea entitlement de acceso digital. Idempotente."""
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "SELECT id FROM order_effects WHERE order_id = %s AND effect_type = 'entitlement_created'",
        (order_id,),
    )
    if cursor.fetchone():
        return "already_applied"

    if order["order_type"] not in ("digital_purchase", "digital_rental"):
        return "not_applicable"

    cursor.execute(
        "SELECT book_id, item_type, rental_days FROM order_items WHERE order_id = %s",
        (order_id,),
    )
    items = cursor.fetchall()

    for item in items:
        if item["item_type"] == "digital_purchase":
            entitlement_type = "purchase"
            expires_at = None
        elif item["item_type"] == "digital_rental":
            entitlement_type = "rental"
            days = item["rental_days"] or order.get("rental_days") or 14
            start_dt = datetime.now(timezone.utc)
            end_dt = start_dt + timedelta(days=days)
            expires_at = end_dt.isoformat()
        else:
            continue

        cursor.execute(
            """INSERT INTO digital_entitlements
               (user_id, book_id, order_id, entitlement_type, starts_at, expires_at, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_id, book_id, order_id) DO NOTHING""",
            (order["user_id"], item["book_id"], order_id, entitlement_type,
             now, expires_at, now),
        )

    cursor.execute(
        "INSERT INTO order_effects (order_id, effect_type, created_at) VALUES (%s, 'entitlement_created', %s)",
        (order_id, now),
    )
    return "applied"


def _effect_reward_rayos(cursor, order_id: int, order: dict) -> str:
    """Acredita Rayos por compra. Idempotente."""
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "SELECT id FROM order_effects WHERE order_id = %s AND effect_type = 'rayos_rewarded'",
        (order_id,),
    )
    if cursor.fetchone():
        return "already_applied"

    if PURCHASE_REWARD_RAYOS <= 0:
        return "not_configured"

    from server import _credit_rayos, VALID_RAYOS_TYPES

    if "purchase_reward" not in VALID_RAYOS_TYPES:
        return "type_not_valid"

    cursor.execute(
        "SELECT book_id FROM order_items WHERE order_id = %s LIMIT 1",
        (order_id,),
    )
    item = cursor.fetchone()
    book_id = item["book_id"] if item else None

    book_title = "libro"
    if book_id:
        cursor.execute("SELECT title FROM books WHERE id = %s", (book_id,))
        book_row = cursor.fetchone()
        if book_row:
            book_title = book_row["title"]

    _credit_rayos(
        cursor,
        order["user_id"],
        PURCHASE_REWARD_RAYOS,
        "purchase_reward",
        f"Recompensa por compra de '{book_title}'",
        book_id=book_id,
    )

    cursor.execute(
        "INSERT INTO order_effects (order_id, effect_type, created_at) VALUES (%s, 'rayos_rewarded', %s)",
        (order_id, now),
    )
    return "applied"


def _effect_create_notification(cursor, order_id: int, order: dict) -> str:
    """Crea notificación interna. Idempotente."""
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "SELECT id FROM order_effects WHERE order_id = %s AND effect_type = 'notification_created'",
        (order_id,),
    )
    if cursor.fetchone():
        return "already_applied"

    cursor.execute(
        "SELECT book_id, item_type, rental_days FROM order_items WHERE order_id = %s LIMIT 1",
        (order_id,),
    )
    item = cursor.fetchone()
    book_title = "libro"
    if item and item["book_id"]:
        cursor.execute("SELECT title FROM books WHERE id = %s", (item["book_id"],))
        book_row = cursor.fetchone()
        if book_row:
            book_title = book_row["title"]

    if order["order_type"] == "digital_purchase":
        content = f"Tu compra de '{book_title}' fue confirmada. Ya puedes acceder a tu libro."
    elif order["order_type"] == "digital_rental":
        days = order.get("rental_days") or (item["rental_days"] if item else 14)
        content = f"Tu alquiler de '{book_title}' fue activado por {days} días."
    elif order["order_type"] == "physical_purchase":
        content = f"Tu pedido #{order['order_number']} está siendo preparado."
    else:
        content = f"Tu orden #{order['order_number']} fue procesada."

    cursor.execute(
        "INSERT INTO notifications (user_id, type, content, created_at) VALUES (%s, 'commerce', %s, %s)",
        (order["user_id"], content, now),
    )

    cursor.execute(
        "INSERT INTO order_effects (order_id, effect_type, created_at) VALUES (%s, 'notification_created', %s)",
        (order_id, now),
    )
    return "applied"


def _effect_send_email(cursor, order_id: int, order: dict) -> str:
    """Envía correo de confirmación. Idempotente."""
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "SELECT id FROM order_effects WHERE order_id = %s AND effect_type = 'email_sent'",
        (order_id,),
    )
    if cursor.fetchone():
        return "already_applied"

    cursor.execute("SELECT email, name FROM users WHERE id = %s", (order["user_id"],))
    user = cursor.fetchone()
    if not user:
        return "user_not_found"

    cursor.execute(
        "SELECT book_id, item_type, unit_price, rental_days FROM order_items WHERE order_id = %s LIMIT 1",
        (order_id,),
    )
    item = cursor.fetchone()
    book_title = "libro"
    if item and item["book_id"]:
        cursor.execute("SELECT title FROM books WHERE id = %s", (item["book_id"],))
        book_row = cursor.fetchone()
        if book_row:
            book_title = book_row["title"]

    from server import send_email_async
    currency = order.get("currency", "PEN")

    if order["order_type"] == "digital_purchase":
        subject = f"Confirmación de compra - {book_title}"
        html = _email_template_purchase_confirmed(
            user["name"], book_title, order["order_number"],
            Decimal(str(order["total"])), currency,
        )
    elif order["order_type"] == "digital_rental":
        days = order.get("rental_days") or (item["rental_days"] if item else 14)
        start = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        end = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%d/%m/%Y")
        subject = f"Confirmación de alquiler - {book_title}"
        html = _email_template_rental_confirmed(
            user["name"], book_title, order["order_number"],
            days, start, end,
        )
    elif order["order_type"] == "physical_purchase":
        subject = f"Confirmación de pedido #{order['order_number']}"
        html = _email_template_physical_confirmed(
            user["name"], order["order_number"],
            Decimal(str(order["total"])), currency,
        )
    else:
        return "unknown_order_type"

    try:
        send_email_async(user["email"], subject, html)
        cursor.execute(
            "INSERT INTO order_effects (order_id, effect_type, created_at) VALUES (%s, 'email_sent', %s)",
            (order_id, now),
        )
        return "applied"
    except Exception:
        return "send_failed"


def _effect_decrement_stock(cursor, order_id: int, order: dict) -> str:
    """Descuenta stock de libros físicos. Idempotente."""
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "SELECT id FROM order_effects WHERE order_id = %s AND effect_type = 'stock_decremented'",
        (order_id,),
    )
    if cursor.fetchone():
        return "already_applied"

    if order["order_type"] != "physical_purchase":
        return "not_applicable"

    cursor.execute(
        "SELECT book_id, quantity FROM order_items WHERE order_id = %s",
        (order_id,),
    )
    items = cursor.fetchall()

    for item in items:
        qty = item.get("quantity", 1)
        cursor.execute(
            "UPDATE books SET stock = stock - %s WHERE id = %s AND stock >= %s RETURNING stock",
            (qty, item["book_id"], qty),
        )
        if cursor.fetchone() is None:
            return "insufficient_stock"

    cursor.execute(
        "INSERT INTO order_effects (order_id, effect_type, created_at) VALUES (%s, 'stock_decremented', %s)",
        (order_id, now),
    )
    return "applied"


def has_access_to_book(db, user_id: int, book_id: int) -> dict:
    """Verifica si un usuario tiene acceso a un libro digital."""
    cursor = db.cursor()

    cursor.execute(
        """SELECT entitlement_type, expires_at, is_active
           FROM digital_entitlements
           WHERE user_id = %s AND book_id = %s AND is_active = TRUE
           ORDER BY created_at DESC LIMIT 1""",
        (user_id, book_id),
    )
    entitlement = cursor.fetchone()

    if not entitlement:
        return {"has_access": False, "entitlement_type": None, "expires_at": None}

    if entitlement["expires_at"]:
        expires = entitlement["expires_at"]
        if isinstance(expires, str):
            expires_dt = datetime.fromisoformat(expires)
        else:
            expires_dt = expires

        if expires_dt.tzinfo is None:
            now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            now_dt = datetime.now(timezone.utc)

        if now_dt > expires_dt:
            return {"has_access": False, "entitlement_type": "expired", "expires_at": str(expires)}

    return {
        "has_access": True,
        "entitlement_type": entitlement["entitlement_type"],
        "expires_at": entitlement["expires_at"],
    }


# ── Templates de Email ──────────────────────────────────────────────────────

def _email_template_purchase_confirmed(name: str, book_title: str, order_number: str,
                                        amount: Decimal, currency: str) -> str:
    from payment_providers import get_currency_symbol
    symbol = get_currency_symbol(currency)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #D92B2B; margin: 0;">AETERNUM</h1>
        </div>
        <div style="background: #1a1a1a; border-radius: 12px; padding: 30px; color: white;">
            <h2 style="color: #D4AF37; margin-top: 0;">Compra Confirmada</h2>
            <p>Hola {name},</p>
            <p>Tu compra fue procesada exitosamente.</p>
            <div style="background: #0A0A0A; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Libro:</strong> {book_title}</p>
                <p style="margin: 5px 0;"><strong>Pedido:</strong> #{order_number}</p>
                <p style="margin: 5px 0;"><strong>Monto:</strong> {symbol} {float(amount):.2f} {currency}</p>
                <p style="margin: 5px 0;"><strong>Estado:</strong> <span style="color: #10B981;">Pagado</span></p>
            </div>
            <p>Ya puedes acceder a tu libro desde la plataforma.</p>
            <a href="https://aeternumlibrary.com" style="display: inline-block; padding: 12px 24px; background-color: #D92B2B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 15px;">Ir a mi Biblioteca</a>
        </div>
        <p style="color: #666; font-size: 12px; text-align: center; margin-top: 20px;">
            Si no realizaste esta compra, contacta a soporte inmediatamente.
        </p>
    </div>
    """


def _email_template_rental_confirmed(name: str, book_title: str, order_number: str,
                                     days: int, start_date: str, end_date: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #D92B2B; margin: 0;">AETERNUM</h1>
        </div>
        <div style="background: #1a1a1a; border-radius: 12px; padding: 30px; color: white;">
            <h2 style="color: #D4AF37; margin-top: 0;">Alquiler Confirmado</h2>
            <p>Hola {name},</p>
            <p>Tu alquiler fue activado exitosamente.</p>
            <div style="background: #0A0A0A; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Libro:</strong> {book_title}</p>
                <p style="margin: 5px 0;"><strong>Pedido:</strong> #{order_number}</p>
                <p style="margin: 5px 0;"><strong>Duración:</strong> {days} días</p>
                <p style="margin: 5px 0;"><strong>Desde:</strong> {start_date}</p>
                <p style="margin: 5px 0;"><strong>Hasta:</strong> {end_date}</p>
            </div>
            <p>Tienes acceso al libro hasta la fecha de vencimiento.</p>
            <a href="https://aeternumlibrary.com" style="display: inline-block; padding: 12px 24px; background-color: #D92B2B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 15px;">Leer Ahora</a>
        </div>
    </div>
    """


def _email_template_physical_confirmed(name: str, order_number: str,
                                       amount: Decimal, currency: str) -> str:
    from payment_providers import get_currency_symbol
    symbol = get_currency_symbol(currency)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #D92B2B; margin: 0;">AETERNUM</h1>
        </div>
        <div style="background: #1a1a1a; border-radius: 12px; padding: 30px; color: white;">
            <h2 style="color: #D4AF37; margin-top: 0;">Pedido Confirmado</h2>
            <p>Hola {name},</p>
            <p>Tu pedido fue confirmado y está siendo preparado.</p>
            <div style="background: #0A0A0A; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Pedido:</strong> #{order_number}</p>
                <p style="margin: 5px 0;"><strong>Total:</strong> {symbol} {float(amount):.2f} {currency}</p>
                <p style="margin: 5px 0;"><strong>Transportista:</strong> Shalom</p>
            </div>
            <p>Te notificaremos cuando tu pedido sea enviado con el número de seguimiento.</p>
        </div>
    </div>
    """
