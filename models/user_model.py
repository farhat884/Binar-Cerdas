"""
Model users.
"""

import datetime

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from firebase_config import db


COLLECTION = "users"


def create_user(
    name,
    email,
    password,
    phone,
    role="siswa",
    jenjang=None,
    kelas=None,
):
    if get_user_by_email(email):
        return (
            None,
            "Email sudah terdaftar. Silakan login."
        )

    ref = (
        db.collection(COLLECTION)
        .document()
    )

    data = {
        "name": name,
        "email": email.lower().strip(),
        "password": generate_password_hash(
            password
        ),
        "phone": phone,
        "role": role,
        "jenjang": jenjang,
        "kelas": kelas,

        "sisa_pertemuan": 0,

        "total_pertemuan_dibeli": 0,

        "created_at": datetime.datetime.utcnow(),
    }

    ref.set(data)

    data["id"] = ref.id

    return data, None


def get_user_by_email(email):
    q = (
        db.collection(COLLECTION)
        .where(
            "email",
            "==",
            email.lower().strip()
        )
        .limit(1)
        .stream()
    )

    for doc in q:
        data = doc.to_dict()

        data["id"] = doc.id

        return data

    return None


def get_user_by_id(user_id):
    doc = (
        db.collection(COLLECTION)
        .document(user_id)
        .get()
    )

    if doc.exists:
        data = doc.to_dict()

        data["id"] = doc.id

        return data

    return None


def verify_password(user, password):
    return check_password_hash(
        user["password"],
        password
    )


def get_all_siswa():
    """
    Dipakai admin untuk melihat
    seluruh siswa.
    """

    q = (
        db.collection(COLLECTION)
        .where(
            "role",
            "==",
            "siswa"
        )
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
        key=lambda u: u.get(
            "name",
            ""
        )
    )

    return hasil


def tambah_pertemuan(user_id, jumlah):
    """
    Menambahkan jumlah pertemuan
    secara manual atau dari pembelian paket.
    """

    try:
        jumlah = int(jumlah)

    except (
        ValueError,
        TypeError
    ):
        raise ValueError(
            "Jumlah pertemuan harus berupa angka."
        )

    if jumlah <= 0:
        raise ValueError(
            "Jumlah pertemuan harus lebih dari 0."
        )

    ref = (
        db.collection(COLLECTION)
        .document(user_id)
    )

    user_doc = ref.get()

    if not user_doc.exists:
        raise ValueError(
            "Data siswa tidak ditemukan."
        )

    data = user_doc.to_dict()

    sisa_sekarang = int(
        data.get(
            "sisa_pertemuan",
            0
        )
    )

    total_dibeli_sekarang = int(
        data.get(
            "total_pertemuan_dibeli",
            0
        )
    )

    sisa_baru = (
        sisa_sekarang + jumlah
    )

    total_dibeli_baru = (
        total_dibeli_sekarang + jumlah
    )

    ref.update({
        "sisa_pertemuan": sisa_baru,
        "total_pertemuan_dibeli": (
            total_dibeli_baru
        ),
    })

    return sisa_baru


def kurangi_pertemuan(user_id):

    user = get_user_by_id(user_id)

    if not user:
        return (
            False,
            "Siswa tidak ditemukan."
        )

    sisa_sekarang = int(
        user.get(
            "sisa_pertemuan",
            0
        )
    )

    if sisa_sekarang <= 0:
        return (
            False,
            "Sisa pertemuan siswa ini sudah 0."
        )

    sisa_baru = sisa_sekarang - 1

    db.collection(COLLECTION).document(
        user_id
    ).update({
        "sisa_pertemuan": sisa_baru
    })

    return (
        True,
        None
    )

def gunakan_pertemuan_untuk_materi(user_id):
    ok, error = kurangi_pertemuan(user_id)
    if not ok:
        raise ValueError(error)
    user = get_user_by_id(user_id)
    return int(user.get("sisa_pertemuan", 0))


def delete_siswa(user_id):
    """
    Hapus akun siswa secara permanen. Sengaja HANYA mau menghapus dokumen
    dengan role == "siswa" (bukan admin), sebagai jaring pengaman supaya
    fitur ini gak bisa kepakai buat menghapus akun admin lain lewat rute
    yang sama.
    """

    user = get_user_by_id(user_id)

    if not user:
        return (
            False,
            "Siswa tidak ditemukan."
        )

    if user.get("role") != "siswa":
        return (
            False,
            "Akun ini bukan akun siswa, tidak bisa dihapus lewat sini."
        )

    db.collection(COLLECTION).document(user_id).delete()

    return (True, None)