import urllib.request
import json
import sys
import io
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API_BASE = "https://aeternum-world.onrender.com"

def fetch_json(url):
    print(f"Fetching {url}...")
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "AeternumLibrary-Audit/1.0")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    print(f"  Received {len(data)} bytes")
    return json.loads(data)

def main():
    print("=" * 70)
    print("AETERNUM LIBRARY - Production PDF / Book Cross-Reference Audit")
    print("=" * 70)

    print("\n[1/3] Fetching /api/debug/files ...")
    debug = fetch_json(f"{API_BASE}/api/debug/files")
    disk_files = debug.get("files_in_storage_books", [])
    print(f"  PDFs on disk: {len(disk_files)}")

    print("\n[2/3] Fetching /api/books ...")
    books_resp = fetch_json(f"{API_BASE}/api/books")
    if isinstance(books_resp, list):
        books = books_resp
    else:
        books = books_resp.get("books", [])
    print(f"  Books in DB: {len(books)}")

    # Check for duplicate filenames on disk
    dup_counts = Counter(disk_files)
    duplicates = {k: v for k, v in dup_counts.items() if v > 1}

    disk_set = set(disk_files)

    # Extract pdf_path and filename from each book
    book_pdf_paths = {}
    book_pdf_filenames = {}
    books_with_pdf = 0
    books_without_pdf = 0

    for book in books:
        bid = book.get("id") or book.get("book_id") or book.get("_id", "?")
        pdf_path = book.get("pdf_path") or book.get("filePath") or ""
        if pdf_path:
            books_with_pdf += 1
            filename = pdf_path.rsplit("/", 1)[-1] if "/" in pdf_path else pdf_path
            book_pdf_paths[bid] = pdf_path
            book_pdf_filenames[bid] = filename
        else:
            books_without_pdf += 1

    # Reverse map
    filename_to_books = {}
    for bid, fname in book_pdf_filenames.items():
        filename_to_books.setdefault(fname, []).append(bid)

    book_filenames_set = set(book_pdf_filenames.values())

    associated = disk_set & book_filenames_set
    orphan = disk_set - book_filenames_set

    books_missing_pdf = []
    for bid, fname in book_pdf_filenames.items():
        if fname not in disk_set:
            books_missing_pdf.append({
                "book_id": bid,
                "pdf_path": book_pdf_paths[bid],
                "filename": fname,
            })

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\n{'Metric':<45} {'Count':>8}")
    print("-" * 55)
    print(f"{'PDFs on disk':<45} {len(disk_files):>8}")
    print(f"{'Books in DB':<45} {len(books):>8}")
    print(f"{'Books with pdf_path':<45} {books_with_pdf:>8}")
    print(f"{'Books WITHOUT pdf_path':<45} {books_without_pdf:>8}")
    print(f"{'PDFs ASSOCIATED (match a book)':<45} {len(associated):>8}")
    print(f"{'PDFs ORPHAN (on disk, no book)':<45} {len(orphan):>8}")
    print(f"{'Books with MISSING PDF on disk':<45} {len(books_missing_pdf):>8}")
    print(f"{'Duplicate filenames on disk':<45} {len(duplicates):>8}")

    if duplicates:
        print(f"\n--- DUPLICATE FILENAMES ON DISK ({len(duplicates)}) ---")
        for fname, count in sorted(duplicates.items()):
            print(f"  {fname}  (appears {count}x)")

    print(f"\n--- ASSOCIATED PDFs ({len(associated)}) ---")
    for fname in sorted(associated):
        bids = filename_to_books[fname]
        print(f"  {fname}  <- book(s): {', '.join(str(b) for b in bids)}")

    print(f"\n--- ORPHAN PDFs ({len(orphan)}) ---")
    for fname in sorted(orphan):
        print(f"  {fname}")

    print(f"\n--- BOOKS WITH MISSING PDF ({len(books_missing_pdf)}) ---")
    for entry in sorted(books_missing_pdf, key=lambda e: str(e["book_id"])):
        print(f"  Book {entry['book_id']}: {entry['pdf_path']}")

    print("\n" + "=" * 70)
    print("DONE (READ-ONLY - no changes made)")
    print("=" * 70)

if __name__ == "__main__":
    main()
