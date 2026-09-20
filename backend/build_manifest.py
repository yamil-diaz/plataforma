#!/usr/bin/env python3
"""Build the complete cover migration manifest."""
import json
import os
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BACKEND = Path(__file__).parent
COVERS_DIR = BACKEND / "cover_candidates"
PRODUCTION_JSON = BACKEND / "production_books.json"

# Load production books for title verification
with open(PRODUCTION_JSON, "r", encoding="utf-8") as f:
    books = json.load(f)

books_by_id = {b["id"]: b for b in books}

# Load Phase 2 results
with open(BACKEND / "cover_phase2_results.json", "r", encoding="utf-8") as f:
    p2 = json.load(f)

# Build mapping: book_id -> cover file
# Sources: unsplash_downloaded + priority (177, 178)
mapping = {}

# Priority covers (177, 178)
mapping[177] = {
    "source_file": "177_anaconda_otros_cuentos.png",
    "source": "test_covers (verified PDF cover)",
    "title_expected": "Anaconda y otros cuentos"
}
mapping[178] = {
    "source_file": "178_cesar_o_nada.png",
    "source": "test_covers (verified PDF cover)",
    "title_expected": "César o nada"
}

# Unsplash books from Phase 2 results
for entry in p2["unsplash_downloaded"]:
    bid = entry["id"]
    mapping[bid] = {
        "source_file": entry["filename"],
        "source": entry["source"],
        "title_expected": entry["title"]
    }

# Retry results (IDs that were in "failed" but found in retry)
retry_ids = [204, 206, 208, 214, 217, 221, 236, 270, 277, 280, 286, 290]
retry_names = {
    204: "204_En_la_Colonia_Penitenciaria.jpg",
    206: "206_Las_Preocupaciones_de_un_Padre.jpg",
    208: "208_Josefina_la_Cantora.jpg",
    214: "214_El_Adolescente.jpg",
    217: "217_Los_Endemoniados.jpg",
    221: "221_La_Patrona.jpg",
    236: "236_El_Doctor_Ox.jpg",
    270: "270_La_Agencia_Thompson.jpg",
    277: "277_Historia_de_Dos_Ciudades.jpg",
    280: "280_El_Misterio_de_Edwin_Drood.jpg",
    286: "286_El_Manuscrito_de_un_Loco.jpg",
    290: "290_Cuento_de_Navidad.jpg",
}

for bid in retry_ids:
    if bid in mapping and mapping[bid].get("source_file", "").startswith("201_"):
        # Already has a good mapping from unsplash_downloaded
        pass
    else:
        mapping[bid] = {
            "source_file": retry_names[bid],
            "source": "Open Library / Internet Archive (retry)",
            "title_expected": books_by_id[bid]["title"].strip()
        }

# Now verify every mapping
print("=" * 90)
print("MANIFEST VERIFICATION")
print("=" * 90)

errors = []
manifest = []

for bid in sorted(mapping.keys()):
    m = mapping[bid]
    source_file = m["source_file"]
    source_path = COVERS_DIR / source_file
    
    # Check file exists
    file_exists = source_path.exists()
    file_size = source_path.stat().st_size if file_exists else 0
    
    # Check book exists in production
    book = books_by_id.get(bid)
    book_exists = book is not None
    
    # Check title match (fuzzy)
    title_match = False
    db_title = ""
    if book_exists:
        db_title = book["title"].strip()
        expected = m["title_expected"].strip()
        # Fuzzy match: normalize both titles
        def normalize(t):
            t = t.lower().strip()
            t = re.sub(r'\s+', ' ', t)
            t = re.sub(r'de charles dickens en pdf$', '', t).strip()
            t = re.sub(r'de charles dickens$', '', t).strip()
            return t
        
        norm_db = normalize(db_title)
        norm_expected = normalize(expected)
        
        # Check if one contains the other or they're very similar
        title_match = (
            norm_expected in norm_db or
            norm_db in norm_expected or
            norm_expected[:20] in norm_db or
            norm_db[:20] in norm_expected
        )
    
    status = "pending"
    error_msg = ""
    
    if not book_exists:
        status = "error"
        error_msg = f"Book ID {bid} not found in production"
        errors.append({"id": bid, "error": error_msg})
    elif not file_exists:
        status = "error"
        error_msg = f"Cover file not found: {source_file}"
        errors.append({"id": bid, "error": error_msg})
    elif file_size < 1000:
        status = "warning"
        error_msg = f"Cover file very small ({file_size} bytes)"
    elif not title_match:
        status = "error"
        error_msg = f"Title mismatch: DB='{db_title}' vs Expected='{m['title_expected']}'"
        errors.append({"id": bid, "error": error_msg})
    else:
        status = "pending"
    
    entry = {
        "book_id": bid,
        "title": db_title if book_exists else m["title_expected"],
        "author": (book.get("author_name", "") or "").strip() if book_exists else "",
        "source_file": source_file,
        "source": m["source"],
        "source_url": "",
        "file_size": file_size,
        "status": status,
        "error": error_msg
    }
    
    manifest.append(entry)
    
    icon = "OK" if status == "pending" else "!!" if status == "warning" else "ERR"
    print(f"  [{icon}] ID {bid:3d}: {db_title[:45]:45s} | {source_file[:40]:40s} | {file_size:>8,} bytes")

# Add ID 176 as skipped
manifest.append({
    "book_id": 176,
    "title": "Rayuelas mentales",
    "author": "Rodrigo Ramos",
    "source_file": "",
    "source": "",
    "source_url": "",
    "file_size": 0,
    "status": "skipped",
    "error": "Contemporary original work - needs author-provided cover"
})

print(f"\n{'=' * 90}")
print(f"TOTAL ENTRIES: {len(manifest)}")
print(f"  Pending (ready to apply): {sum(1 for e in manifest if e['status'] == 'pending')}")
print(f"  Warnings: {sum(1 for e in manifest if e['status'] == 'warning')}")
print(f"  Errors: {sum(1 for e in manifest if e['status'] == 'error')}")
print(f"  Skipped (ID 176): {sum(1 for e in manifest if e['status'] == 'skipped')}")

if errors:
    print(f"\nERRORS:")
    for e in errors:
        print(f"  ID {e['id']}: {e['error']}")

# Save manifest
with open(BACKEND / "cover_migration_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"\nManifest saved to: {BACKEND / 'cover_migration_manifest.json'}")
