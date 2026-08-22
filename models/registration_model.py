"""
Model registrations untuk pembelian paket pertemuan.

Alur:
1. Siswa memilih jumlah paket dan mengisi informasi pembayaran.
2. Data pembelian masuk dengan status "pending".
3. Admin dapat menyetujui atau menolak pembelian.
4. Jika disetujui, sisa pertemuan siswa bertambah.
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
    try:
        jumlah_paket = int(jumlah_paket)
    except (ValueError, TypeError):
        jumlah_paket = 1

    jumlah_paket = max(
        1,
        min(jumlah_paket, MAKS_PAKET_SEKALIGUS)
    )

    total_pertemuan = (
        jumlah_paket * PERTEMUAN_PER_PAKET
    )

    total_harga = (
        jumlah_paket * HARGA_PER_PAKET
    )

    data = {
        "user_id": user_id,
        "user_name": user_name,

        "jumlah_paket": jumlah_paket,

        "total_pertemuan": total_pertemuan,

        "total_harga": total_harga,

        "metode_pembayaran": metode_pembayaran,
        "nama_pengirim": nama_pengirim,
        "tanggal_transfer": tanggal_transfer,
        "referensi_transfer": referensi_transfer,

        "status": "pending",

        "catatan_admin": "",

        "created_at": firestore.SERVER_TIMESTAMP,

        "processed_at": None,
        "processed_by": None,
    }

    ref = db.collection(COLLECTION).document()

    ref.set(data)

    data["id"] = ref.id

    return data


def get_pendaftaran(reg_id):
    doc = (
        db.collection(COLLECTION)
        .document(reg_id)
        .get()
    )

    if doc.exists:
        return {
            **doc.to_dict(),
            "id": doc.id,
        }

    return None


def get_pendaftaran_by_status(status="pending"):
    q = (
        db.collection(COLLECTION)
        .where("status", "==", status)
        .stream()
    )

    hasil = [
        {
            **doc.to_dict(),
            "id": doc.id,
        }
        for doc in q
    ]

    hasil.sort(
        key=lambda r: (
            r.get("created_at")
            or datetime.datetime.min
        ),
        reverse=True,
    )

    return hasil


def get_pendaftaran_by_user(user_id):
    q = (
        db.collection(COLLECTION)
        .where("user_id", "==", user_id)
        .stream()
    )

    hasil = [
        {
            **doc.to_dict(),
            "id": doc.id,
        }
        for doc in q
    ]

    hasil.sort(
        key=lambda r: (
            r.get("created_at")
            or datetime.datetime.min
        ),
        reverse=True,
    )

    return hasil


def proses_pendaftaran(
    reg_id,
    status,
    admin_id,
    catatan=""
):
    """
    status:
    - approved
    - ditolak
    """

    db.collection(COLLECTION).document(
        reg_id
    ).update({
        "status": status,
        "processed_at": firestore.SERVER_TIMESTAMP,
        "processed_by": admin_id,
        "catatan_admin": catatan,
    })
