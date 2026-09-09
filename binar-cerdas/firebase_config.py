"""Inisialisasi Firebase Admin SDK dan Firestore."""
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, storage


def _load_credentials():
    raw_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if raw_json:
        return credentials.Certificate(json.loads(raw_json))
    cred_path = os.environ.get("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
    if os.path.exists(cred_path):
        return credentials.Certificate(cred_path)
    raise RuntimeError(
        "Kredensial Firebase tidak ditemukan. Set FIREBASE_CREDENTIALS_JSON "
        "atau taruh serviceAccountKey.json di root project."
    )


if not firebase_admin._apps:
    cred = _load_credentials()
    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")
    options = {"storageBucket": bucket_name} if bucket_name else None
    firebase_admin.initialize_app(cred, options)


db = firestore.client()
