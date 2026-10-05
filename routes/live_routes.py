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
from models.materi_model import get_all_materials
from models.program_model import get_kelas_map
from models.soal_model import get_questions
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
        target_kelas = request.form.get("target_kelas", "").strip()
        try:
            durasi = max(5, min(120, int(request.form.get("durasi_detik", 20))))
        except (ValueError, TypeError):
            durasi = 20
        sess = live_model.create_session(session["user_id"], judul, mapel, durasi, target_kelas)
        flash(f"Kelas hari ini dibuat. Kode gabung: {sess['kode']}", "success")
        return redirect(url_for("live_admin.kelola", session_id=sess["id"]))
    sesi_list = live_model.get_sessions_by_admin(session["user_id"])
    return render_template("admin/live_list.html", sesi_list=sesi_list)


def _get_owned_session_or_none(session_id):
    sess = live_model.get_session(session_id)
    if not sess or sess.get("admin_id") != session["user_id"]:
        return None
    return sess


# Ulangan Harian (UH) itu level Bab, bukan level Tahapan, jadi di Live semua
# soal UH pada bab terpilih dikumpulkan dalam satu kelompok sendiri.
UH_GROUP = "Ulangan Harian Bab"


def _norm(v):
    """Samakan teks buat perbandingan: abaikan spasi ganda & huruf besar/kecil."""
    return " ".join(str(v or "").split()).lower()


def _soal_kelas_mapel_bab(kelas, mapel, bab, **extra_filters):
    """Sumber Live = soal Bank Soal yang tertaut ke *Tahapan Materi*.

    Tahapan soal SELALU diambil dari judul Tahapan Materi yang tertaut lewat
    ``material_id`` (bukan dari kolom ``checkpoint`` yang tersimpan, karena
    kolom itu bisa kosong/basi kalau judul materi diubah atau soal lama), jadi
    tahapan Live = tahapan Materi. Soal cocok dengan Kelas+Mapel+Bab kalau
    field soalnya ATAU materi yang tertaut cocok (dibandingkan tanpa
    membedakan spasi/huruf besar-kecil). Soal tanpa Tahapan Materi tetap
    tidak dimasukkan. Semua tipe soal (Latihan, UH, UTS, UAS) ikut terbaca."""
    if not (kelas and mapel and bab):
        return []
    checkpoint = extra_filters.pop("checkpoint", None)
    materials = {m["id"]: m for m in get_all_materials() if m.get("id")}
    out = []
    for q in get_questions(**extra_filters):
        m = materials.get((q.get("material_id") or "").strip())
        if (q.get("tipe") or "").strip().upper() == "UH":
            cocok_uh = (_norm(q.get("kelas")) == _norm(kelas)
                        and _norm(q.get("mapel")) == _norm(mapel)
                        and _norm(q.get("bab")) == _norm(bab))
            if not cocok_uh and m:
                cocok_uh = (_norm(m.get("kelas")) == _norm(kelas)
                            and _norm(m.get("mapel")) == _norm(mapel)
                            and _norm(m.get("bab")) == _norm(bab))
            if cocok_uh and (not checkpoint or _norm(checkpoint) == _norm(UH_GROUP)):
                q = dict(q)
                q["checkpoint"] = UH_GROUP
                out.append(q)
            continue
        if not m:
            continue
        judul = (m.get("judul") or "").strip()
        if not judul:
            continue
        cocok_soal = (_norm(q.get("kelas")) == _norm(kelas)
                      and _norm(q.get("mapel")) == _norm(mapel)
                      and _norm(q.get("bab")) == _norm(bab))
        cocok_materi = (_norm(m.get("kelas")) == _norm(kelas)
                        and _norm(m.get("mapel")) == _norm(mapel)
                        and _norm(m.get("bab")) == _norm(bab))
        if not (cocok_soal or cocok_materi):
            continue
        if checkpoint and _norm(judul) != _norm(checkpoint):
            continue
        q = dict(q)
        q["checkpoint"] = judul
        out.append(q)
    return out


def _kelompokkan_soal(bank_questions, materials=None):
    """Kelompokkan soal berdasarkan Tahapan Materi resminya, bukan label bebas.
    Urutan mengikuti urutan subbab/tahapan di Materi."""
    by_group = {}
    for q in bank_questions:
        cp = (q.get("checkpoint") or "").strip()
        if not cp:
            continue
        by_group.setdefault(cp, []).append(q)

    order_map = {}
    for m in materials or []:
        if (m.get("judul") or "").strip():
            order_map[m["judul"].strip()] = (int(m.get("urutan_subbab", 1) or 1), str(m.get("judul") or ""))

    groups = []
    for nama, qs in by_group.items():
        groups.append({"nama": nama, "soal": qs, "checkpoint": nama})
    groups.sort(key=lambda g: order_map.get(g["nama"], (999999, g["nama"])))
    # Kelompok Ulangan Harian Bab selalu di paling bawah.
    groups.sort(key=lambda g: g["nama"] == UH_GROUP)
    return groups


@live_admin_bp.route("/<session_id>")
@admin_required
def kelola(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    peserta = live_model.get_participants(session_id)
    kelas_map = get_kelas_map()
    # Cuma dipakai buat daftar nama Bab resmi per Kelas+Mapel (taksonomi),
    # BUKAN buat ditampilkan sebagai materi/PDF ke siswa lagi.
    materials = get_all_materials()
    bank_questions = []
    checkpoints = []
    grouped_questions = []
    if sess.get("quiz_kelas") and sess.get("quiz_mapel") and sess.get("quiz_bab"):
        bank_questions = _soal_kelas_mapel_bab(sess["quiz_kelas"], sess["quiz_mapel"], sess["quiz_bab"])
        stage_materials = [m for m in materials
                           if _norm(m.get("kelas")) == _norm(sess["quiz_kelas"])
                           and _norm(m.get("mapel")) == _norm(sess["quiz_mapel"])
                           and _norm(m.get("bab")) == _norm(sess["quiz_bab"])]
        grup = _kelompokkan_soal(bank_questions, stage_materials)
        grouped_questions = [{"nama": g["nama"], "soal": g["soal"]} for g in grup]
        # Kuis per Tahapan membaca semua tipe soal yang tersedia pada tahapan.
        # Tipe tidak lagi dipaksa menjadi "latihan".
        for g in grup:
            if not g["checkpoint"]:
                continue
            jumlah = len(g["soal"])
            if jumlah:
                checkpoints.append({"nama": g["nama"], "jumlah": jumlah, "checkpoint": g["checkpoint"]})
    return render_template("admin/live_kelola.html", sesi=sess, peserta=peserta,
                           kelas_map=kelas_map, materials=materials, bank_questions=bank_questions,
                           grouped_questions=grouped_questions, checkpoints=checkpoints)

@live_admin_bp.route("/<session_id>/kelas-config", methods=["POST"])
@admin_required
def kelas_config(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    if sess["status"] != live_model.STATUS_LOBI:
        flash("Pengaturan kelas hanya bisa diubah sebelum sesi dimulai.", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    kelas = request.form.get("quiz_kelas", "").strip()
    mapel = request.form.get("quiz_mapel", "").strip()
    bab = request.form.get("quiz_bab", "").strip()
    live_model.set_quiz_source(session_id, kelas, mapel, bab)
    flash("Sumber soal kelas diperbarui.", "success")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/aktifkan-checkpoint", methods=["POST"])
@admin_required
def aktifkan_checkpoint(session_id):
    """'Kuis Cepat' ala Ruang Guru: pengajar lagi menjelaskan, lalu tiba-tiba
    menyalakan kuis singkat untuk SATU bagian/checkpoint yang baru dibahas.
    Soalnya diambil dari Bank Soal (Kelas+Mapel+Bab yang sudah diatur di
    kelas-config) dan harus bertag Tahapan Materi yang sama. Semua tipe soal
    (Latihan, UH, UTS, UAS) tetap terbaca. Urutan soal mengikuti Bank Soal
    dan tidak diacak."""
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan."}), 404
    kelas, mapel, bab = sess.get("quiz_kelas"), sess.get("quiz_mapel"), sess.get("quiz_bab")
    if not (kelas and mapel and bab):
        return jsonify({"error": "Pilih Kelas/Mapel/Bab dulu sebelum menyalakan kuis cepat."}), 400
    checkpoint = (request.form.get("checkpoint") or "").strip()
    if not checkpoint:
        return jsonify({"error": "Bagian/checkpoint wajib dipilih."}), 400
    try:
        jumlah = max(1, min(100, int(request.form.get("jumlah", 3))))
    except (TypeError, ValueError):
        jumlah = 3
    bank = _soal_kelas_mapel_bab(kelas, mapel, bab, checkpoint=checkpoint)
    if not bank:
        return jsonify({"error": f"Belum ada soal untuk bagian '{checkpoint}'."}), 400
    # Urutan bank dipertahankan. Tidak ada pengacakan soal maupun urutan per siswa.
    ambil = bank[:jumlah]
    questions = [{"id": q["id"], "pertanyaan": q.get("pertanyaan", ""),
                  "pilihan": q.get("pilihan") or ["", "", "", ""],
                  "jawaban_benar": q.get("jawaban_benar", "A"),
                  "penjelasan": q.get("penjelasan", "") or "",
                  "gambar_url": q.get("gambar_url")} for q in ambil]
    peserta = live_model.get_participants(session_id)
    target_ids = [p["user_id"] for p in peserta]
    if not target_ids:
        return jsonify({"error": "Belum ada siswa yang join."}), 400
    live_model.activate_checkpoint_quiz(session_id, checkpoint, questions, target_ids, False)
    return jsonify({"ok": True})


@live_admin_bp.route("/<session_id>/atur-kuis", methods=["POST"])
@admin_required
def atur_kuis(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess or sess["status"] != live_model.STATUS_LOBI:
        flash("Pengaturan kuis hanya bisa dilakukan sebelum kelas dimulai.", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    ids = request.form.getlist("question_ids")
    questions = []
    for qid in ids:
        q = __import__("models.soal_model", fromlist=["get_question"]).get_question(qid)
        if q:
            # Simpan snapshot agar perubahan bank soal tidak mengganggu sesi berjalan.
            questions.append({"id": q["id"], "pertanyaan": q.get("pertanyaan",""),
                              "pilihan": q.get("pilihan") or ["","","",""],
                              "jawaban_benar": q.get("jawaban_benar","A"),
                              "penjelasan": q.get("penjelasan","") or "",
                              "gambar_url": q.get("gambar_url")})
    if not questions:
        flash("Pilih minimal satu soal dari latihan/bank soal.", "danger")
        return redirect(url_for("live_admin.kelola", session_id=session_id))
    # Urutan mengikuti urutan soal yang dipilih pengajar. Tidak ada shuffle.
    live_model.set_quiz_questions(session_id, questions)
    live_model.set_quiz_enabled(session_id, False)
    target_ids = request.form.getlist("target_user_ids")
    peserta = live_model.get_participants(session_id)
    if not target_ids or "__all__" in target_ids:
        target_ids = [p["user_id"] for p in peserta]
    assignments = {}
    for uid in target_ids:
        assignments[uid] = [q["id"] for q in questions]
    live_model.set_quiz_assignments(session_id, assignments)
    flash(f"{len(questions)} soal siap digunakan untuk {len(assignments)} siswa.", "success")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/quiz-toggle", methods=["POST"])
@admin_required
def quiz_toggle(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return redirect(url_for("live_admin.daftar"))
    enabled = request.form.get("enabled") == "on"
    if enabled:
        assignments = sess.get("quiz_assignments") or {}
        if sess.get("quiz_question_ids"):
            # Pastikan semua siswa yang sudah join punya assignment. Ini juga
            # menangani siswa yang baru join setelah tombol "Atur kuis" disimpan.
            peserta = live_model.get_participants(session_id)
            order = list(sess.get("quiz_question_ids") or [])
            changed = False
            for p in peserta:
                if p["user_id"] not in assignments:
                    assignments[p["user_id"]] = list(order)
                    changed = True
            if changed:
                live_model.set_quiz_assignments(session_id, assignments)
        if not assignments:
            flash("Belum ada siswa yang join kelas ini, atau soal kuis belum diatur lewat 'Atur kuis'.", "danger")
        else:
            live_model.set_quiz_enabled(session_id, True)
            live_model.start_session(session_id)
            flash("Kuis dinyalakan. Siswa yang ditugaskan akan melihat soal.", "success")
    else:
        live_model.set_quiz_enabled(session_id, False)
        if sess["status"] in (live_model.STATUS_SOAL, live_model.STATUS_JEDA):
            live_model.end_quiz_to_teaching(session_id)
        flash("Kuis dimatikan. Kelas kembali ke mode mengajar.", "info")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/quiz-pause", methods=["POST"])
@admin_required
def quiz_pause(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan."}), 404
    if sess.get("status") != live_model.STATUS_SOAL or not sess.get("quiz_enabled"):
        return jsonify({"error": "Kuis belum aktif."}), 400
    paused = not sess.get("quiz_paused", False)
    live_model.set_quiz_paused(session_id, paused)
    return jsonify({"ok": True, "paused": paused})


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
        live_model.import_questions_to_quiz(session_id, berhasil)
        pesan = f"{len(berhasil)} soal berhasil diimpor dan siap dipakai untuk kuis."
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
    live_model.start_class(session_id)
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
    # Latihan UAS Live tidak dibatasi waktu.
    return None


def _soal_aktif_publik(sess, user_id=None):
    """Soal aktif tanpa kunci. Siswa dapat memiliki urutan acak masing-masing."""
    idx = sess.get("current_index", -1)
    questions = sess.get("questions") or []
    if user_id:
        order=(sess.get("quiz_assignments") or {}).get(user_id)
        if order:
            qid=order[idx] if 0 <= idx < len(order) else None
            q=next((x for x in questions if x.get("id")==qid),None)
            if not q: return None
        else:
            if idx < 0 or idx >= len(questions): return None
            q=questions[idx]
    else:
        if idx < 0 or idx >= len(questions): return None
        q=questions[idx]
    return {"id": q["id"], "pertanyaan": q["pertanyaan"], "pilihan": q["pilihan"], "nomor": idx + 1,
            "gambar_url": q.get("gambar_url")}


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
    sudah_jawab = sum(len(p.get("jawaban") or {}) for p in peserta) if sess.get("status") == live_model.STATUS_SOAL else 0
    questions_by_id = {q.get("id"): q for q in (sess.get("questions") or [])}
    assignments = sess.get("quiz_assignments") or {}
    monitor = []
    for p in peserta:
        order = assignments.get(p.get("user_id")) or list(sess.get("quiz_question_ids") or [])
        answers = p.get("jawaban") or {}
        items = []
        for number, qid in enumerate(order, 1):
            q = questions_by_id.get(qid)
            if not q:
                continue
            a = answers.get(qid) or {}
            if not a:
                status_q = "unanswered"
            elif a.get("benar") is True:
                status_q = "correct"
            else:
                status_q = "wrong"
            items.append({"nomor": number, "id": qid, "status": status_q,
                          "selected": a.get("selected", "") if a else "",
                          "benar": a.get("benar") if a else None})
        terjawab = sum(1 for x in items if x["status"] != "unanswered")
        current_id = p.get("current_question_id") or (order[0] if order else "")
        current_number = next((x["nomor"] for x in items if x["id"] == current_id), None)
        monitor.append({"user_id": p.get("user_id"), "nama": p.get("nama"), "skor": p.get("skor", 0),
                        "terjawab": terjawab, "total": len(items), "current_number": current_number, "soal": items})
    return jsonify({
        "status": sess["status"], "current_index": idx, "total_soal": total_soal,
        "sisa_detik": _sisa_detik(sess), "soal_aktif": None, "jumlah_peserta": len(peserta),
        "sudah_jawab": sudah_jawab,
        "monitor_siswa": monitor,
        "leaderboard": [{"nama": p["nama"], "skor": p.get("skor", 0)} for p in peserta[:10]],
        "mode": sess.get("mode", "mengajar"), "quiz_enabled": sess.get("quiz_enabled", False),
        "active_checkpoint": sess.get("active_checkpoint", ""), "quiz_paused": sess.get("quiz_paused", False),
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
    user = get_user_by_id(session["user_id"])
    kelas_list = live_model.get_today_open_sessions(user.get("kelas") if user else None)
    return render_template("student/live_join.html", kelas_list=kelas_list, kelas_saya=(user or {}).get("kelas"))


@live_student_bp.route("/masuk/<session_id>", methods=["POST"])
@student_required
def masuk_langsung(session_id):
    """Gabung ke 'Kelas Hari Ini' langsung dari daftar (tanpa ketik kode)."""
    sess = live_model.get_session(session_id)
    if not sess or sess["status"] == live_model.STATUS_SELESAI:
        flash("Kelas ini sudah tidak tersedia.", "danger")
        return redirect(url_for("live_student.gabung"))
    user = get_user_by_id(session["user_id"])
    live_model.join_session(sess["id"], session["user_id"], user["name"])
    return redirect(url_for("live_student.main", session_id=sess["id"]))


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
    order = (sess.get("quiz_assignments") or {}).get(session["user_id"]) or []
    if not order and sess.get("quiz_question_ids"):
        order = list(sess.get("quiz_question_ids") or [])
    questions_by_id = {q.get("id"): q for q in (sess.get("questions") or [])}
    answered = peserta.get("jawaban") or {}
    public_questions = []
    for i, qid in enumerate(order):
        q = questions_by_id.get(qid)
        if not q:
            continue
        public_questions.append({
            "id": qid, "nomor": i + 1, "pertanyaan": q.get("pertanyaan", ""),
            "pilihan": q.get("pilihan") or ["", "", "", ""],
            "gambar_url": q.get("gambar_url"), "sudah_jawab": qid in answered,
            "hasil": answered.get(qid)
        })
    current_id = peserta.get("current_question_id") or (order[0] if order else "")
    if current_id and current_id not in order:
        current_id = order[0] if order else ""
    current = next((q for q in public_questions if q["id"] == current_id), None)
    if current and current.get("hasil"):
        qraw = questions_by_id.get(current_id) or {}
        current["hasil"] = dict(current["hasil"], jawaban_benar=str(qraw.get("jawaban_benar") or "").strip().upper()[:1])
    leaderboard = live_model.get_leaderboard(session_id)
    peringkat_saya = next((i + 1 for i, p in enumerate(leaderboard) if p["user_id"] == session["user_id"]), None)
    return jsonify({
        "status": sess["status"],
        "current_index": next((i for i,q in enumerate(public_questions) if q["id"] == current_id), 0) if public_questions else -1,
        "current_question_id": current_id,
        "total_soal": len(public_questions),
        "sisa_detik": None,
        "soal_aktif": current if sess["status"] == live_model.STATUS_SOAL else None,
        "soal_list": public_questions if sess["status"] == live_model.STATUS_SOAL else [],
        "sudah_jawab": bool(current and current.get("sudah_jawab")),
        "hasil_soal_ini": answered.get(current_id),
        "skor_saya": peserta.get("skor", 0),
        "peringkat_saya": peringkat_saya,
        "jumlah_terjawab": sum(1 for qid in order if qid in answered),
        "leaderboard": [{"nama": p["nama"], "skor": p.get("skor", 0)} for p in leaderboard[:10]],
        "mode": sess.get("mode", "mengajar"),
        "quiz_enabled": sess.get("quiz_enabled", False),
        "quiz_paused": sess.get("quiz_paused", False),
        "active_checkpoint": sess.get("active_checkpoint", ""),
        "quiz_allowed": session["user_id"] in (sess.get("quiz_assignments") or {}) or bool(sess.get("quiz_question_ids"))
    })


@live_student_bp.route("/<session_id>/pilih-soal", methods=["POST"])
@student_required
def pilih_soal(session_id):
    data = request.get_json(silent=True) or {}
    question_id = str(data.get("question_id", ""))
    hasil, error = live_model.set_current_question(session_id, session["user_id"], question_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"ok": True, "current_question_id": question_id})


@live_student_bp.route("/<session_id>/jawab", methods=["POST"])
@student_required
def jawab(session_id):
    data = request.get_json(silent=True) or {}
    question_id = str(data.get("question_id", ""))
    selected = str(data.get("selected", ""))[:5]
    hasil, error = live_model.submit_answer(session_id, session["user_id"], question_id, selected, 0)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"ok": True, "hasil": hasil})