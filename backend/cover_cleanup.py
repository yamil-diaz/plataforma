#!/usr/bin/env python3
"""Clean up cover_candidates: merge duplicates, rename properly."""
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CANDIDATES = Path(r"C:\Users\Z\Desktop\plataforma\backend\cover_candidates")

# Rename _cover_candidate files to proper names
rename_map = {
    "204_cover_candidate.jpg": "204_En_la_Colonia_Penitenciaria.jpg",
    "206_cover_candidate.jpg": "206_Las_Preocupaciones_de_un_Padre.jpg",
    "208_cover_candidate.jpg": "208_Josefina_la_Cantora.jpg",
    "217_cover_candidate.jpg": "217_Los_Endemoniados.jpg",
    "221_cover_candidate.jpg": "221_La_Patrona.jpg",
    "236_cover_candidate.jpg": "236_El_Doctor_Ox.jpg",
    "270_cover_candidate.jpg": "270_La_Agencia_Thompson.jpg",
    "277_cover_candidate.jpg": "277_Historia_de_Dos_Ciudades.jpg",
    "280_cover_candidate.jpg": "280_El_Misterio_de_Edwin_Drood.jpg",
    "286_cover_candidate.jpg": "286_El_Manuscrito_de_un_Loco.jpg",
    "290_cover_candidate.jpg": "290_Cuento_de_Navidad.jpg",
}

# For ID 214, we already have 214_El_Adolescente.jpg from first run
# The 214_cover_candidate.jpg is a duplicate - just delete it

for old_name, new_name in rename_map.items():
    old_path = CANDIDATES / old_name
    new_path = CANDIDATES / new_name
    
    if old_path.exists():
        if new_path.exists():
            # Compare sizes
            if old_path.stat().st_size > new_path.stat().st_size:
                new_path.unlink()
                old_path.rename(new_path)
                print(f"  Renamed {old_name} -> {new_name} (larger)")
            else:
                old_path.unlink()
                print(f"  Removed {old_name} (existing {new_name} is larger)")
        else:
            old_path.rename(new_path)
            print(f"  Renamed {old_name} -> {new_name}")

# Remove duplicate 214_cover_candidate if it still exists
dup = CANDIDATES / "214_cover_candidate.jpg"
if dup.exists():
    dup.unlink()
    print(f"  Removed 214_cover_candidate.jpg (duplicate)")

# Final listing
print(f"\n=== FINAL COVER CANDIDATES ===")
files = sorted(CANDIDATES.glob("*"))
total = 0
for f in files:
    if f.is_file():
        print(f"  {f.name:60s} {f.stat().st_size:>10,} bytes")
        total += 1

print(f"\nTotal: {total} cover files ready for review")
