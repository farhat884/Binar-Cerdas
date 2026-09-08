# Migrasi Firestore -> Turso

Versi ini memindahkan model Flask utama ke Turso/libSQL. `firebase_config.py`, file ekspor Firestore, dan script seed lama dipertahankan sebagai arsip/backup, tetapi model aplikasi tidak lagi mengimpor Firestore.

## Environment
Set:
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- secret lain yang memang masih dipakai aplikasi

Jangan commit `.env` atau `serviceAccountKey.json`.

## Test
```bash
python test_turso.py
python -m py_compile database.py models/*.py routes/*.py auth/*.py services/*.py utils/*.py app.py
```

## Catatan
Schema hasil ekspor memakai kolom `TEXT`, sehingga model melakukan konversi angka/boolean/JSON saat membaca dan menulis. Data lama Firestore tidak dihapus oleh kode migrasi.
