"""
Cek langsung isi sesi kelas live tertentu di database -- terutama
kolom material_id (apakah beneran kesimpen) dan status.

Cara pakai:
  python debug_sesi.py e95ff63319ef4fd08f25
(ganti dengan ID sesi kelas kamu -- itu bagian di URL setelah /admin/live/)
"""
import sys
from database import fetch_all, fetch_one

session_id = sys.argv[1] if len(sys.argv) > 1 else input("ID sesi kelas: ").strip()

sess = fetch_one("SELECT * FROM live_sessions WHERE id=?", (session_id,))
if not sess:
    print(f"Sesi dengan id={session_id!r} TIDAK KETEMU di tabel live_sessions.")
    sys.exit(1)

print("=" * 70)
print("ISI SESI KELAS:")
print("=" * 70)
for k, v in sess.items():
    print(f"  {k:<22} = {v!r}")

material_id = sess.get("material_id")
print()
print("=" * 70)
if not material_id:
    print("material_id KOSONG/NULL -- ini penyebabnya. Materi belum kesimpen")
    print("ke sesi ini sama sekali, walaupun dropdown-nya kelihatan kepilih.")
else:
    m = fetch_one("SELECT * FROM materials WHERE id=?", (material_id,))
    if not m:
        print(f"material_id={material_id!r} TERSIMPAN, tapi TIDAK ADA row materials")
        print("dengan id itu -- materinya mungkin sudah dihapus/diganti.")
    else:
        print(f"material_id={material_id!r} valid, merujuk ke materi:")
        print(f"  mapel={m.get('mapel')!r}  bab={m.get('bab')!r}  judul={m.get('judul')!r}")
        print()
        print("Ini harusnya SUDAH cukup buat soal muncul di section 'Atur kuis'.")
        print("Kalau tetap gak muncul, kemungkinan bug ada di fungsi")
        print("_soal_bab_materi() atau get_questions() -- kasih tau hasil ini")
        print("ke Claude buat digali lebih lanjut.")