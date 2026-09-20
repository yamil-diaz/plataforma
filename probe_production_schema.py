"""
PRODUCTION SCHEMA PROBE — READ-ONLY
Probes https://aeternum-world.onrender.com to determine exact DB schema.
"""
import urllib.request
import json
import sys
import time
from collections import Counter

BASE = "https://aeternum-world.onrender.com"
TIMEOUT = 120

FIELDS_OF_INTEREST = [
    "source", "source_hash", "source_url", "source_id", "source_format",
    "pdf_path", "page_count", "paginated_at", "published", "content",
    "cover_image_url", "uploader_id",
]

USER_FIELDS_OF_INTEREST = [
    "google_id", "email_verified", "google_email",
    "referred_by_qr_id", "verification_code", "verification_expiry",
]

def fetch(path, label=None):
    url = f"{BASE}{path}"
    label = label or path
    print(f"[*] Fetching {label} ... ", end="", flush=True)
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SchemaProbe/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            elapsed = time.time() - t0
            print(f"OK ({len(data)} bytes, {elapsed:.1f}s)")
            return json.loads(data)
    except Exception as e:
        elapsed = time.time() - t0
        print(f"FAILED ({elapsed:.1f}s): {e}")
        return None


def main():
    print("=" * 70)
    print("AETERNUM LIBRARY — PRODUCTION SCHEMA PROBE")
    print("=" * 70)

    # ── 1. /api/health ────────────────────────────────────────────────────
    print("\n### 1. /api/health ###")
    health = fetch("/api/health")
    if health:
        print(json.dumps(health, indent=2, default=str)[:3000])

    # ── 2. /api/debug/files (db_tables) ───────────────────────────────────
    print("\n### 2. /api/debug/files (db_tables) ###")
    debug = fetch("/api/debug/files")
    if debug:
        tables = debug.get("db_tables") or debug.get("tables")
        if tables:
            print(f"Tables found ({len(tables)}):")
            for t in sorted(tables):
                print(f"  - {t}")
        else:
            # Print keys to find the right field
            print("Keys:", list(debug.keys())[:20])
            # Print first 3000 chars
            s = json.dumps(debug, indent=2, default=str)
            print(s[:3000])

    # ── 3. /api/books — FULL ANALYSIS ─────────────────────────────────────
    print("\n### 3. /api/books — FULL ANALYSIS ###")
    books_data = fetch("/api/books", "/api/books (full ~42MB)")
    if not books_data:
        print("FATAL: Could not fetch /api/books")
        return

    if not isinstance(books_data, list):
        print(f"Response is not a list, type={type(books_data)}")
        if isinstance(books_data, dict):
            print("Keys:", list(books_data.keys())[:30])
        return

    total_books = len(books_data)
    print(f"\nTotal books returned: {total_books}")

    # ── 3a. ALL keys from the first book ──────────────────────────────────
    print("\n### 3a. ALL KEYS in first book object ###")
    first_book = books_data[0]
    all_keys = list(first_book.keys())
    print(f"Total keys: {len(all_keys)}")
    for i, k in enumerate(all_keys, 1):
        v = first_book[k]
        vtype = type(v).__name__
        if isinstance(v, str) and len(v) > 80:
            vpreview = repr(v[:80]) + f"... ({len(v)} chars)"
        else:
            vpreview = repr(v)
        print(f"  {i:2d}. {k:30s}  type={vtype:10s}  value={vpreview}")

    # ── 3b. Check specific fields ─────────────────────────────────────────
    print("\n### 3b. Field presence check (books table) ###")
    for f in FIELDS_OF_INTEREST:
        present = f in all_keys
        if present:
            # Count non-null across all books
            non_null = sum(1 for b in books_data if b.get(f) is not None)
            pct = (non_null / total_books * 100) if total_books else 0
            print(f"  [OK] {f:25s}  PRESENT  non_null={non_null}/{total_books} ({pct:.1f}%)")
        else:
            print(f"  [--] {f:25s}  NOT PRESENT in API response")

    # ── 3c. source distribution ───────────────────────────────────────────
    print("\n### 3c. source field distribution ###")
    if "source" in all_keys:
        source_counter = Counter()
        for b in books_data:
            source_counter[b.get("source")] += 1
        for val, cnt in source_counter.most_common():
            pct = cnt / total_books * 100
            val_short = repr(val)[:50]
            print(f"  source={val_short:50s}  count={cnt:5d}  ({pct:.1f}%)")
    else:
        print("  'source' field not in response")

    # ── 3d. source_hash distribution ──────────────────────────────────────
    print("\n### 3d. source_hash field distribution ###")
    if "source_hash" in all_keys:
        hash_counter = Counter()
        first_5_hashes = []
        for b in books_data:
            h = b.get("source_hash")
            hash_counter[h is not None] += 1
            if h and len(first_5_hashes) < 5:
                first_5_hashes.append(h[:16])
        null_count = hash_counter.get(None, hash_counter.get(False, 0))
        non_null_count = hash_counter.get(True, 0)
        print(f"  source_hash=NULL:     {null_count}/{total_books} ({null_count/total_books*100:.1f}%)")
        print(f"  source_hash!=NULL:    {non_null_count}/{total_books} ({non_null_count/total_books*100:.1f}%)")
        if first_5_hashes:
            print(f"  First 5 hashes (16 chars):")
            for i, h in enumerate(first_5_hashes, 1):
                print(f"    {i}. {h}")
    else:
        print("  'source_hash' field not in response")

    # ── 3e. content field analysis ────────────────────────────────────────
    print("\n### 3e. content field analysis ###")
    if "content" in all_keys:
        content_lengths = []
        content_null = 0
        for b in books_data:
            c = b.get("content")
            if c is None:
                content_null += 1
            else:
                content_lengths.append(len(c))
        print(f"  content=NULL:  {content_null}/{total_books}")
        if content_lengths:
            print(f"  content!=NULL: {len(content_lengths)}/{total_books}")
            print(f"  Min length:    {min(content_lengths)}")
            print(f"  Max length:    {max(content_lengths)}")
            print(f"  Avg length:    {sum(content_lengths)/len(content_lengths):.0f}")
            print(f"  Median length: {sorted(content_lengths)[len(content_lengths)//2]}")
    else:
        print("  'content' field not in response")

    # ── 3f. uploader_id distribution ──────────────────────────────────────
    print("\n### 3f. uploader_id field distribution ###")
    if "uploader_id" in all_keys:
        uid_counter = Counter()
        for b in books_data:
            uid_counter[b.get("uploader_id")] += 1
        null_count = uid_counter.get(None, 0)
        non_null_count = total_books - null_count
        print(f"  uploader_id=NULL:    {null_count}/{total_books} ({null_count/total_books*100:.1f}%)")
        print(f"  uploader_id!=NULL:   {non_null_count}/{total_books} ({non_null_count/total_books*100:.1f}%)")
        # Show top uploader_ids
        top_ids = [(k, v) for k, v in uid_counter.most_common() if k is not None][:5]
        if top_ids:
            print(f"  Top uploader_ids:")
            for uid, cnt in top_ids:
                print(f"    id={uid}: {cnt} books")
    else:
        print("  'uploader_id' field not in response")

    # ── 3g. published distribution ────────────────────────────────────────
    print("\n### 3g. published field distribution ###")
    if "published" in all_keys:
        pub_counter = Counter()
        for b in books_data:
            pub_counter[b.get("published")] += 1
        for val, cnt in pub_counter.most_common():
            print(f"  published={val}: {cnt}/{total_books} ({cnt/total_books*100:.1f}%)")
    else:
        print("  'published' field not in response")

    # ── 3h. source_url distribution ───────────────────────────────────────
    print("\n### 3h. source_url field distribution ###")
    if "source_url" in all_keys:
        su_counter = Counter()
        for b in books_data:
            su_counter[b.get("source_url") is not None] += 1
        null_count = su_counter.get(False, 0)
        non_null_count = su_counter.get(True, 0)
        print(f"  source_url=NULL:     {null_count}/{total_books} ({null_count/total_books*100:.1f}%)")
        print(f"  source_url!=NULL:    {non_null_count}/{total_books} ({non_null_count/total_books*100:.1f}%)")
    else:
        print("  'source_url' field not in response")

    # ── 3i. source_id / source_format distribution ────────────────────────
    print("\n### 3i. source_id / source_format distribution ###")
    for field in ["source_id", "source_format"]:
        if field in all_keys:
            non_null = sum(1 for b in books_data if b.get(field) is not None)
            print(f"  {field}=NULL:    {total_books - non_null}/{total_books}")
            print(f"  {field}!=NULL:   {non_null}/{total_books}")
        else:
            print(f"  {field} not in response")

    # ── 3j. page_count / paginated_at / pdf_path ──────────────────────────
    print("\n### 3j. page_count / paginated_at / pdf_path ###")
    for field in ["page_count", "paginated_at", "pdf_path"]:
        if field in all_keys:
            non_null = sum(1 for b in books_data if b.get(field) is not None)
            vals = [b.get(field) for b in books_data if b.get(field) is not None]
            print(f"  {field}=NULL:    {total_books - non_null}/{total_books}")
            print(f"  {field}!=NULL:   {non_null}/{total_books}")
            if vals and isinstance(vals[0], (int, float)):
                print(f"  min={min(vals)}, max={max(vals)}, avg={sum(vals)/len(vals):.1f}")
        else:
            print(f"  {field} not in response")

    # ── 4. Check for user-related fields across all books ─────────────────
    print("\n### 4. User-related fields in book data ###")
    for f in USER_FIELDS_OF_INTEREST:
        present_in_any = any(f in b for b in books_data)
        present_in_first = f in first_book
        print(f"  {f:25s}  in_first={present_in_first}  in_any={present_in_any}")

    # ── 5. Check ALL unique keys across ALL books ─────────────────────────
    print("\n### 5. Union of ALL keys across ALL books ###")
    all_union_keys = set()
    for b in books_data:
        all_union_keys.update(b.keys())
    all_union_keys_sorted = sorted(all_union_keys)
    print(f"Total unique keys: {len(all_union_keys_sorted)}")
    for k in all_union_keys_sorted:
        in_first = k in first_book
        non_null = sum(1 for b in books_data if b.get(k) is not None)
        print(f"  {k:35s}  in_first={str(in_first):5s}  non_null={non_null}/{total_books}")

    print("\n" + "=" * 70)
    print("SCHEMA PROBE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
