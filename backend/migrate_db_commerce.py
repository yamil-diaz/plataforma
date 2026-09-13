# -*- coding: utf-8 -*-
"""
Migración: Sistema de Comercio AeternumLibrary.

Crea las tablas necesarias para soportar:
- Órdenes de compra (digital, alquiler, físico)
- Items de orden
- Derechos de acceso digital (entitlements)
- Direcciones de usuario
- Pedidos físicos
- Eventos de pago (auditoría + idempotencia)
- Precios por moneda (book_prices)
- Añade columnas a books (is_physical, physical_price, stock, isbn)
"""
import os

import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def migrate():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()

    print("Iniciando migración de Comercio...")

    # ── 1. Columnas nuevas en books ───────────────────────────────────────────
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS is_physical BOOLEAN DEFAULT FALSE")
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS physical_price NUMERIC(10,2) DEFAULT 0")
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS stock INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS isbn TEXT")
        conn.commit()
        print("Columnas de comercio añadidas a books.")
    except Exception as e:
        conn.rollback()
        print(f"Error añadiendo columnas a books: {e}")

    # ── 1b. Migrar books.price de REAL a NUMERIC(10,2) ──────────────────────
    try:
        cursor.execute("""
            ALTER TABLE books ALTER COLUMN price TYPE NUMERIC(10,2) 
            USING ROUND(price::numeric, 2)
        """)
        conn.commit()
        print("books.price migrado de REAL a NUMERIC(10,2).")
    except Exception as e:
        conn.rollback()
        print(f"books.price migración (puede ya ser NUMERIC): {e}")

    # ── 2. Tabla orders ──────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        order_number VARCHAR(32) UNIQUE NOT NULL,
        order_type TEXT NOT NULL CHECK (order_type IN ('digital_purchase', 'digital_rental', 'physical_purchase')),
        currency VARCHAR(3) NOT NULL DEFAULT 'PEN',
        subtotal NUMERIC(10,2) NOT NULL DEFAULT 0,
        shipping_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
        total NUMERIC(10,2) NOT NULL DEFAULT 0,
        payment_status TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'approved', 'rejected', 'cancelled')),
        order_status TEXT NOT NULL DEFAULT 'pending' CHECK (order_status IN ('pending', 'confirmed', 'preparing', 'shipped', 'delivered', 'cancelled')),
        payment_provider TEXT DEFAULT 'flow',
        provider_order_id TEXT,
        provider_token TEXT,
        rental_days INTEGER,
        created_at TEXT NOT NULL,
        paid_at TEXT,
        updated_at TEXT
    )
    """)
    print("Tabla 'orders' verificada.")

    # ── 3. Tabla order_items ─────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id),
        item_type TEXT NOT NULL CHECK (item_type IN ('digital_purchase', 'digital_rental', 'physical_purchase')),
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price NUMERIC(10,2) NOT NULL,
        total_price NUMERIC(10,2) NOT NULL,
        rental_days INTEGER,
        metadata JSONB,
        created_at TEXT NOT NULL
    )
    """)
    print("Tabla 'order_items' verificada.")

    # ── 4. Tabla digital_entitlements ────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS digital_entitlements (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER NOT NULL REFERENCES books(id),
        order_id INTEGER NOT NULL REFERENCES orders(id),
        entitlement_type TEXT NOT NULL CHECK (entitlement_type IN ('purchase', 'rental')),
        starts_at TEXT NOT NULL,
        expires_at TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, book_id, order_id)
    )
    """)
    print("Tabla 'digital_entitlements' verificada.")

    # ── 5. Tabla user_addresses ──────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_addresses (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        label TEXT DEFAULT 'Principal',
        recipient_name TEXT NOT NULL,
        recipient_phone TEXT NOT NULL,
        address_line1 TEXT NOT NULL,
        address_line2 TEXT,
        district TEXT,
        city TEXT,
        department TEXT,
        postal_code TEXT,
        country TEXT DEFAULT 'PE',
        is_default BOOLEAN DEFAULT FALSE,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )
    """)
    print("Tabla 'user_addresses' verificada.")

    # ── 6. Tabla physical_orders ─────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS physical_orders (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE UNIQUE,
        shipping_address_snapshot JSONB NOT NULL,
        carrier TEXT DEFAULT 'shalom',
        tracking_number TEXT,
        fulfillment_status TEXT NOT NULL DEFAULT 'pending' CHECK (fulfillment_status IN ('pending', 'preparing', 'shipped', 'delivered', 'cancelled')),
        shipped_at TEXT,
        delivered_at TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )
    """)
    print("Tabla 'physical_orders' verificada.")

    # ── 7. Tabla payment_events (auditoría) ──────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_events (
        id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
        provider TEXT NOT NULL DEFAULT 'flow',
        provider_event_id TEXT,
        event_type TEXT NOT NULL,
        payload JSONB,
        provider_payment_id TEXT,
        provider_order_id TEXT,
        amount NUMERIC(12,2),
        currency VARCHAR(3),
        status TEXT,
        flow_status INTEGER,
        flow_amount INTEGER,
        flow_currency VARCHAR(3),
        flow_commerce_order TEXT,
        processing_status TEXT NOT NULL DEFAULT 'received' CHECK (processing_status IN ('received', 'processed', 'failed', 'ignored')),
        error_message TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(provider, provider_event_id)
    )
    """)
    print("Tabla 'payment_events' verificada.")

    # ── 8. Tabla order_effects (idempotencia de efectos) ────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_effects (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        effect_type TEXT NOT NULL CHECK (effect_type IN ('entitlement_created', 'rayos_rewarded', 'notification_created', 'email_sent', 'stock_decremented')),
        created_at TEXT NOT NULL,
        UNIQUE(order_id, effect_type)
    )
    """)
    print("Tabla 'order_effects' verificada.")

    # ── 9. Tabla book_prices (precios por moneda) ───────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS book_prices (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        currency VARCHAR(3) NOT NULL,
        price NUMERIC(10,2) NOT NULL CHECK (price >= 0),
        rental_price NUMERIC(10,2) CHECK (rental_price >= 0),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        UNIQUE(book_id, currency)
    )
    """)
    print("Tabla 'book_prices' verificada.")

    # ── 10. Poblar book_prices desde books.price (solo PEN) ─────────────────
    try:
        cursor.execute("""
            INSERT INTO book_prices (book_id, currency, price, is_active, created_at)
            SELECT id, 'PEN', price, TRUE, NOW()::text
            FROM books
            WHERE price > 0
            ON CONFLICT (book_id, currency) DO NOTHING
        """)
        populated = cursor.rowcount
        conn.commit()
        if populated > 0:
            print(f"book_prices poblado con {populated} registros PEN desde books.price.")
        else:
            print("book_prices: sin nuevos registros para poblar (ya existen o price=0).")
    except Exception as e:
        conn.rollback()
        print(f"Error poblando book_prices: {e}")

    # ── 11. Índices ───────────────────────────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(payment_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitlements_user ON digital_entitlements(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitlements_user_book ON digital_entitlements(user_id, book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitlements_expires ON digital_entitlements(expires_at) WHERE expires_at IS NOT NULL")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_addresses_user ON user_addresses(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_physical_orders_order ON physical_orders(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_order ON payment_events(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_provider_id ON payment_events(provider_event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_effects_order ON order_effects(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_prices_book ON book_prices(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_prices_book_currency ON book_prices(book_id, currency)")

    # ── 12. Migración multi-proveedor (Paddle + Culqi) ──────────────────────
    # Agregar columnas nuevas a orders si no existen
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS provider_payment_id TEXT")
        conn.commit()
    except Exception:
        conn.rollback()

    # Agregar columnas nuevas a payment_events si no existen (ya creadas arriba)
    # Agregar constraint UNIQUE a payment_events(provider, provider_event_id)
    try:
        cursor.execute("""
            ALTER TABLE payment_events ADD CONSTRAINT payment_events_provider_event_unique
            UNIQUE (provider, provider_event_id)
        """)
        conn.commit()
    except Exception:
        conn.rollback()

    conn.commit()
    conn.close()
    print("Migración de Comercio completada con éxito.")


if __name__ == "__main__":
    migrate()
