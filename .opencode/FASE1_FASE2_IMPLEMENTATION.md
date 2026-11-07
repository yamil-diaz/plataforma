# FASE 1 + FASE 2: IMPLEMENTATION ROADMAP

## FASE 1: LIMPIEZA TÉCNICA (2-3 días)

### 1.1 Eliminar Flow/CLP deprecado ✓ COMPLETADO
- ✓ `payment_providers.py`: Agregar comentario en línea 71 indicando CLP reservado para FASE 4
- ✓ `commerce_service.py`: Línea 100 — CLP en fallback rates (dejar, solo es config)
- ✓ `server.py`: Línea 760 — GeoIP mapping CLP→CL (dejar, es mapping geográfico válido)
- **NOTA**: No hay Flow API integration activa — fue eliminado previamente

### 1.2 Implementar Logging Profesional (REEMPLAZAR TODOS LOS print()) ✓ EN PROGRESO
**Cambios en `payment_providers.py`:**
- Línea 1-23: Agregar `import logging` + `logger = logging.getLogger("aeternum.payments")`
- Línea 295: `print(...)` → `logger.debug(...)`
- Línea 318: `print(...)` → `logger.error(...)`
- Línea 329: `print(...)` → `logger.debug(...)`
- Línea 334: `print(...)` → `logger.debug(...)`
- Línea 345: `print(...)` → `logger.error(...)`
- Línea 366: `print(...)` → `logger.error(...)`
- Línea 418-422: `print(...)` → `logger.debug(...)`
- Línea 457-462: `print(...)` → `logger.error(...)`
- Línea 475-484: `print(...)` → `logger.debug(...)`

**Cambios en `commerce_service.py`:**
- Línea 1-20: Agregar `import logging` + `logger = logging.getLogger("aeternum.commerce")`
- Línea 82: `print(...)` → `logger.info(...)`
- Línea 85: `print(...)` → `logger.warning(...)`

**Cambios en `webhook_handler.py`:**
- ✓ YA TIENE logging.getLogger("aeternum.webhooks")
- Línea 50: `print(...)` → `logger.warning(...)`
- Línea 58-60: `print(...)` → `logger.debug(...)`
- Línea 62: `print(...)` → `logger.error(...)`
- Línea 134: `print(...)` → `logger.debug(...)`
- Línea 163: `print(...)` → `logger.debug(...)`
- Línea 182: `print(...)` → `logger.debug(...)`
- Línea 205: `print(...)` → `logger.info(...)`
- Línea 237: `print(...)` → `logger.debug(...)`

### 1.3 Health Check DB + Retry Webhooks
**`database.py`:**
- Línea 53-82: YA EXISTE health check barato con `SELECT 1` — OK ✓
- Falta: Agregar método `health_check_pool()` para monitoreo externo

**`webhook_handler.py`:**
- Falta: Implementar retry automático con backoff exponencial
- Crear tabla `webhook_retry_queue` para eventos fallidos
- Cron job que procesa retry_queue cada 5 minutos

---

## FASE 2: SELLER PLATFORM COMPLETA (5-7 días)

### 2.1 Crear Tablas de Comisiones y Payout
**`database.py` — Agregar a `init_db()`:**

```python
# Tabla: Comisiones por orden
cursor.execute("""
CREATE TABLE IF NOT EXISTS seller_commissions (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    commission_percentage DECIMAL(5,2) NOT NULL,  -- ej: 30.00 = 30%
    order_total DECIMAL(12,2) NOT NULL,
    commission_amount DECIMAL(12,2) NOT NULL,
    currency TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'paid', 'cancelled')),
    created_at TEXT NOT NULL,
    approved_at TEXT,
    paid_at TEXT
)
""")

# Tabla: Saldos de vendedor
cursor.execute("""
CREATE TABLE IF NOT EXISTS seller_balances (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    currency TEXT NOT NULL,
    total_earned DECIMAL(12,2) DEFAULT 0,
    total_paid DECIMAL(12,2) DEFAULT 0,
    pending_amount DECIMAL(12,2) DEFAULT 0,
    last_payout_at TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(seller_id, currency)
)
""")

# Tabla: Payouts (liquidaciones)
cursor.execute("""
CREATE TABLE IF NOT EXISTS seller_payouts (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payout_number VARCHAR(32) UNIQUE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    payment_method TEXT,  -- bank_transfer, paypal, stripe_connect
    bank_info JSONB,  -- {account_number, bank_code, etc.} - ENCRYPTED en prod
    commission_ids TEXT,  -- CSV de IDs
    transaction_id TEXT,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    processed_at TEXT,
    completed_at TEXT
)
""")

# Índices
cursor.execute("CREATE INDEX IF NOT EXISTS idx_seller_commissions_seller ON seller_commissions(seller_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_seller_commissions_status ON seller_commissions(status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_seller_balances_seller ON seller_balances(seller_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_seller_payouts_seller ON seller_payouts(seller_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_seller_payouts_status ON seller_payouts(status)")
```

### 2.2 Vincular Libros a Vendedor + Comisiones
**`database.py` — Agregar migraciones a `users` y `books`:**

```python
# users: Agregar columnas seller
cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS seller_verified BOOLEAN DEFAULT FALSE")
cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS seller_approved_at TEXT")
# ✓ YA EXISTE

# books: Vincular a vendedor
cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS seller_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS commission_percentage DECIMAL(5,2) DEFAULT 30.00")
cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS is_for_sale BOOLEAN DEFAULT TRUE")

# order_items: Agregar seller_id para trazabilidad
cursor.execute("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS seller_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
```

### 2.3 Implementar Comisiones en Confirmación de Pago
**`commerce_service.py` — Modificar `confirm_payment()` y `_apply_order_effects()`:**

```python
def _effect_calculate_commissions(cursor, order_id: int, order: dict) -> str:
    """Calcula y registra comisiones de vendedores. Idempotente."""
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        "SELECT id FROM order_effects WHERE order_id = %s AND effect_type = 'commissions_calculated'",
        (order_id,),
    )
    if cursor.fetchone():
        return "already_applied"

    # Obtener items de la orden con vendedor
    cursor.execute(
        """SELECT oi.id, oi.book_id, oi.unit_price, oi.quantity, b.seller_id, b.commission_percentage
           FROM order_items oi
           LEFT JOIN books b ON oi.book_id = b.id
           WHERE oi.order_id = %s""",
        (order_id,),
    )
    items = cursor.fetchall()

    commission_ids = []
    for item in items:
        seller_id = item.get("seller_id")
        if not seller_id:
            continue  # Libros sin vendedor asignado (admin)

        commission_pct = Decimal(str(item.get("commission_percentage", 30)))
        unit_price = Decimal(str(item["unit_price"]))
        qty = item.get("quantity", 1)
        item_total = unit_price * qty
        commission_amount = (item_total * commission_pct / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

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

        # Actualizar balance del vendedor
        cursor.execute(
            """INSERT INTO seller_balances (seller_id, currency, total_earned, pending_amount, updated_at)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (seller_id, currency) DO UPDATE
               SET total_earned = total_earned + EXCLUDED.total_earned,
                   pending_amount = pending_amount + EXCLUDED.pending_amount,
                   updated_at = EXCLUDED.updated_at""",
            (seller_id, order.get("currency", "PEN"), float(commission_amount),
             float(commission_amount), now),
        )

    cursor.execute(
        """INSERT INTO order_effects
           (order_id, effect_type, created_at, metadata)
           VALUES (%s, 'commissions_calculated', %s, %s)""",
        (order_id, now, json.dumps({"commission_ids": commission_ids})),
    )
    return "applied"
```

**`commerce_service.py` — Modificar `_apply_order_effects()`:**

```python
def _apply_order_effects(cursor, order_id: int, order: dict) -> dict:
    """Aplica todos los efectos secundarios. Cada efecto es idempotente por order_effects."""
    now = datetime.now(timezone.utc).isoformat()
    results = {}

    # 1. Comisiones (PRIMERO, antes de entitlement)
    results["commissions"] = _effect_calculate_commissions(cursor, order_id, order)

    # 2. Stock (ANTES de entitlement para físicos)
    if order["order_type"] == "physical_purchase":
        results["stock"] = _effect_decrement_stock(cursor, order_id, order)

    # 3. Entitlement (acceso digital)
    if order["order_type"] in ("digital_purchase", "digital_rental"):
        results["entitlement"] = _effect_create_entitlement(cursor, order_id, order)

    # 4. Rayos
    results["rayos"] = _effect_reward_rayos(cursor, order_id, order)

    # 5. Notificación
    results["notification"] = _effect_create_notification(cursor, order_id, order)

    # 6. Email
    results["email"] = _effect_send_email(cursor, order_id, order)

    return results
```

### 2.4 Endpoints de Vendedor
**`server.py` — Agregar nuevos endpoints:**

```python
# GET /api/seller/dashboard
@app.get("/api/seller/dashboard")
def get_seller_dashboard(token: str = Depends(verify_token)):
    """Dashboard de vendedor con estadísticas."""
    db = get_db()
    cursor = db.cursor()
    
    # Verificar que es vendedor aprobado
    cursor.execute(
        "SELECT id, seller_verified FROM users WHERE id = %s",
        (token["user_id"],),
    )
    user = cursor.fetchone()
    if not user or not user["seller_verified"]:
        raise HTTPException(status_code=403, detail="No eres vendedor aprobado")
    
    # Estadísticas
    cursor.execute(
        """SELECT 
           COUNT(DISTINCT sc.order_id) as total_orders,
           COUNT(*) as total_commissions,
           SUM(sc.commission_amount) as total_earned,
           SUM(CASE WHEN sc.status = 'pending' THEN sc.commission_amount ELSE 0 END) as pending,
           COALESCE(sb.currency, 'PEN') as currency
           FROM seller_commissions sc
           LEFT JOIN seller_balances sb ON sc.seller_id = sb.seller_id
           WHERE sc.seller_id = %s""",
        (token["user_id"],),
    )
    stats = cursor.fetchone() or {}
    
    # Comisiones recientes
    cursor.execute(
        """SELECT sc.id, sc.order_id, sc.book_id, sc.commission_amount, sc.currency, sc.status, sc.created_at,
           b.title as book_title
           FROM seller_commissions sc
           LEFT JOIN books b ON sc.book_id = b.id
           WHERE sc.seller_id = %s
           ORDER BY sc.created_at DESC
           LIMIT 20""",
        (token["user_id"],),
    )
    commissions = cursor.fetchall()
    
    db.close()
    return {
        "stats": {
            "total_orders": stats.get("total_orders", 0),
            "total_earned": float(stats.get("total_earned") or 0),
            "pending": float(stats.get("pending") or 0),
            "currency": stats.get("currency", "PEN"),
        },
        "commissions": commissions,
    }

# POST /api/seller/payout/request
@app.post("/api/seller/payout/request")
def request_payout(amount: Decimal, currency: str = "PEN", token: str = Depends(verify_token)):
    """Solicita payout de comisiones."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        "SELECT id, seller_verified FROM users WHERE id = %s",
        (token["user_id"],),
    )
    user = cursor.fetchone()
    if not user or not user["seller_verified"]:
        raise HTTPException(status_code=403, detail="No eres vendedor aprobado")
    
    # Verificar saldo disponible
    cursor.execute(
        """SELECT pending_amount FROM seller_balances 
           WHERE seller_id = %s AND currency = %s""",
        (token["user_id"], currency),
    )
    balance = cursor.fetchone()
    if not balance or Decimal(str(balance["pending_amount"])) < amount:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")
    
    # Crear payout
    now = datetime.now(timezone.utc).isoformat()
    payout_number = f"PAYOUT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
    
    cursor.execute(
        """INSERT INTO seller_payouts
           (seller_id, payout_number, amount, currency, status, created_at)
           VALUES (%s, %s, %s, %s, 'pending', %s)
           RETURNING id""",
        (token["user_id"], payout_number, float(amount), currency, now),
    )
    payout_id = cursor.fetchone()["id"]
    
    db.commit()
    db.close()
    
    return {
        "success": True,
        "payout_id": payout_id,
        "payout_number": payout_number,
        "amount": float(amount),
        "currency": currency,
        "status": "pending",
    }

# GET /api/seller/payouts
@app.get("/api/seller/payouts")
def get_seller_payouts(token: str = Depends(verify_token)):
    """Historial de payouts del vendedor."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        "SELECT id, seller_verified FROM users WHERE id = %s",
        (token["user_id"],),
    )
    user = cursor.fetchone()
    if not user or not user["seller_verified"]:
        raise HTTPException(status_code=403, detail="No eres vendedor aprobado")
    
    cursor.execute(
        """SELECT id, payout_number, amount, currency, status, created_at, completed_at
           FROM seller_payouts
           WHERE seller_id = %s
           ORDER BY created_at DESC""",
        (token["user_id"],),
    )
    payouts = cursor.fetchall()
    db.close()
    
    return {"payouts": payouts}
```

---

## SUMMARY: QUÉ CAMBIA

| Archivo | Cambios |
|---------|---------|
| `payment_providers.py` | +logging, -print() |
| `commerce_service.py` | +logging, -print(), +_effect_calculate_commissions() |
| `webhook_handler.py` | +logging, -print() |
| `database.py` | +3 tablas, +índices, +migraciones |
| `server.py` | +4 endpoints seller (dashboard, payout request, payouts, etc) |

---

## VERIFICACIÓN

Después de implementar:
1. ✅ Ejecutar tests: `python -m pytest backend/tests/ -v`
2. ✅ Verificar tablas creadas: `psql` → `\dt seller_*`
3. ✅ Probar endpoint: POST `/api/seller/payout/request` con auth
4. ✅ Revisar logs: `logger.debug()` en production mode (vía RENDER_LOG_LEVEL=debug)
