"""
Model 'schedules' = jadwal kelas yang tampil di landing page & dashboard siswa.
Admin bisa tambah/hapus jadwal lewat /admin/jadwal.
"""
import datetime
from firebase_config import db

COLLECTION = "schedules"

# Data awal (dipakai kalau koleksi Firestore masih kosong, lihat scripts/seed_firestore.py)
DEFAULT_SCHEDULES = [
    {"jenjang": "SD", "kelas": "5-6", "mapel": "Matematika & IPA", "hari": "Senin & Kamis", "jam": "16.00 - 17.30"},
    {"jenjang": "SMP", "kelas": "7-9", "mapel": "Matematika & IPA", "hari": "Selasa & Jumat", "jam": "16.00 - 17.30"},
    {"jenjang": "SMA", "kelas": "10-11", "mapel": "Matematika, Fisika & Kimia", "hari": "Rabu & Sabtu", "jam": "19.00 - 20.30"},
]


def get_all_schedules():
    q = db.collection(COLLECTION).stream()
    hasil = [{**doc.to_dict(), "id": doc.id} for doc in q]
    urutan = {"SD": 0, "SMP": 1, "SMA": 2}
    hasil.sort(key=lambda s: urutan.get(s.get("jenjang"), 99))
    return hasil


def create_schedule(jenjang, kelas, mapel, hari, jam):
    ref = db.collection(COLLECTION).document()
    data = {
        "jenjang": jenjang, "kelas": kelas, "mapel": mapel,
        "hari": hari, "jam": jam,
        "created_at": datetime.datetime.utcnow(),
    }
    ref.set(data)
    return ref.id


def delete_schedule(schedule_id):
    db.collection(COLLECTION).document(schedule_id).delete()
