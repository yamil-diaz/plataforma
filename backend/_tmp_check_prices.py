import psycopg2
import psycopg2.extras

conn = psycopg2.connect("postgresql://postgres:yamilpro002@localhost:5432/plataforma_dev", cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

# Check book 176
cur.execute("SELECT id, title, price, published FROM books WHERE id = 176")
b = cur.fetchone()
if b:
    print(f"Book 176: {dict(b)}")
else:
    print("Book 176 NOT FOUND")

# Check book_prices for 176
cur.execute("SELECT currency, price, rental_price, is_active FROM book_prices WHERE book_id = 176")
bp = cur.fetchall()
if bp:
    for r in bp:
        print(f"  book_prices: {r['currency']} = {r['price']} (rental={r['rental_price']}, active={r['is_active']})")
else:
    print("  book_prices: EMPTY (no entries)")

# Simulate get_book_price for PEN
print("\n--- get_book_price('PEN') simulation ---")
cur.execute("SELECT price, rental_price FROM book_prices WHERE book_id = 176 AND currency = 'PEN' AND is_active = TRUE")
row = cur.fetchone()
if row:
    print(f"  Found in book_prices: price={row['price']}, rental={row['rental_price']}")
else:
    print("  NOT in book_prices")
    cur.execute("SELECT price FROM books WHERE id = 176")
    r = cur.fetchone()
    if r and r['price']:
        print(f"  Fallback to books.price: {r['price']}")
    else:
        print("  No fallback (books.price is null/0)")

# Simulate get_book_price for USD
print("\n--- get_book_price('USD') simulation ---")
cur.execute("SELECT price, rental_price FROM book_prices WHERE book_id = 176 AND currency = 'USD' AND is_active = TRUE")
row = cur.fetchone()
if row:
    print(f"  Found in book_prices: price={row['price']}, rental={row['rental_price']}")
else:
    print("  NOT in book_prices")
    print("  No fallback (currency is not PEN)")

conn.close()
