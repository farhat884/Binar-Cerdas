"""
SEMUA route di file ini khusus role 'siswa' (@student_required).

Siswa BISA:
  - lihat jadwal kelas
  - lihat sisa pertemuan miliknya sendiri (read-only, tidak ada tombol ubah)
  - daftar les / beli paket (1-4 paket sekaligus) + upload bukti bayar
  - lihat riwayat & status pendaftarannya

Siswa TIDAK BISA (tidak ada route/tombol untuk ini sama sekali di sisi siswa):
  - mengubah sisa_pertemuan miliknya atau siswa lain
  - approve/tolak pendaftaran siapapun (termasuk miliknya sendiri)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.decorators import student_required
from models.user_model import get_user_by_id
from models.program_model import get_all_schedules
from models.registration_model import (
    buat_pendaftaran, get_pendaftaran_by_user,
    HARGA_PER_PAKET, PERTEMUAN_PER_PAKET, MAKS_PAKET_SEKALIGUS,
)
from utils.helpers import upload_bukti_pembayaran, allowed_file, format_rupiah

student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@student_required
def dashboard():
    user = get_user_by_id(session["user_id"])
    riwayat = get_pendaftaran_by_user(session["user_id"])[:5]
    return render_template("student/dashboard.html", user=user, riwayat=riwayat)


@student_bp.route("/jadwal")
@student_required
def jadwal():
    user = get_user_by_id(session["user_id"])
    semua_jadwal = get_all_schedules()
    return render_template("student/jadwal.html", user=user, jadwal=semua_jadwal)


@student_bp.route("/daftar-les", methods=["GET", "POST"])
@student_required
def daftar_les():
    user = get_user_by_id(session["user_id"])

    if request.method == "POST":
        jenjang = request.form.get("jenjang")
        mapel = request.form.get("mapel", "").strip()
        try:
            jumlah_paket = int(request.form.get("jumlah_paket", 1))
        except ValueError:
            jumlah_paket = 1
        jumlah_paket = max(1, min(jumlah_paket, MAKS_PAKET_SEKALIGUS))

        file = request.files.get("bukti")
        if not file or file.filename == "":
            flash("Bukti pembayaran wajib diunggah.", "danger")
            return render_template("student/daftar_les.html", user=user,
                                    harga_per_paket=HARGA_PER_PAKET,
                                    pertemuan_per_paket=PERTEMUAN_PER_PAKET,
                                    maks_paket=MAKS_PAKET_SEKALIGUS)
        if not allowed_file(file.filename):
            flash("Format file harus JPG, PNG, atau PDF.", "danger")
            return render_template("student/daftar_les.html", user=user,
                                    harga_per_paket=HARGA_PER_PAKET,
                                    pertemuan_per_paket=PERTEMUAN_PER_PAKET,
                                    maks_paket=MAKS_PAKET_SEKALIGUS)

        try:
            bukti_url = upload_bukti_pembayaran(file, user["id"])
        except RuntimeError as e:
            flash(str(e), "danger")
            return render_template("student/daftar_les.html", user=user,
                                    harga_per_paket=HARGA_PER_PAKET,
                                    pertemuan_per_paket=PERTEMUAN_PER_PAKET,
                                    maks_paket=MAKS_PAKET_SEKALIGUS)

        buat_pendaftaran(
            user_id=user["id"], user_name=user["name"],
            jenjang=jenjang, mapel=mapel,
            jumlah_paket=jumlah_paket, bukti_url=bukti_url,
        )
        flash(
            "Pendaftaran terkirim! Menunggu persetujuan admin setelah bukti "
            "pembayaran diverifikasi. Sisa pertemuanmu akan otomatis "
            "bertambah begitu disetujui.", "success",
        )
        return redirect(url_for("student.riwayat"))

    return render_template(
        "student/daftar_les.html", user=user,
        harga_per_paket=HARGA_PER_PAKET,
        pertemuan_per_paket=PERTEMUAN_PER_PAKET,
        maks_paket=MAKS_PAKET_SEKALIGUS,
    )


@student_bp.route("/riwayat")
@student_required
def riwayat():
    user = get_user_by_id(session["user_id"])
    daftar = get_pendaftaran_by_user(user["id"])
    return render_template("student/riwayat.html", user=user, riwayat=daftar,
                            format_rupiah=format_rupiah)
