import os
import re
import uuid
import requests
from urllib.parse import urlencode


def _cfg(bucket_env="SUPABASE_MATERI_BUCKET", bucket_default="materi"):
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SECRET_KEY", "")
    bucket = os.environ.get(bucket_env, bucket_default)

    if not url or not key:
        raise RuntimeError(
            "Supabase belum dikonfigurasi. "
            "Isi SUPABASE_URL dan SUPABASE_SECRET_KEY."
        )

    return url, key, bucket


def safe_pdf_name(filename):
    if not filename or not filename.lower().endswith(".pdf"):
        raise ValueError("Materi harus berupa file PDF.")

    stem = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        filename.rsplit(".", 1)[0]
    ).strip("-") or "materi"

    return (
        f"materials/"
        f"{uuid.uuid4().hex}-"
        f"{stem[:80]}.pdf"
    )


EKSTENSI_GAMBAR_DIIZINKAN = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def safe_image_name(filename):
    if not filename or not filename.lower().endswith(EKSTENSI_GAMBAR_DIIZINKAN):
        raise ValueError("Gambar harus berformat JPG, PNG, WEBP, atau GIF.")

    ext = filename.rsplit(".", 1)[1].lower()
    stem = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        filename.rsplit(".", 1)[0]
    ).strip("-") or "gambar-soal"

    return (
        f"soal-images/"
        f"{uuid.uuid4().hex}-"
        f"{stem[:80]}.{ext}"
    )


def create_signed_upload(filename, kind="pdf"):
    """kind: 'pdf' untuk materi, 'image' untuk gambar soal (misalnya soal matriks/grafik)."""
    url, key, bucket = _cfg()
    path = safe_image_name(filename) if kind == "image" else safe_pdf_name(filename)

    response = requests.post(
        f"{url}/storage/v1/object/upload/sign/{bucket}/{path}",
        headers={
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": "application/json",
        },
        json={
            "upsert": False
        },
        timeout=20,
    )

    if not response.ok:
        raise RuntimeError(
            "Gagal menyiapkan upload Supabase: "
            f"{response.status_code} - "
            f"{response.text[:300]}"
        )

    data = response.json()

    token = data.get("token")

    if not token:
        raise RuntimeError(
            f"Supabase tidak mengembalikan token upload: {data}"
        )

    upload_url = (
        f"{url}/storage/v1/object/upload/sign/"
        f"{bucket}/{path}?{urlencode({'token': token})}"
    )

    public_url = (
        f"{url}/storage/v1/object/public/"
        f"{bucket}/{path}"
    )

    return {
        "path": path,
        "token": token,
        "bucket": bucket,
        "upload_url": upload_url,
        "public_url": public_url,
    }


def delete_file(path):
    if not path:
        return

    try:
        url, key, bucket = _cfg()

        requests.delete(
            f"{url}/storage/v1/object/{bucket}/{path}",
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
            },
            timeout=15,
        )

    except Exception:
        pass