"""
SEMUA route di file ini khusus role 'admin' (@admin_required).

Admin BISA:
  - lihat & approve/tolak pendaftaran (termasuk lihat bukti bayar)
  - lihat semua siswa & sisa pertemuan masing-masing
  - MENGURANGI sisa pertemuan siswa (dipakai tiap kali 1 sesi les selesai)
  - kelola jadwal kelas (tambah/hapus)

Ini yang TIDAK ada di sisi siswa: kurangi_pertemuan() hanya dipanggil di
route /admin/siswa/<id>/kurangi, tidak ada endpoint setara di student_routes.py.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.decorators import admin_required
from models.user_model import get_all_siswa, get_user_by_id, tambah_pertemuan, kurangi_pertemuan
from models.registration_model import (
    get_pendaftaran_by_status, get_pendaftaran, proses_pendaftaran,
)
from models.program_model import get_all_schedules, create_schedule, delete_schedule
from utils.helpers import format_rupiah

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    pending = get_pendaftaran_by_status("pending")
    siswa = get_all_siswa()
    return render_template(
        "admin/dashboard.html",
        jumlah_pending=len(pending),
        jumlah_siswa=len(siswa),
        pending_terbaru=pending[:5],
    )


@admin_bp.route("/pendaftaran")
@admin_required
def pendaftaran():
    status = request.args.get("status", "pending")
    daftar = get_pendaftaran_by_status(status)
    return render_template("admin/pendaftaran.html", daftar=daftar, status_aktif=status,
                            format_rupiah=format_rupiah)


@admin_bp.route("/pendaftaran/<reg_id>/setujui", methods=["POST"])
@admin_required
def setujui_pendaftaran(reg_id):
    reg = get_pendaftaran(reg_id)
    if not reg:
        flash("Pendaftaran tidak ditemukan.", "danger")
        return redirect(url_for("admin.pendaftaran"))
    if reg["status"] != "pending":
        flash("Pendaftaran ini sudah diproses sebelumnya.", "warning")
        return redirect(url_for("admin.pendaftaran"))

    # Inti alur approval: setelah admin setuju, baru sisa_pertemuan siswa bertambah.
    tambah_pertemuan(reg["user_id"], reg["total_pertemuan"])
    proses_pendaftaran(reg_id, "approved", admin_id=session["user_id"])
    flash(f"Pendaftaran {reg['user_name']} disetujui. Sisa pertemuan bertambah {reg['total_pertemuan']}.", "success")
    return redirect(url_for("admin.pendaftaran"))


@admin_bp.route("/pendaftaran/<reg_id>/tolak", methods=["POST"])
@admin_required
def tolak_pendaftaran(reg_id):
    reg = get_pendaftaran(reg_id)
    if not reg:
        flash("Pendaftaran tidak ditemukan.", "danger")
        return redirect(url_for("admin.pendaftaran"))
    catatan = request.form.get("catatan", "Bukti pembayaran tidak valid.")
    proses_pendaftaran(reg_id, "ditolak", admin_id=session["user_id"], catatan=catatan)
    flash(f"Pendaftaran {reg['user_name']} ditolak.", "info")
    return redirect(url_for("admin.pendaftaran"))


@admin_bp.route("/siswa")
@admin_required
def siswa():
    daftar = get_all_siswa()
    return render_template("admin/siswa.html", daftar=daftar)


@admin_bp.route("/siswa/<user_id>/kurangi", methods=["POST"])
@admin_required
def kurangi_siswa(user_id):
    """Dipakai admin tiap kali 1 sesi les untuk siswa ini sudah berlangsung."""
    ok, error = kurangi_pertemuan(user_id)
    if not ok:
        flash(error, "danger")
    else:
        flash("Sisa pertemuan dicatat berkurang 1.", "success")
    return redirect(url_for("admin.siswa"))


@admin_bp.route("/jadwal", methods=["GET", "POST"])
@admin_required
def jadwal():
    if request.method == "POST":
        create_schedule(
            jenjang=request.form.get("jenjang"),
            kelas=request.form.get("kelas"),
            mapel=request.form.get("mapel"),
            hari=request.form.get("hari"),
            jam=request.form.get("jam"),
        )
        flash("Jadwal baru ditambahkan.", "success")
        return redirect(url_for("admin.jadwal"))

    semua_jadwal = get_all_schedules()
    return render_template("admin/jadwal.html", jadwal=semua_jadwal)


@admin_bp.route("/jadwal/<schedule_id>/hapus", methods=["POST"])
@admin_required
def hapus_jadwal(schedule_id):
    delete_schedule(schedule_id)
    flash("Jadwal dihapus.", "info")
    return redirect(url_for("admin.jadwal"))
