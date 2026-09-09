"""
Test manual untuk models/user_model.py (versi Turso).

Cara pakai (jalankan dari root project, sejajar dengan app.py):

    python test_user_model.py get_all_siswa
    python test_user_model.py get_user_by_email nama@email.com
    python test_user_model.py get_user_by_id ID_USER
    python test_user_model.py verify_password nama@email.com passwordnya

Script ini HANYA melakukan pembacaan (SELECT), TIDAK mengubah/menghapus
data apa pun, jadi aman dijalankan langsung ke database Turso asli.
"""

import sys

from models.user_model import (
    get_all_siswa,
    get_user_by_email,
    get_user_by_id,
    verify_password,
)


def cmd_get_all_siswa():
    siswa = get_all_siswa()
    print(f"Total siswa: {len(siswa)}\n")
    for s in siswa[:10]:
        print(
            f"- id={s['id']} | {s['name']} | {s['email']} | "
            f"sisa_pertemuan={s['sisa_pertemuan']} "
            f"({type(s['sisa_pertemuan']).__name__})"
        )
    if len(siswa) > 10:
        print(f"... dan {len(siswa) - 10} siswa lainnya")


def cmd_get_user_by_email(email):
    user = get_user_by_email(email)
    if not user:
        print(f"Tidak ditemukan user dengan email: {email}")
        return
    print("Ditemukan:")
    for k, v in user.items():
        if k == "password":
            continue  # jangan tampilkan hash password
        print(f"  {k}: {v!r} ({type(v).__name__})")


def cmd_get_user_by_id(user_id):
    user = get_user_by_id(user_id)
    if not user:
        print(f"Tidak ditemukan user dengan id: {user_id}")
        return
    for k, v in user.items():
        if k == "password":
            continue
        print(f"  {k}: {v!r} ({type(v).__name__})")


def cmd_verify_password(email, password):
    user = get_user_by_email(email)
    if not user:
        print(f"Tidak ditemukan user dengan email: {email}")
        return
    ok = verify_password(user, password)
    print("Password cocok" if ok else "Password TIDAK cocok")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "get_all_siswa":
        cmd_get_all_siswa()
    elif cmd == "get_user_by_email" and args:
        cmd_get_user_by_email(args[0])
    elif cmd == "get_user_by_id" and args:
        cmd_get_user_by_id(args[0])
    elif cmd == "verify_password" and len(args) == 2:
        cmd_verify_password(args[0], args[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()