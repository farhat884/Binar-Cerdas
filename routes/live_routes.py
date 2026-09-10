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
from models.materi_model import get_all_materials, get_material
from models.soal_model import get_questions
import random
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


def _soal_bab_materi(m, **extra_filters):
    """Soal yang match mapel+bab materi ATAU tertaut langsung lewat
    material_id -- digabung (union) tanpa dobel. Perlu supaya soal yang
    ditautkan ke materi tapi field bab-nya sempat berubah tetap kebaca."""
    by_bab = get_questions(mapel=m.get("mapel"), bab=m.get("bab"), **extra_filters)
    by_material = get_questions(material_id=m.get("id"), **extra_filters) if m.get("id") else []
    seen = set()
    out = []
    for q in by_bab + by_material:
        if q["id"] not in seen:
            seen.add(q["id"]); out.append(q)
    return out


def _kelompokkan_soal(bank_questions, materi_by_id):
    """Kelompokkan soal buat ditampilkan: pakai label Checkpoint kalau diisi,
    kalau kosong jatuh balik ke nama 'Tahapan Materi' yang ditautkan lewat
    material_id (kolom "Tahapan Materi" pas nambah soal) -- ini yang paling
    sering keisi, jadi soal gak nyasar semua ke 'Tanpa tahapan' cuma karena
    Checkpoint (field lain, opsional) belum diisi. Tiap grup dikasih tahu asal
    labelnya (checkpoint asli atau tahapan materi) supaya "Kuis Cepat" bisa
    nembak soal yang benar walau grupnya dari fallback."""
    by_group, group_urutan, group_checkpoint, group_tahapan_id = {}, {}, {}, {}
    for q in bank_questions:
        cp = (q.get("checkpoint") or "").strip()
        if cp:
            nama, urutan, real_cp, tahapan_id = cp, 0, cp, None
        else:
            mat_q = materi_by_id.get(q.get("material_id"))
            if mat_q:
                nama, urutan, real_cp, tahapan_id = mat_q["judul"], mat_q.get("urutan_subbab", 1), None, mat_q["id"]
            else:
                nama, urutan, real_cp, tahapan_id = "Tanpa tahapan", 999, None, None
        by_group.setdefault(nama, []).append(q)
        group_urutan.setdefault(nama, urutan)
        group_checkpoint.setdefault(nama, real_cp)
        group_tahapan_id.setdefault(nama, tahapan_id)
    tanpa = by_group.pop("Tanpa tahapan", [])
    grup = [{"nama": nama, "soal": qs, "checkpoint": group_checkpoint[nama], "tahapan_id": group_tahapan_id[nama]}
            for nama, qs in sorted(by_group.items(), key=lambda kv: (group_urutan[kv[0]], kv[0]))]
    if tanpa:
        grup.append({"nama": "Tanpa tahapan", "soal": tanpa, "checkpoint": None, "tahapan_id": None})
    return grup


@live_admin_bp.route("/<session_id>")
@admin_required
def kelola(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    peserta = live_model.get_participants(session_id)
    materials = get_all_materials()
    bank_questions = []
    checkpoints = []
    grouped_questions = []
    materi_terpilih = None
    if sess.get("material_id"):
        m = get_material(sess["material_id"])
        if m:
            materi_terpilih = m
            # Gabungkan soal yang match mapel+bab DENGAN soal yang tertaut
            # langsung lewat material_id (kalau bab-nya sempat diubah nama
            # setelah soal dibuat, soal itu tetap kebaca lewat material_id).
            bank_questions = _soal_bab_materi(m)
            materi_by_id = {mm["id"]: mm for mm in materials}
            grup = _kelompokkan_soal(bank_questions, materi_by_id)
            grouped_questions = [{"nama": g["nama"], "soal": g["soal"]} for g in grup]
            # "Kuis Cepat": cuma grup yang punya identitas (checkpoint asli ATAU
            # tahapan materi), dan cuma hitung soal tipe "latihan" -- soal
            # UH/UTS/UAS gak dipakai buat kuis dadakan ala Ruang Guru ini.
            for g in grup:
                if not (g["checkpoint"] or g["tahapan_id"]):
                    continue
                jumlah = len([q for q in g["soal"] if (q.get("tipe") or "latihan") == "latihan"])
                if jumlah:
                    checkpoints.append({"nama": g["nama"], "jumlah": jumlah,
                                         "checkpoint": g["checkpoint"], "tahapan_id": g["tahapan_id"]})
    return render_template("admin/live_kelola.html", sesi=sess, peserta=peserta,
                           materials=materials, bank_questions=bank_questions,
                           grouped_questions=grouped_questions, materi_terpilih=materi_terpilih,
                           checkpoints=checkpoints)

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
    material_id = request.form.get("material_id", "").strip() or None
    live_model.configure_class(session_id, material_id)
    flash("Materi kelas diperbarui.", "success")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/izin-coret", methods=["POST"])
@admin_required
def izin_coret(session_id):
    """Pengajar pilih sendiri siapa yang boleh mencoret di papan tulis --
    bisa diubah kapan saja selagi kelas berjalan, bukan cuma di lobi."""
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        flash("Sesi live tidak ditemukan.", "danger")
        return redirect(url_for("live_admin.daftar"))
    ids = request.form.getlist("draw_user_ids")
    live_model.set_draw_allowed(session_id, ids)
    if ids:
        flash(f"{len(ids)} siswa sekarang boleh mencoret di papan tulis.", "success")
    else:
        flash("Izin mencoret dicabut dari semua siswa.", "info")
    return redirect(url_for("live_admin.kelola", session_id=session_id))


@live_admin_bp.route("/<session_id>/ganti-materi", methods=["POST"])
@admin_required
def ganti_materi(session_id):
    """Pindah tahapan/materi yang tampil DI TENGAH kelas berlangsung, gaya
    ganti slide presentasi ke bab/tahapan berikutnya. Beda dari kelas-config
    di atas (yang cuma bisa dipakai sebelum kelas mulai)."""
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan."}), 404
    material_id = (request.form.get("material_id") or "").strip() or None
    live_model.set_material_live(session_id, material_id)
    return jsonify({"ok": True})


@live_admin_bp.route("/<session_id>/halaman", methods=["POST"])
@admin_required
def halaman(session_id):
    """Kontrol halaman materi gaya presentasi: next/prev. Siswa ikut pindah
    otomatis lewat polling /status. Bisa dipanggil kapan saja selama kelas
    berjalan, gak dibatasi cuma pas lobi seperti pengaturan lain."""
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan."}), 404
    if request.form.get("page") is not None:
        live_model.set_page(session_id, request.form.get("page"))
    else:
        live_model.step_page(session_id, request.form.get("delta", 1))
    return jsonify({"ok": True, "current_page": live_model.get_session(session_id)["current_page"]})


@live_admin_bp.route("/<session_id>/aktifkan-checkpoint", methods=["POST"])
@admin_required
def aktifkan_checkpoint(session_id):
    """'Kuis Cepat' ala Ruang Guru: pengajar lagi menjelaskan, lalu tiba-tiba
    menyalakan kuis singkat untuk SATU bagian/checkpoint yang baru dibahas.
    Soalnya diambil ACAK dari bank soal bertag checkpoint yang sama, jadi
    setiap dinyalakan (walau bagiannya sama) soal yang keluar bisa beda --
    tapi jenis/temanya tetap sama. Bisa dipanggil kapan saja saat 'mengajar',
    tanpa perlu balik ke lobi dulu."""
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan."}), 404
    if not sess.get("material_id"):
        return jsonify({"error": "Pilih materi/tahapan dulu sebelum menyalakan kuis cepat."}), 400
    m = get_material(sess["material_id"])
    if not m:
        return jsonify({"error": "Materi tidak ditemukan."}), 404
    checkpoint = (request.form.get("checkpoint") or "").strip()
    tahapan_id = (request.form.get("tahapan_id") or "").strip()
    if not checkpoint and not tahapan_id:
        return jsonify({"error": "Bagian/checkpoint wajib dipilih."}), 400
    try:
        jumlah = max(1, min(20, int(request.form.get("jumlah", 3))))
    except (TypeError, ValueError):
        jumlah = 3
    acak_per_siswa = request.form.get("acak_per_siswa", "on") == "on"
    if checkpoint:
        bank = _soal_bab_materi(m, tipe="latihan", checkpoint=checkpoint)
        label = checkpoint
    else:
        # Grup ini bukan dari Checkpoint asli, tapi fallback ke Tahapan Materi
        # -- ambil soal yang tertaut ke tahapan itu DAN belum diberi checkpoint
        # (yang sudah punya checkpoint sendiri sudah masuk grup checkpoint-nya).
        # Query langsung (bukan lewat _soal_bab_materi) supaya gak dobel kirim
        # material_id -- di sini material_id yang dipakai adalah tahapan_id,
        # bukan material_id sesi secara keseluruhan.
        bank = [q for q in get_questions(mapel=m.get("mapel"), bab=m.get("bab"), tipe="latihan", material_id=tahapan_id)
                if not (q.get("checkpoint") or "").strip()]
        mat_tahapan = get_material(tahapan_id)
        label = mat_tahapan["judul"] if mat_tahapan else tahapan_id
    if not bank:
        return jsonify({"error": f"Belum ada soal untuk bagian '{label}'."}), 400
    ambil = random.sample(bank, min(jumlah, len(bank)))
    random.shuffle(ambil)
    questions = [{"id": q["id"], "pertanyaan": q.get("pertanyaan", ""),
                  "pilihan": q.get("pilihan") or ["", "", "", ""],
                  "jawaban_benar": q.get("jawaban_benar", "A"),
                  "penjelasan": q.get("penjelasan", "") or "",
                  "gambar_url": q.get("gambar_url")} for q in ambil]
    peserta = live_model.get_participants(session_id)
    target_ids = [p["user_id"] for p in peserta]
    if not target_ids:
        return jsonify({"error": "Belum ada siswa yang join."}), 400
    live_model.activate_checkpoint_quiz(session_id, checkpoint or label, questions, target_ids, acak_per_siswa)
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
    if request.form.get("acak_soal") == "on":
        random.shuffle(questions)
    live_model.set_quiz_questions(session_id, questions)
    live_model.set_quiz_enabled(session_id, False)
    target_ids = request.form.getlist("target_user_ids")
    peserta = live_model.get_participants(session_id)
    if not target_ids or "__all__" in target_ids:
        target_ids = [p["user_id"] for p in peserta]
    assignments = {}
    per_student = request.form.get("acak_per_siswa") == "on"
    for uid in target_ids:
        order = [q["id"] for q in questions]
        if per_student:
            random.shuffle(order)
        assignments[uid] = order
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
        if not assignments:
            flash("Belum ada siswa/soal yang ditentukan untuk kuis.", "danger")
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


@live_admin_bp.route("/<session_id>/drawing", methods=["POST"])
@admin_required
def drawing(session_id):
    sess = _get_owned_session_or_none(session_id)
    if not sess:
        return jsonify({"error":"Sesi tidak ditemukan"}), 404
    data=request.get_json(silent=True) or {}
    if data.get("clear"):
        live_model.clear_drawing(session_id)
    elif data.get("stroke"):
        live_model.add_drawing_stroke(session_id, data["stroke"])
    return jsonify({"ok": True})


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
    if sess["status"] != live_model.STATUS_SOAL or not sess.get("current_started_at"):
        return None
    mulai = sess["current_started_at"]
    if isinstance(mulai, str):
        try:
            mulai = datetime.datetime.fromisoformat(mulai.replace("Z", "+00:00"))
        except ValueError:
            return 0
    if mulai.tzinfo is None:
        mulai = mulai.replace(tzinfo=datetime.timezone.utc)
    sekarang = datetime.datetime.now(datetime.timezone.utc)
    berlalu = (sekarang - mulai).total_seconds()
    return max(0, round(sess.get("durasi_detik", live_model.DURASI_DEFAULT) - berlalu))


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
    soal_aktif = _soal_aktif_dengan_jawaban(sess) if sess["status"] in (live_model.STATUS_SOAL, live_model.STATUS_JEDA) else None
    sudah_jawab = 0
    if soal_aktif:
        sudah_jawab = sum(1 for p in peserta if soal_aktif["id"] in (p.get("jawaban") or {}))
    mat = get_material(sess.get("material_id")) if sess.get("material_id") else None
    return jsonify({
        "status": sess["status"],
        "material": {"id": mat["id"], "judul": mat.get("judul"), "tipe": mat.get("tipe"), "pdf_url": mat.get("pdf_url"), "rangkuman_gambar_url": mat.get("rangkuman_gambar_url"), "ringkasan": mat.get("ringkasan","")} if mat else None,
        "current_index": idx,
        "total_soal": total_soal,
        "sisa_detik": _sisa_detik(sess),
        "soal_aktif": soal_aktif,
        "jumlah_peserta": len(peserta),
        "sudah_jawab": sudah_jawab,
        "leaderboard": [{"nama": p["nama"], "skor": p.get("skor", 0)} for p in peserta[:10]],
        "mode": sess.get("mode", "mengajar"), "material_id": sess.get("material_id"),
        "drawing": sess.get("drawing") or [], "draw_allowed_ids": sess.get("draw_allowed_ids") or [],
        "quiz_enabled": sess.get("quiz_enabled", False),
        "current_page": sess.get("current_page", 1), "active_checkpoint": sess.get("active_checkpoint", ""),
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
    total_soal = len(sess.get("questions") or [])
    soal_publik = _soal_aktif_publik(sess, session["user_id"]) if sess["status"] == live_model.STATUS_SOAL else None
    sudah_jawab_soal_ini = bool(soal_publik and soal_publik["id"] in (peserta.get("jawaban") or {}))
    hasil_soal_ini = None
    if sess["status"] == live_model.STATUS_JEDA and session["user_id"] in (sess.get("quiz_assignments") or {}):
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
    mat = get_material(sess.get("material_id")) if sess.get("material_id") else None
    return jsonify({
        "status": sess["status"],
        "material": {"id": mat["id"], "judul": mat.get("judul"), "tipe": mat.get("tipe"), "pdf_url": mat.get("pdf_url"), "rangkuman_gambar_url": mat.get("rangkuman_gambar_url"), "ringkasan": mat.get("ringkasan","")} if mat else None,
        "current_index": sess.get("current_index", -1),
        "total_soal": total_soal,
        "sisa_detik": _sisa_detik(sess),
        "soal_aktif": soal_publik,
        "sudah_jawab": sudah_jawab_soal_ini,
        "hasil_soal_ini": hasil_soal_ini,
        "skor_saya": peserta.get("skor", 0),
        "peringkat_saya": peringkat_saya,
        "leaderboard": [{"nama": p["nama"], "skor": p.get("skor", 0)} for p in leaderboard[:10]],
        "mode": sess.get("mode", "mengajar"), "material_id": sess.get("material_id"),
        "drawing": sess.get("drawing") or [], "student_draw_enabled": session["user_id"] in (sess.get("draw_allowed_ids") or []),
        "quiz_enabled": sess.get("quiz_enabled", False),
        "current_page": sess.get("current_page", 1), "active_checkpoint": sess.get("active_checkpoint", ""),
        "quiz_allowed": session["user_id"] in (sess.get("quiz_assignments") or {})    })


@live_student_bp.route("/<session_id>/drawing", methods=["POST"])
@student_required
def student_drawing(session_id):
    sess = live_model.get_session(session_id)
    if not sess:
        return jsonify({"error":"Sesi tidak ditemukan"}), 404
    if session["user_id"] not in (sess.get("draw_allowed_ids") or []):
        return jsonify({"error":"Pengajar belum mengizinkan kamu mencoret."}), 403
    data=request.get_json(silent=True) or {}
    if data.get("stroke"):
        live_model.add_drawing_stroke(session_id, data["stroke"])
    return jsonify({"ok": True})

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