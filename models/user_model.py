"""
Model 'users'. Field paling penting untuk pemisahan role: `role` ("admin"
atau "siswa"), dan `sisa_pertemuan` (hanya berubah lewat aksi admin).
"""
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from firebase_admin import firestore
from firebase_config import db

COLLECTION = "users"


def create_user(name, email, password, phone, role="siswa", jenjang=None, kelas=None):
    if get_user_by_email(email):
        return None, "Email sudah terdaftar. Silakan login."

    ref = db.collection(COLLECTION).document()
    data = {
        "name": name,
        "email": email.lower().strip(),
        "password": generate_password_hash(password),
        "phone": phone,
        "role": role,                     # "admin" | "siswa"
        "jenjang": jenjang,                # "SD" | "SMP" | "SMA" (None untuk admin)
        "kelas": kelas,
        "sisa_pertemuan": 0,               # HANYA diubah oleh admin (approve / kurangi)
        "total_pertemuan_dibeli": 0,
        "created_at": datetime.datetime.utcnow(),
    }
    ref.set(data)
    data["id"] = ref.id
    return data, None


def get_user_by_email(email):
    q = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1).stream()
    for doc in q:
        d = doc.to_dict()
        d["id"] = doc.id
        return d
    return None


def get_user_by_id(user_id):
    doc = db.collection(COLLECTION).document(user_id).get()
    if doc.exists:
        d = doc.to_dict()
        d["id"] = doc.id
        return d
    return None


def verify_password(user, password):
    return check_password_hash(user["password"], password)


def get_all_siswa():
    """Dipakai admin untuk melihat & mengelola sisa pertemuan tiap siswa."""
    q = db.collection(COLLECTION).where("role", "==", "siswa").stream()
    hasil = [{**doc.to_dict(), "id": doc.id} for doc in q]
    hasil.sort(key=lambda u: u.get("name", ""))
    return hasil


def tambah_pertemuan(user_id, jumlah):
    """Dipanggil saat admin approve pendaftaran/pembelian paket."""
    db.collection(COLLECTION).document(user_id).update({
        "sisa_pertemuan": firestore.Increment(jumlah),
        "total_pertemuan_dibeli": firestore.Increment(jumlah),
    })


def kurangi_pertemuan(user_id):
    """Dipanggil admin tiap kali 1 sesi les sudah berlangsung.
    Siswa TIDAK punya akses ke fungsi ini sama sekali (lihat student_routes.py)."""
    user = get_user_by_id(user_id)
    if not user:
        return False, "Siswa tidak ditemukan."
    if user.get("sisa_pertemuan", 0) <= 0:
        return False, "Sisa pertemuan siswa ini sudah 0."
    db.collection(COLLECTION).document(user_id).update({
        "sisa_pertemuan": firestore.Increment(-1)
    })
    return True, None
