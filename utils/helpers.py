import uuid
from firebase_config import bucket

ALLOWED_EXT = {"png", "jpg", "jpeg", "pdf", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def upload_bukti_pembayaran(file_storage, user_id):
    """Upload file bukti transfer ke Firebase Storage, return public URL.
    file_storage: objek werkzeug FileStorage dari request.files['bukti']"""
    if bucket is None:
        raise RuntimeError(
            "Firebase Storage belum dikonfigurasi. Set FIREBASE_STORAGE_BUCKET di .env"
        )
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    path = f"bukti_pembayaran/{user_id}_{uuid.uuid4().hex}.{ext}"
    blob = bucket.blob(path)
    blob.upload_from_file(file_storage, content_type=file_storage.content_type)
    blob.make_public()
    return blob.public_url


def format_rupiah(angka):
    return f"Rp{angka:,.0f}".replace(",", ".")
