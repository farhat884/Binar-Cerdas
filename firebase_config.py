"""
Inisialisasi Firebase Admin SDK.

Untuk development lokal:
- Simpan serviceAccountKey.json di root project.

Untuk deploy di Vercel:
- Isi FIREBASE_CREDENTIALS_JSON
  dengan isi JSON service account Firebase.
"""

import os
import json

import firebase_admin

from firebase_admin import (
    credentials,
    firestore,
)


def _load_credentials():

    # ==========================================
    # OPSI A
    # FIREBASE_CREDENTIALS_JSON
    # Untuk Vercel
    # ==========================================

    raw_json = os.environ.get(
        "FIREBASE_CREDENTIALS_JSON"
    )

    if raw_json:

        return credentials.Certificate(
            json.loads(raw_json)
        )


    # ==========================================
    # OPSI B
    # serviceAccountKey.json
    # Untuk localhost
    # ==========================================

    cred_path = os.environ.get(
        "FIREBASE_CREDENTIALS",
        "serviceAccountKey.json"
    )

    if os.path.exists(cred_path):

        return credentials.Certificate(
            cred_path
        )


    # ==========================================
    # KALAU KREDENSIAL TIDAK DITEMUKAN
    # ==========================================

    raise RuntimeError(
        "Kredensial Firebase tidak ditemukan. "
        "Set FIREBASE_CREDENTIALS_JSON "
        "(untuk Vercel) atau taruh "
        "serviceAccountKey.json di root project."
    )


# ==========================================
# INISIALISASI FIREBASE
# ==========================================

if not firebase_admin._apps:

    cred = _load_credentials()

    firebase_admin.initialize_app(
        cred
    )


# ==========================================
# FIRESTORE DATABASE
# ==========================================

db = firestore.client()