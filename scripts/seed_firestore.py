"""
Isi Firestore dengan jadwal default (SD/SMP/SMA) supaya landing page tidak
kosong saat pertama kali dijalankan. Aman dijalankan berkali-kali (idempoten
secara kasar -- cek jumlah dokumen dulu sebelum menambah).

Cara pakai (dari root folder project):
    python scripts/seed_firestore.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.program_model import get_all_schedules, create_schedule, DEFAULT_SCHEDULES  # noqa: E402


def main():
    existing = get_all_schedules()
    if existing:
        print(f"Sudah ada {len(existing)} jadwal di Firestore, tidak menambah data baru.")
        return

    for s in DEFAULT_SCHEDULES:
        create_schedule(**s)
        print(f"Ditambahkan: {s['jenjang']} - {s['mapel']}")

    print("Selesai seeding jadwal default.")


if __name__ == "__main__":
    main()
