"""
Routes fitur "Latihan Soal Live" (gaya Kahoot).

Dua blueprint dalam satu file karena satu fitur, dua sisi:
  - live_admin_bp  (prefix /admin/live) -> admin bikin sesi, isi soal, kontrol jalannya
  - live_student_bp (prefix /siswa/live) -> siswa join pakai kode & jawab soal

Sinkronisasi "live" pakai polling AJAX (bukan WebSocket) -> lihat catatan di
models/live_model.py kenapa. Endpoint /status di kedua sisi sengaja dibuat
ringan (dipanggil tiap ~2 detik oleh browser).
"""
import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

from auth.decorators import admin_required, student_required
from models.user_model import get_user_by_id
from utils.formatter import parse_full_mcq
import models.live_model as live_model

live_admin_bp = Blueprint("live_admin", __name__)
live_student_bp = Blueprint("live_student", __name__)


# ---------------------------------------------------------------- ADMIN ----

@live_admin_bp.route("", methods=["GET", "POST"])
@admin_required
def daftar():
    if request.method == "POST":
        judul = request.form.get("judul", "").strip()
        mapel = request.form.get("mapel", "").strip()
        try:
            durasi = max(5, min(120, int(request.form.get("durasi_detik", 20))))
        except (ValueError, TypeError):
            durasi = 20
        sess = live_model.create_session(session["user_id"], judul, mapel, durasi)
        flash(f"Sesi live dibuat. Kode gabung: {sess['kode']}", "success")
        return redirect(url_for("live_admin.kelola", session_id=sess["id"]))
    sesi_list = live_model.get_sessions_by_admin(session["user_id"])
    return render_template("admin/live_list.html", sesi_list=sesi_list)


def _get_owned_session_or_none(session_id):
    sess = live_model.get_session(session_id)
    if not sess or sess.get("admin_id") != session["user_id"]:
        return None
    return sess


@live_admin_bp.route("/<session_id>")
@admin_required
def kelola(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    peserta = live_model.get_participants(session_id)
    return render_template("admin/live_kelola.html", sesi=sess, peserta=peserta)


@live_admin_bp.route("/<session_id>/soal", methods=["POST"])
@admin_required
def tambah_soal(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    if sess["status"] != live_model.STATUS_LOBI:
        flash("Soal cuma bisa ditambah selagi sesi masih di lobi (belum dimulai).", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    pertanyaan = request.form.get("pertanyaan", "").strip()
    pilihan = [
        request.form.get("pilihan_a", "").strip(),
        request.form.get("pilihan_b", "").strip(),
        request.form.get("pilihan_c", "").strip(),
        request.form.get("pilihan_d", "").strip(),
    ]
    jawaban_benar = request.form.get("jawaban_benar", "A")
    penjelasan = request.form.get("penjelasan", "").strip()
    if not pertanyaan or any(not p for p in pilihan):
        flash("Pertanyaan dan keempat pilihan wajib diisi.", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    live_model.add_question(session_id, pertanyaan, pilihan, jawaban_benar, penjelasan)
    flash("Soal ditambahkan ke sesi live.", "success")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/soal/<question_id>/hapus", methods=["POST"])
@admin_required
def hapus_soal(session_id, question_id):
    sess = _get_owned_session_or_none(session_id)
    if sess and sess["status"] == live_model.STATUS_LOBI:
        live_model.delete_question(session_id, question_id)
        flash("Soal dihapus dari sesi.", "info")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/soal/impor", methods=["POST"])
@admin_required
def impor_soal(session_id):
    """Impor banyak soal sekaligus dari teks yang ditempel (format sama persis
    seperti mode 'Lengkap' di Bank Soal: nomor, pilihan A-D, baris JAWABAN)."""
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    if sess["status"] != live_model.STATUS_LOBI:
        flash("Soal cuma bisa ditambah selagi sesi masih di lobi (belum dimulai).", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    teks = request.form.get("teks_soal", "")
    berhasil, gagal = parse_full_mcq(teks)
    if not berhasil and not gagal:
        flash("Gak ada soal yang kebaca dari teks yang ditempel. Cek lagi formatnya (harus ada nomor, pilihan A-D, dan baris JAWABAN).", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    if berhasil:
        live_model.add_questions_bulk(session_id, berhasil)
        pesan = f"{len(berhasil)} soal berhasil diimpor ke sesi live."
    else:
        pesan = "Gak ada satupun soal yang berhasil diimpor."
    if gagal:
        detail = "; ".join(f"No.{g['nomor']}: {g['alasan']}" for g in gagal)
        pesan += f" {len(gagal)} soal GAGAL diimpor (gak disimpan, biar gak ada data ngaco) -- {detail}"
        flash(pesan, "warning" if berhasil else "danger")
    else:
        flash(pesan, "success")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/mulai", methods=["POST"])
@admin_required
def mulai(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    if not sess.get("questions"):
        flash("Tambahkan minimal 1 soal dulu sebelum mulai.", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    live_model.start_session(session_id)
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/lanjut", methods=["POST"])
@admin_required
def lanjut(session_id):
    sess = _get_owned_session_or_none(session_id)
    if sess:
        live_model.advance_session(session_id)
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/akhiri", methods=["POST"])
@admin_required
def akhiri(session_id):
    sess = _get_owned_session_or_none(session_id)
    if sess:
        live_model.end_session(session_id)
        flash("Sesi live diakhiri.", "info")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/ulang", methods=["POST"])
@admin_required
def ulang(session_id):
    sess = _get_owned_session_or_none(session_id)
    if sess:
        live_model.reset_session(session_id)
        flash("Sesi dikembalikan ke lobi. Skor & jawaban peserta direset.", "info")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/hapus", methods=["POST"])
@admin_required
def hapus(session_id):
    sess = _get_owned_session_or_none(session_id)
    if sess:
        live_model.delete_session(session_id)
        flash("Sesi live dihapus.", "info")
    return redirect(url_for("live_admin.daftar"))


def _sisa_detik(sess):
    if sess["status"] != live_model.STATUS_SOAL or not sess.get("current_started_at"):
        return None
    mulai = sess["current_started_at"]
    # PENTING: Firestore balikin field timestamp sebagai datetime timezone-aware
    # (UTC), sedangkan kalau ditulis pakai datetime.utcnow() dia naive (tanpa
    # tzinfo). Ngurangin naive - aware langsung raise TypeError -> endpoint
    # /status ini jadi 500 PERSIS pas status pindah ke SOAL (abis admin pencet
    # "Mulai") -> polling siswa/admin gagal terus & halaman siswa nyangkut di
    # layar lobi selamanya. Makanya kedua sisi disamain ke aware-UTC dulu.
    if mulai.tzinfo is None:
        mulai = mulai.replace(tzinfo=datetime.timezone.utc)
    sekarang = datetime.datetime.now(datetime.timezone.utc)
    berlalu = (sekarang - mulai).total_seconds()
    return max(0, round(sess.get("durasi_detik", live_model.DURASI_DEFAULT) - berlalu))


def _soal_aktif_publik(sess):
    """Payload soal aktif TANPA jawaban benar (buat ditampilkan ke siswa selagi menjawab)."""
    idx = sess.get("current_index", -1)
    questions = sess.get("questions") or []
    if idx < 0 or idx >= len(questions):
        return None
    q = questions[idx]
    return {"id": q["id"], "pertanyaan": q["pertanyaan"], "pilihan": q["pilihan"], "nomor": idx + 1}


def _soal_aktif_dengan_jawaban(sess):
    idx = sess.get("current_index", -1)
    questions = sess.get("questions") or []
    if idx < 0 or idx >= len(questions):
        return None
    return dict(questions[idx], nomor=idx + 1)


@live_admin_bp.route("/<session_id>/status")
@admin_required
def status(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan."}), 404
    peserta = live_model.get_leaderboard(session_id)
    total_soal = len(sess.get("questions") or [])
    idx = sess.get("current_index", -1)
    soal_aktif = _soal_aktif_dengan_jawaban(sess) if sess["status"] in (live_model.STATUS_SOAL, live_model.STATUS_JEDA) else None
    sudah_jawab = 0
    if soal_aktif:
        sudah_jawab = sum(1 for p in peserta if soal_aktif["id"] in (p.get("jawaban") or {}))
    return jsonify({
        "status": sess["status"],
        "current_index": idx,
        "total_soal": total_soal,
        "sisa_detik": _sisa_detik(sess),
        "soal_aktif": soal_aktif,
        "jumlah_peserta": len(peserta),
        "sudah_jawab": sudah_jawab,
        "leaderboard": [{"nama": p["nama"], "skor": p.get("skor", 0)} for p in peserta[:10]],
    })


# --------------------------------------------------------------- SISWA -----

@live_student_bp.route("/gabung", methods=["GET", "POST"])
@student_required
def gabung():
    if request.method == "POST":
        kode = request.form.get("kode", "").strip().upper()
        sess = live_model.get_session_by_kode(kode)
        if not sess:
            flash("Kode sesi tidak ditemukan. Cek lagi kodenya ya.", "danger")
            return redirect(url_for("live_student.gabung"))
        if sess["status"] == live_model.STATUS_SELESAI:
            flash("Sesi live ini sudah selesai.", "danger")
            return redirect(url_for("live_student.gabung"))
        user = get_user_by_id(session["user_id"])
        live_model.join_session(sess["id"], session["user_id"], user["name"])
        return redirect(url_for("live_student.main", session_id=sess["id"]))
    return render_template("student/live_join.html")


@live_student_bp.route("/<session_id>")
@student_required
def main(session_id):
    sess = live_model.get_session(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_student.gabung"))
    peserta = live_model.get_participant(session_id, session["user_id"])
    if not peserta:
        # belum join (misal buka link langsung) -> join otomatis kalau sesi masih terbuka
        if sess["status"] == live_model.STATUS_SELESAI:
            flash("Sesi live ini sudah selesai.", "danger")
            return redirect(url_for("live_student.gabung"))
        user = get_user_by_id(session["user_id"])
        live_model.join_session(session_id, session["user_id"], user["name"])
    return render_template("student/live_main.html", sesi=sess)


@live_student_bp.route("/<session_id>/status")
@student_required
def status(session_id):
    sess = live_model.get_session(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan."}), 404
    peserta = live_model.get_participant(session_id, session["user_id"])
    if not peserta:
        return jsonify({"error": "Kamu belum join sesi ini."}), 403
    total_soal = len(sess.get("questions") or [])
    soal_publik = _soal_aktif_publik(sess) if sess["status"] == live_model.STATUS_SOAL else None
    sudah_jawab_soal_ini = bool(soal_publik and soal_publik["id"] in (peserta.get("jawaban") or {}))
    hasil_soal_ini = None
    if sess["status"] == live_model.STATUS_JEDA:
        soal = _soal_aktif_dengan_jawaban(sess)
        if soal:
            hasil_soal_ini = {
                "pertanyaan": soal["pertanyaan"],
                "jawaban_benar": soal["jawaban_benar"],
                "penjelasan": soal.get("penjelasan", ""),
                "jawaban_saya": (peserta.get("jawaban") or {}).get(soal["id"]),
            }
    leaderboard = live_model.get_leaderboard(session_id)
    peringkat_saya = next((i + 1 for i, p in enumerate(leaderboard) if p["user_id"] == session["user_id"]), None)
    return jsonify({
        "status": sess["status"],
        "current_index": sess.get("current_index", -1),
        "total_soal": total_soal,
        "sisa_detik": _sisa_detik(sess),
        "soal_aktif": soal_publik,
        "sudah_jawab": sudah_jawab_soal_ini,
        "hasil_soal_ini": hasil_soal_ini,
        "skor_saya": peserta.get("skor", 0),
        "peringkat_saya": peringkat_saya,
        "leaderboard": [{"nama": p["nama"], "skor": p.get("skor", 0)} for p in leaderboard[:10]],
    })


@live_student_bp.route("/<session_id>/jawab", methods=["POST"])
@student_required
def jawab(session_id):
    data = request.get_json(silent=True) or {}
    question_id = str(data.get("question_id", ""))
    selected = str(data.get("selected", ""))[:5]
    waktu_ms = data.get("waktu_ms", 0)
    hasil, error = live_model.submit_answer(session_id, session["user_id"], question_id, selected, waktu_ms)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"ok": True, "hasil": hasil})
