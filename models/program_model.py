"""Data program pembelajaran dan jadwal internal yang tetap bisa dikelola admin."""
import datetime
from firebase_config import db

COLLECTION = "schedules"
PROGRAMS = [
    {"jenjang":"SD", "kelas":"5–6", "mapel":["Matematika","IPA"], "deskripsi":"Penguatan konsep dasar, pemahaman materi, dan latihan soal untuk siswa kelas 5 sampai 6."},
    {"jenjang":"SMP", "kelas":"7–9", "mapel":["Matematika","IPA"], "deskripsi":"Pendalaman konsep dan latihan bertahap untuk siswa kelas 7 sampai 9."},
    {"jenjang":"SMA", "kelas":"10–11", "mapel":["Matematika Wajib","Matematika Tingkat Lanjut","Fisika","Kimia"], "deskripsi":"Pendalaman konsep, pemecahan masalah, dan persiapan evaluasi untuk kelas 10 sampai 11."},
]
DEFAULT_SCHEDULES = [
    {"jenjang":"SD", "kelas":"5-6", "mapel":"Matematika & IPA", "hari":"Senin & Kamis", "jam":"16.00 - 17.30"},
    {"jenjang":"SMP", "kelas":"7-9", "mapel":"Matematika & IPA", "hari":"Selasa & Jumat", "jam":"16.00 - 17.30"},
    {"jenjang":"SMA", "kelas":"10-11", "mapel":"Matematika Wajib, Matematika Tingkat Lanjut, Fisika & Kimia", "hari":"Rabu & Sabtu", "jam":"19.00 - 20.30"},
]
def get_programs(): return PROGRAMS

# Peta jenjang -> daftar kelas & mapel yang valid, dipakai buat bikin dropdown
# (Kelas/Mapel) yang saling terhubung di form Materi & Bank Soal, biar admin
# tinggal pilih (gak ketik manual) dan gak ada typo yang bikin data nyasar.
PROGRAM_MAP = {
    "SD": {"kelas": ["5", "6"], "mapel": ["Matematika", "IPA"]},
    "SMP": {"kelas": ["7", "8", "9"], "mapel": ["Matematika", "IPA"]},
    "SMA": {"kelas": ["10", "11"], "mapel": ["Matematika Wajib", "Matematika Tingkat Lanjut", "Fisika", "Kimia"]},
}

def get_program_map(): return PROGRAM_MAP

def allowed_subjects(jenjang, kelas):
    kelas = str(kelas)
    rules = {
        "SD": ({"5", "6"}, {"Matematika", "IPA"}),
        "SMP": ({"7", "8", "9"}, {"Matematika", "IPA"}),
        "SMA": ({"10", "11"}, {"Matematika Wajib", "Matematika Tingkat Lanjut", "Fisika", "Kimia"}),
    }
    allowed_kelas, subjects = rules.get(str(jenjang), (set(), set()))
    if kelas not in allowed_kelas:
        return set()
    return subjects

def validate_program_item(jenjang, kelas, mapel):
    return str(mapel).strip() in allowed_subjects(jenjang, kelas)

def get_all_schedules():
    hasil=[{**d.to_dict(),"id":d.id} for d in db.collection(COLLECTION).stream()]
    hasil.sort(key=lambda s:{"SD":0,"SMP":1,"SMA":2}.get(s.get("jenjang"),99))
    return hasil

def create_schedule(jenjang,kelas,mapel,hari,jam):
    ref=db.collection(COLLECTION).document(); ref.set({"jenjang":jenjang,"kelas":kelas,"mapel":mapel,"hari":hari,"jam":jam,"created_at":datetime.datetime.utcnow()}); return ref.id

def delete_schedule(schedule_id): db.collection(COLLECTION).document(schedule_id).delete()
