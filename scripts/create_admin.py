"""
Buat akun ADMIN pertama. Form pendaftaran publik (/register) selalu membuat
role 'siswa', jadi akun admin dibuat lewat script ini saja (dijalankan
manual sekali oleh pemilik aplikasi, bukan lewat website).

Cara pakai (dari root folder project):
    python scripts/create_admin.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user_model import create_user, get_user_by_email  # noqa: E402


def main():
    print("=== Buat Akun Admin Binar Cerdas ===")
    name = input("Nama: ").strip()
    email = input("Email: ").strip()
    phone = input("Nomor WhatsApp: ").strip()
    password = input("Kata sandi: ").strip()

    if get_user_by_email(email):
        print("Email ini sudah terdaftar. Gunakan email lain.")
        return

    user, error = create_user(
        name=name, email=email, password=password, phone=phone,
        role="admin", jenjang=None, kelas=None,
    )
    if error:
        print("Gagal:", error)
        return
    print(f"Akun admin '{user['name']}' berhasil dibuat. Silakan login di /login.")


if __name__ == "__main__":
    main()
