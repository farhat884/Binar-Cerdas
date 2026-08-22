"""
Model 'registrations' = pendaftaran / pembelian paket pertemuan.

Alur:
  1. Siswa isi form (jenjang, mapel, jumlah paket 1-4) + upload bukti bayar
     -> status "pending"
  2. Admin buka daftar pending, lihat bukti bayar, klik Setujui/Tolak
     -> status "approved" -> sisa_pertemuan siswa bertambah
     -> status "ditolak"  -> tidak ada perubahan sisa_pertemuan

1 paket  = Rp30.000 = 2x pertemuan/minggu
4 paket sekaligus = Rp120.000 = 8x pertemuan (kira-kira 1 bulan)
"""
import datetime
from firebase_admin import firestore
from firebase_config import db

COLLECTION = "registrations"

HARGA_PER_PAKET = 30000
PERTEMUAN_PER_PAKET = 2
MAKS_PAKET_SEKALIGUS = 4


def buat_pendaftaran(
    user_id,
    user_name,
    jumlah_paket,
    metode_pembayaran,
    nama_pengirim,
    tanggal_transfer,
    referensi_transfer,
):
    jumlah_paket = max(1, min(int(jumlah_paket), MAKS_PAKET_SEKALIGUS))
    total_pertemuan = jumlah_paket * PERTEMUAN_PER_PAKET
    total_harga = jumlah_paket * HARGA_PER_PAKET

    ref = db.collection(COLLECTION).document()
    data = {
        "user_id": user_id,
        "user_name": user_name,

        "jumlah_paket": jumlah_paket,

        "total_pertemuan": (
            jumlah_paket * PERTEMUAN_PER_PAKET
        ),

        "total_harga": (
            jumlah_paket * HARGA_PER_PAKET
        ),

        "metode_pembayaran": metode_pembayaran,
        "nama_pengirim": nama_pengirim,
        "tanggal_transfer": tanggal_transfer,
        "referensi_transfer": referensi_transfer,

        "status": "pending",

        "catatan_admin": "",

        "created_at": firestore.SERVER_TIMESTAMP,
    }
    ref.set(data)
    data["id"] = ref.id
    return data


def get_pendaftaran(reg_id):
    doc = db.collection(COLLECTION).document(reg_id).get()
    if doc.exists:
        return {**doc.to_dict(), "id": doc.id}
    return None


def get_pendaftaran_by_status(status="pending"):
    q = db.collection(COLLECTION).where("status", "==", status).stream()
    hasil = [{**doc.to_dict(), "id": doc.id} for doc in q]
    hasil.sort(key=lambda r: r.get("created_at") or datetime.datetime.min, reverse=True)
    return hasil


def get_pendaftaran_by_user(user_id):
    q = db.collection(COLLECTION).where("user_id", "==", user_id).stream()
    hasil = [{**doc.to_dict(), "id": doc.id} for doc in q]
    hasil.sort(key=lambda r: r.get("created_at") or datetime.datetime.min, reverse=True)
    return hasil


def proses_pendaftaran(reg_id, status, admin_id, catatan=""):
    """status: 'approved' atau 'ditolak'. Hanya dipanggil dari admin_routes.py."""
    db.collection(COLLECTION).document(reg_id).update({
        "status": status,
        "processed_at": datetime.datetime.utcnow(),
        "processed_by": admin_id,
        "catatan_admin": catatan,
    })
