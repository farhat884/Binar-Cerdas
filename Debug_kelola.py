"""
Reproduksi persis logika di routes/live_routes.py -> kelola() step by step,
buat lihat di step mana soalnya "hilang".

Cara pakai:
  python debug_kelola.py b5389df4989f4d0f9974
"""
import sys
import models.live_model as live_model
from models.materi_model import get_material
from models.soal_model import get_questions

session_id = sys.argv[1] if len(sys.argv) > 1 else input("ID sesi kelas: ").strip()

sess = live_model.get_session(session_id)
print("STEP 1 -- sess.material_id:", repr(sess.get("material_id")))

m = get_material(sess["material_id"])
print("STEP 2 -- materi ditemukan:", m is not None)
if m:
    print("          m['mapel'] =", repr(m.get("mapel")))
    print("          m['bab']   =", repr(m.get("bab")))
    print("          m['id']    =", repr(m.get("id")))

by_bab = get_questions(mapel=m.get("mapel"), bab=m.get("bab"))
print("STEP 3 -- get_questions(mapel=..., bab=...) ->", len(by_bab), "soal ketemu")
for q in by_bab[:5]:
    print("          -", repr(q.get("pertanyaan"))[:60], "| tipe=", repr(q.get("tipe")),
          "| checkpoint=", repr(q.get("checkpoint")), "| kelas=", repr(q.get("kelas")),
          "| mapel=", repr(q.get("mapel")), "| bab=", repr(q.get("bab")))

by_material = get_questions(material_id=m.get("id"))
print("STEP 4 -- get_questions(material_id=...) ->", len(by_material), "soal ketemu")

print()
print("Kalau STEP 3 nunjukin 0 soal padahal harusnya ada -- masalahnya di")
print("get_questions() atau ada whitespace aneh yang gak ketauan dari repr biasa.")
print("Kalau STEP 3 > 0 tapi soal tetap gak muncul di halaman web, masalahnya")
print("di kode template/grouping, bukan di query -- kasih tau hasil ini ke Claude.")