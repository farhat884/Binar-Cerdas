"""
Inisialisasi Firebase Admin SDK.

Butuh 2 hal dari Firebase Console (Project Settings > Service Accounts):
  1. File JSON service account -> simpan sebagai serviceAccountKey.json
     di root folder (JANGAN di-commit ke GitHub, sudah ada di .gitignore).
  2. Nama Storage bucket, contoh: "binar-cerdas.appspot.com"

Untuk deploy di Vercel, isi JSON service account tsb sebagai satu
environment variable (FIREBASE_CREDENTIALS_JSON) berisi string JSON-nya,
karena Vercel tidak menyimpan file biasa secara persisten.
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, storage

_bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")


def _load_credentials():
    # Opsi A: kredensial di-taruh langsung sebagai JSON string di env var
    # (dipakai saat deploy di Vercel).
    raw_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if raw_json:
        return credentials.Certificate(json.loads(raw_json))

    # Opsi B: kredensial berupa file lokal (dipakai saat development).
    cred_path = os.environ.get("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
    if os.path.exists(cred_path):
        return credentials.Certificate(cred_path)

    raise RuntimeError(
        "Kredensial Firebase tidak ditemukan. Set FIREBASE_CREDENTIALS_JSON "
        "(untuk production) atau taruh file serviceAccountKey.json di root "
        "project (untuk development). Lihat README.md."
    )


if not firebase_admin._apps:
    cred = _load_credentials()
    firebase_admin.initialize_app(cred, {"storageBucket": _bucket_name} if _bucket_name else None)

db = firestore.client()
bucket = storage.bucket() if _bucket_name else None
