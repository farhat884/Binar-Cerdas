"""
Script diagnosa: bandingin persis (character-by-character) field mapel & bab
antara tabel `materials` (materi pengajaran) dan tabel `questions` (bank soal).

Cara pakai:
  1. Copy file ini ke folder project Binar Cerdas kamu (sejajar sama app.py,
     supaya bisa import database.py).
  2. Jalankan: python3 debug_materi_soal.py
  3. Baca outputnya -- kalau ada mapel/bab yang "keliatan sama" tapi repr()-nya
     beda, itu penyebabnya (biasanya spasi nyempil di ujung, atau beda kapital).
"""
from database import fetch_all

print("=" * 70)
print("MATERIALS (materi pengajaran) -- kombinasi kelas/mapel/bab unik:")
print("=" * 70)
mat_rows = fetch_all("SELECT DISTINCT kelas, mapel, bab FROM materials")
mat_combos = set()
for r in mat_rows:
    kelas, mapel, bab = r.get("kelas"), r.get("mapel"), r.get("bab")
    mat_combos.add((str(kelas), mapel, bab))
    print(f"  kelas={kelas!r:>6}  mapel={mapel!r:<25}  bab={bab!r}")

print()
print("=" * 70)
print("QUESTIONS (bank soal) -- kombinasi kelas/mapel/bab unik:")
print("=" * 70)
q_rows = fetch_all("SELECT DISTINCT kelas, mapel, bab FROM questions")
q_combos = set()
for r in q_rows:
    kelas, mapel, bab = r.get("kelas"), r.get("mapel"), r.get("bab")
    q_combos.add((str(kelas), mapel, bab))
    print(f"  kelas={kelas!r:>6}  mapel={mapel!r:<25}  bab={bab!r}")

print()
print("=" * 70)
print("KOMBINASI YANG ADA DI QUESTIONS TAPI TIDAK PERSIS SAMA DI MATERIALS:")
print("(ini yang bikin soal 'gak kedetect' di Kelas Live)")
print("=" * 70)
missing = q_combos - mat_combos
if not missing:
    print("  (kosong -- semua kombinasi soal cocok persis dengan materials)")
else:
    for kelas, mapel, bab in sorted(missing):
        print(f"  kelas={kelas!r:>6}  mapel={mapel!r:<25}  bab={bab!r}")
        # cari kandidat yang "hampir" cocok di materials, buat nunjukin bedanya
        for mk, mm, mb in mat_combos:
            if mk == kelas and mm.strip().lower() == (mapel or "").strip().lower() \
               and mb.strip().lower() == (bab or "").strip().lower():
                print(f"    -> mirip banget sama materi: mapel={mm!r} bab={mb!r}")
                print(f"       (bedanya cuma spasi/kapital -- ini biang keroknya)")