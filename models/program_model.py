"""Data program pembelajaran dan jadwal internal."""
from database import fetch_all, execute, new_id, utcnow_iso

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
PROGRAM_MAP = {
    "SD": {"kelas": ["5", "6"], "mapel": ["Matematika", "IPA"]},
    "SMP": {"kelas": ["7", "8", "9"], "mapel": ["Matematika", "IPA"]},
    "SMA": {"kelas": ["10", "11"], "mapel": ["Matematika Wajib", "Matematika Tingkat Lanjut", "Fisika", "Kimia"]},
}
def get_program_map(): return PROGRAM_MAP

def allowed_subjects(jenjang, kelas):
    kelas = str(kelas)
    rules = {"SD": ({"5", "6"}, {"Matematika", "IPA"}), "SMP": ({"7", "8", "9"}, {"Matematika", "IPA"}), "SMA": ({"10", "11"}, {"Matematika Wajib", "Matematika Tingkat Lanjut", "Fisika", "Kimia"})}
    allowed_kelas, subjects = rules.get(str(jenjang), (set(), set()))
    return subjects if kelas in allowed_kelas else set()

def validate_program_item(jenjang, kelas, mapel): return str(mapel).strip() in allowed_subjects(jenjang, kelas)

def get_all_schedules():
    hasil = fetch_all("SELECT * FROM schedules")
    hasil.sort(key=lambda s: {"SD":0,"SMP":1,"SMA":2}.get(s.get("jenjang"),99))
    return hasil

def create_schedule(jenjang,kelas,mapel,hari,jam):
    sid = new_id()
    execute("INSERT INTO schedules (id,jenjang,kelas,mapel,hari,jam,created_at) VALUES (?,?,?,?,?,?,?)", (sid,jenjang,kelas,mapel,hari,jam,utcnow_iso()))
    return sid

def delete_schedule(schedule_id): execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
