"""
SEMUA route di file ini khusus
untuk role admin.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from auth.decorators import (
    admin_required
)

from models.user_model import (
    get_all_siswa,
    get_user_by_id,
    tambah_pertemuan,
    kurangi_pertemuan,
    delete_siswa,
)

from models.registration_model import (
    get_pendaftaran_by_status,
    get_pendaftaran,
    proses_pendaftaran,
)

from models.program_model import (
    get_all_schedules,
    create_schedule,
    delete_schedule,
    validate_program_item,
    get_program_map,
)

from models.materi_model import create_material, get_all_materials, get_material, update_material, delete_material, grant_access, revoke_access, get_access_map_for_user, get_progress_for_user, delete_user_material_data, get_subject_groups_for_user
from services.supabase_storage import create_signed_upload
from models.soal_model import create_question, get_questions, get_question, update_question, delete_question, get_all_attempts, get_all_drafts, delete_user_quiz_data

from utils.helpers import (
    format_rupiah, clean_url_param
)

from utils.formatter import parse_numbered_questions, parse_full_mcq


admin_bp = Blueprint(
    "admin",
    __name__
)


@admin_bp.route("/dashboard")
@admin_required
def dashboard():

    pending = (
        get_pendaftaran_by_status(
            "pending"
        )
    )

    siswa = get_all_siswa()

    return render_template(
        "admin/dashboard.html",

        jumlah_pending=len(pending),

        jumlah_siswa=len(siswa),

        pending_terbaru=pending[:5],
        format_rupiah=format_rupiah,
    )


@admin_bp.route("/pendaftaran")
@admin_required
def pendaftaran():

    status = request.args.get(
        "status",
        "pending"
    )

    daftar = (
        get_pendaftaran_by_status(
            status
        )
    )

    return render_template(
        "admin/pendaftaran.html",

        daftar=daftar,

        status_aktif=status,

        format_rupiah=format_rupiah,
    )


@admin_bp.route(
    "/pendaftaran/<reg_id>/setujui",
    methods=["POST"]
)
@admin_required
def setujui_pendaftaran(reg_id):

    reg = get_pendaftaran(
        reg_id
    )

    if not reg:

        flash(
            "Pendaftaran tidak ditemukan.",
            "danger"
        )

        return redirect(
            url_for(
                "admin.pendaftaran"
            )
        )

    if reg["status"] != "pending":

        flash(
            "Pendaftaran ini sudah diproses sebelumnya.",
            "warning"
        )

        return redirect(
            url_for(
                "admin.pendaftaran"
            )
        )

    try:

        sisa_baru = tambah_pertemuan(
            reg["user_id"],
            reg["total_pertemuan"]
        )

    except ValueError as e:

        flash(
            str(e),
            "danger"
        )

        return redirect(
            url_for(
                "admin.pendaftaran"
            )
        )

    proses_pendaftaran(
        reg_id,

        "approved",

        admin_id=session["user_id"]
    )

    flash(
        f"Pembelian {reg['user_name']} "
        f"disetujui. "

        f"Sisa pertemuan sekarang: "
        f"{sisa_baru}.",

        "success"
    )

    return redirect(
        url_for(
            "admin.pendaftaran"
        )
    )


@admin_bp.route(
    "/pendaftaran/<reg_id>/tolak",
    methods=["POST"]
)
@admin_required
def tolak_pendaftaran(reg_id):

    reg = get_pendaftaran(
        reg_id
    )

    if not reg:

        flash(
            "Pendaftaran tidak ditemukan.",
            "danger"
        )

        return redirect(
            url_for(
                "admin.pendaftaran"
            )
        )

    catatan = request.form.get(
        "catatan",
        "Pembayaran tidak dapat diverifikasi."
    )

    proses_pendaftaran(
        reg_id,

        "ditolak",

        admin_id=session["user_id"],

        catatan=catatan
    )

    flash(
        f"Pembelian "
        f"{reg['user_name']} "
        f"ditolak.",

        "info"
    )

    return redirect(
        url_for(
            "admin.pendaftaran"
        )
    )


@admin_bp.route("/siswa")
@admin_required
def siswa():

    daftar = get_all_siswa()

    return render_template(
        "admin/siswa.html",

        daftar=daftar
    )


@admin_bp.route(
    "/siswa/<user_id>/tambah-pertemuan",
    methods=["POST"]
)
@admin_required
def tambah_pertemuan_siswa(user_id):

    try:

        jumlah = int(
            request.form.get(
                "jumlah_pertemuan",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        flash(
            "Jumlah pertemuan harus berupa angka.",
            "danger"
        )

        return redirect(
            url_for(
                "admin.siswa"
            )
        )

    if jumlah <= 0:

        flash(
            "Jumlah pertemuan harus lebih dari 0.",
            "danger"
        )

        return redirect(
            url_for(
                "admin.siswa"
            )
        )

    try:

        sisa_baru = tambah_pertemuan(
            user_id,
            jumlah
        )

        flash(
            f"Pertemuan berhasil ditambahkan. "
            f"Sisa pertemuan sekarang: "
            f"{sisa_baru}.",

            "success"
        )

    except ValueError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "admin.siswa"
        )
    )


@admin_bp.route(
    "/siswa/<user_id>/kurangi",
    methods=["POST"]
)
@admin_required
def kurangi_siswa(user_id):

    ok, error = kurangi_pertemuan(
        user_id
    )

    if not ok:

        flash(
            error,
            "danger"
        )

    else:

        flash(
            "Sisa pertemuan berhasil "
            "dikurangi 1.",

            "success"
        )

    return redirect(
        url_for(
            "admin.siswa"
        )
    )


@admin_bp.route(
    "/siswa/<user_id>/hapus",
    methods=["POST"]
)
@admin_required
def hapus_siswa(user_id):
    """Hapus akun siswa secara permanen, termasuk data akses/progress
    materi dan riwayat pengerjaan soal miliknya. Tindakan ini gak bisa
    dibatalkan, makanya di tombolnya ada konfirmasi dulu."""

    user = get_user_by_id(user_id)
    nama = user.get("name", "Siswa") if user else "Siswa"

    ok, error = delete_siswa(user_id)

    if not ok:
        flash(
            error,
            "danger"
        )

        return redirect(
            url_for(
                "admin.siswa"
            )
        )

    delete_user_material_data(user_id)
    delete_user_quiz_data(user_id)

    flash(
        f"Akun siswa {nama} berhasil dihapus, "
        f"beserta seluruh data akses materi & "
        f"riwayat pengerjaannya.",

        "info"
    )

    return redirect(
        url_for(
            "admin.siswa"
        )
    )


@admin_bp.route(
    "/jadwal",
    methods=["GET", "POST"]
)
@admin_required
def jadwal():

    if request.method == "POST":

        create_schedule(
            jenjang=request.form.get(
                "jenjang"
            ),

            kelas=request.form.get(
                "kelas"
            ),

            mapel=request.form.get(
                "mapel"
            ),

            hari=request.form.get(
                "hari"
            ),

            jam=request.form.get(
                "jam"
            ),
        )

        flash(
            "Jadwal baru ditambahkan.",
            "success"
        )

        return redirect(
            url_for(
                "admin.jadwal"
            )
        )

    semua_jadwal = (
        get_all_schedules()
    )

    return render_template(
        "admin/jadwal.html",

        jadwal=semua_jadwal
    )


@admin_bp.route(
    "/jadwal/<schedule_id>/hapus",
    methods=["POST"]
)
@admin_required
def hapus_jadwal(schedule_id):

    delete_schedule(
        schedule_id
    )

    flash(
        "Jadwal dihapus.",
        "info"
    )

    return redirect(
        url_for(
            "admin.jadwal"
        )
    )

def _admin_time(value):
    if not value:
        return "-"
    try:
        return value.strftime("%d %b %Y, %H:%M:%S")
    except AttributeError:
        return str(value)


def _question_for_attempt(attempt):
    if attempt.get("material_id"):
        return get_questions(material_id=attempt["material_id"], tipe="latihan")
    filters=dict(jenjang=attempt.get("jenjang"),kelas=attempt.get("kelas"),mapel=attempt.get("mapel"),tipe=attempt.get("tipe"))
    if attempt.get("bab"):
        filters["bab"]=attempt.get("bab")
    return get_questions(**filters)


def _build_monitoring_detail(user_id):
    siswa = get_user_by_id(user_id)
    if not siswa:
        return None

    materials = [
        m for m in get_all_materials()
        if m.get("jenjang") == str(siswa.get("jenjang") or "")
        and str(m.get("kelas")) == str(siswa.get("kelas") or "")
    ]
    access_map = get_access_map_for_user(user_id)
    progress_map = get_progress_for_user(user_id)
    for m in materials:
        access = access_map.get(m["id"], {})
        progress = progress_map.get(m["id"], {})
        m["sudah_akses"] = bool(access)
        m["sudah_baca"] = bool(access.get("first_accessed_at"))
        m["selesai"] = bool(progress.get("completed"))
        m["view_count"] = int(access.get("view_count", 0) or 0)
        m["first_accessed_at_text"] = _admin_time(access.get("first_accessed_at"))
        m["last_accessed_at_text"] = _admin_time(access.get("last_accessed_at"))

    attempts = [a for a in get_all_attempts() if a.get("user_id") == user_id]
    for a in attempts:
        a["created_at_text"] = _admin_time(a.get("created_at"))
        a["questions"] = _question_for_attempt(a)
        answers = a.get("answers") or {}
        a["answer_rows"] = []
        for q in a["questions"]:
            selected = answers.get(q["id"], "")
            a["answer_rows"].append({
                "question": q,
                "selected": selected,
                "benar": bool(selected and selected == q.get("jawaban_benar")),
            })

    drafts = [d for d in get_all_drafts() if d.get("user_id") == user_id]
    live_sessions = []
    for d in drafts:
        scope_type = d.get("scope_type")
        scope_key = d.get("scope_key")
        if scope_type not in ("ujian", "latihan"):
            continue
        if scope_type == "ujian":
            raw=str(scope_key or "")
            if raw.startswith("UH__"):
                parts=raw.split("__",2)
                tipe="UH"; mapel=parts[1] if len(parts)>1 else ""; bab=parts[2] if len(parts)>2 else ""
                questions=get_questions(jenjang=siswa.get("jenjang"),kelas=siswa.get("kelas"),mapel=mapel,tipe=tipe,bab=bab)
                label=f"Ulangan Harian · {mapel} · {bab}"
            else:
                parts = raw.split("_", 1)
                tipe = parts[0] if parts else "Ujian"
                mapel = parts[1] if len(parts) > 1 else ""
                questions = get_questions(jenjang=siswa.get("jenjang"),kelas=siswa.get("kelas"),mapel=mapel,tipe=tipe)
                label = f"{tipe} · {mapel}"
        else:
            material = get_material(str(scope_key or ""))
            questions = get_questions(material_id=str(scope_key or ""), tipe="latihan")
            label = f"Latihan · {material.get('judul') if material else scope_key}"
        answers = d.get("answers") or {}
        rows = []
        for q in questions:
            if q["id"] not in answers:
                continue
            h = answers[q["id"]] or {}
            selected = h.get("selected", "")
            rows.append({
                "question": q,
                "selected": selected,
                "benar": bool(h.get("benar")),
                "answered_at": _admin_time(h.get("answered_at")),
            })
        live_sessions.append({
            "scope_type": scope_type,
            "scope_key": scope_key,
            "label": label,
            "answered": len(rows),
            "total": len(questions),
            "updated_at_text": _admin_time(d.get("updated_at")),
            "rows": rows,
        })

    return {
        "siswa": siswa,
        "materials": materials,
        "attempts": attempts,
        "live_sessions": live_sessions,
    }


@admin_bp.route("/monitoring")
@admin_required
def monitoring():
    siswa = get_all_siswa()
    attempts = get_all_attempts()
    drafts = get_all_drafts()
    latest_by_user = {}
    live_by_user = {}
    for a in attempts:
        uid = a.get("user_id")
        if uid and uid not in latest_by_user:
            latest_by_user[uid] = a
    for d in drafts:
        uid = d.get("user_id")
        if uid:
            live_by_user[uid] = live_by_user.get(uid, 0) + len(d.get("answers") or {})
    for s in siswa:
        latest = latest_by_user.get(s["id"])
        s["latest_attempt"] = latest
        s["live_answer_count"] = live_by_user.get(s["id"], 0)
    return render_template("admin/monitoring.html", siswa=siswa)


@admin_bp.route("/monitoring/siswa/<user_id>")
@admin_required
def monitoring_siswa(user_id):
    data = _build_monitoring_detail(user_id)
    if not data:
        flash("Data siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.monitoring"))
    return render_template("admin/monitoring_siswa.html", **data)


@admin_bp.route("/monitoring/siswa/<user_id>/live")
@admin_required
def monitoring_siswa_live(user_id):
    data = _build_monitoring_detail(user_id)
    if not data:
        return jsonify({"error": "Data siswa tidak ditemukan."}), 404
    return jsonify({
        "live_sessions": data["live_sessions"],
        "materials": [
            {
                "id": m["id"],
                "sudah_akses": m["sudah_akses"],
                "sudah_baca": m["sudah_baca"],
                "selesai": m["selesai"],
                "view_count": m["view_count"],
                "last_accessed_at": m["last_accessed_at_text"],
            }
            for m in data["materials"]
        ],
    })


@admin_bp.route("/siswa/<user_id>/akses-materi", methods=["GET"])
@admin_required
def akses_materi_siswa(user_id):
    siswa = get_user_by_id(user_id)
    if not siswa:
        flash("Data siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.siswa"))
    # Dikelompokkan mapel -> bab (bukan per subbab lagi), biar admin cukup
    # sekali toggle buat gratisin satu bab penuh ke siswa ini.
    access_map = get_access_map_for_user(user_id)
    subject_groups = get_subject_groups_for_user(siswa)
    for g in subject_groups:
        for b in g["bab"]:
            total = len(b["subbab"])
            granted = sum(1 for m in b["subbab"] if access_map.get(m["id"], {}).get("source") == "gratis_admin")
            b["total_subbab"] = total
            b["granted_subbab"] = granted
            b["akses_gratis"] = granted == total and total > 0
            b["akses_sebagian"] = 0 < granted < total
    return render_template("admin/akses_materi_siswa.html", siswa=siswa, subject_groups=subject_groups)

@admin_bp.route("/siswa/<user_id>/akses-materi/<mapel>/<bab>", methods=["POST"])
@admin_required
def toggle_akses_bab_siswa(user_id, mapel, bab):
    mapel=clean_url_param(mapel); bab=clean_url_param(bab)
    siswa = get_user_by_id(user_id)
    if not siswa:
        flash("Data siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.siswa"))
    # Ambil semua materi (subbab) yang ada di bab ini buat siswa ini, lalu
    # gratiskan/cabut aksesnya sekaligus semua -- bukan satu-satu subbab.
    materi_bab = [
        m for m in get_all_materials()
        if m.get("jenjang") == str(siswa.get("jenjang") or "")
        and str(m.get("kelas")) == str(siswa.get("kelas") or "")
        and (m.get("mapel") or "Lainnya") == mapel
        and (m.get("bab") or "Bab 1") == bab
    ]
    if not materi_bab:
        flash("Bab tidak ditemukan.", "danger")
        return redirect(url_for("admin.akses_materi_siswa", user_id=user_id))
    aktifkan = request.form.get("aktif") == "on"
    if aktifkan:
        for m in materi_bab:
            grant_access(user_id, m["id"], source="gratis_admin")
        flash(f"Semua materi di \"{bab}\" ({mapel}) digratiskan untuk {siswa['name']}.", "success")
    else:
        for m in materi_bab:
            revoke_access(user_id, m["id"])
        flash(f"Akses gratis \"{bab}\" ({mapel}) untuk {siswa['name']} dicabut.", "info")
    return redirect(url_for("admin.akses_materi_siswa", user_id=user_id))

@admin_bp.route("/materi/upload-url", methods=["POST"])
@admin_required
def materi_upload_url():
    try:
        data=request.get_json(silent=True) or {}
        kind=data.get("kind") or "pdf"
        return create_signed_upload(data.get("filename", ""), kind=kind)
    except (ValueError, RuntimeError) as e:
        return {"error": str(e)}, 400

@admin_bp.route("/materi", methods=["GET","POST"])
@admin_required
def materi():
    if request.method=="POST":
        jenjang=request.form.get("jenjang",""); kelas=request.form.get("kelas",""); mapel=request.form.get("mapel","").strip()
        if not validate_program_item(jenjang,kelas,mapel):
            flash("Jenjang, kelas, atau mata pelajaran tidak sesuai program Binar Cerdas.","danger"); return redirect(url_for("admin.materi"))
        try:
            create_material(jenjang,kelas,mapel,request.form.get("judul","").strip(),request.form.get("pdf_url","").strip(),request.form.get("pdf_path","").strip(),request.form.get("pdf_filename","").strip(),request.form.get("ringkasan","").strip(),request.form.get("bab","Bab 1").strip(),request.form.get("urutan_bab",1),request.form.get("urutan_subbab",1),tipe=request.form.get("tipe","pdf"),rangkuman_gambar_url=request.form.get("rangkuman_gambar_url","").strip() or None,rangkuman_gambar_path=request.form.get("rangkuman_gambar_path","").strip() or None)
            flash("Tahapan materi berhasil ditambahkan.","success")
        except (ValueError,RuntimeError) as e: flash(str(e),"danger")
        return redirect(url_for("admin.materi"))
    return render_template("admin/materi.html",materials=get_all_materials(),program_map=get_program_map())

@admin_bp.route("/materi/<material_id>/edit",methods=["GET","POST"])
@admin_required
def edit_materi(material_id):
    material=get_material(material_id)
    if not material: flash("Materi tidak ditemukan.","danger"); return redirect(url_for("admin.materi"))
    if request.method=="POST":
        try:
            pdf_url=request.form.get("pdf_url","").strip() or None; pdf_path=request.form.get("pdf_path","").strip() or None; pdf_filename=request.form.get("pdf_filename","").strip() or None
            rangkuman_gambar_url=request.form.get("rangkuman_gambar_url","").strip() or None; rangkuman_gambar_path=request.form.get("rangkuman_gambar_path","").strip() or None
            update_material(material_id,pdf_url=pdf_url,pdf_path=pdf_path,pdf_filename=pdf_filename,rangkuman_gambar_url=rangkuman_gambar_url,rangkuman_gambar_path=rangkuman_gambar_path,tipe=request.form.get("tipe","pdf"),jenjang=request.form.get("jenjang",""),kelas=request.form.get("kelas",""),mapel=request.form.get("mapel","").strip(),bab=request.form.get("bab","Bab 1").strip(),urutan_bab=request.form.get("urutan_bab",1),urutan_subbab=request.form.get("urutan_subbab",1),judul=request.form.get("judul","").strip(),ringkasan=request.form.get("ringkasan","").strip())
            flash("Materi berhasil diperbarui.","success")
        except (ValueError,RuntimeError) as e: flash(str(e),"danger")
        return redirect(url_for("admin.materi"))
    return render_template("admin/edit_materi.html",material=material,program_map=get_program_map())

@admin_bp.route("/materi/<material_id>/hapus",methods=["POST"])
@admin_required
def hapus_materi(material_id):
    delete_material(material_id); flash("Materi dihapus.","info"); return redirect(url_for("admin.materi"))

@admin_bp.route("/soal/upload-url", methods=["POST"])
@admin_required
def soal_upload_url():
    try:
        data=request.get_json(silent=True) or {}
        return create_signed_upload(data.get("filename", ""), kind="image")
    except (ValueError, RuntimeError) as e:
        return {"error": str(e)}, 400

@admin_bp.route("/soal",methods=["GET","POST"])
@admin_required
def soal():
    if request.method=="POST":
        jenjang=request.form.get("jenjang",""); kelas=request.form.get("kelas",""); mapel=request.form.get("mapel","").strip()
        if not validate_program_item(jenjang, kelas, mapel):
            flash("Jenjang, kelas, atau mata pelajaran tidak sesuai program Binar Cerdas.","danger"); return redirect(url_for("admin.soal"))
        pilihan=[request.form.get("pilihan_a",""),request.form.get("pilihan_b",""),request.form.get("pilihan_c",""),request.form.get("pilihan_d","")]
        pilihan_gambar=[request.form.get(f"pilihan_{l}_gambar_url","").strip() or None for l in ("a","b","c","d")]
        pilihan_gambar_path=[request.form.get(f"pilihan_{l}_gambar_path","").strip() or None for l in ("a","b","c","d")]
        if any(not (t or g) for t,g in zip(pilihan,pilihan_gambar)):
            flash("Tiap pilihan jawaban harus punya teks atau gambar (boleh salah satu).","danger"); return redirect(url_for("admin.soal"))
        gambar_url=request.form.get("gambar_url","").strip() or None; gambar_path=request.form.get("gambar_path","").strip() or None
        konteks_ai_pilihan=[request.form.get(f"konteks_ai_{l}","").strip() for l in ("a","b","c","d")]
        material_id=request.form.get("material_id") or None
        bab=request.form.get("bab","").strip()
        if material_id and not bab:
            linked=get_material(material_id); bab=(linked or {}).get("bab","")
        create_question(jenjang,kelas,mapel,request.form.get("tipe","latihan"),request.form.get("pertanyaan",""),pilihan,request.form.get("jawaban_benar","A"),request.form.get("penjelasan",""),material_id,gambar_url,gambar_path,pilihan_gambar,pilihan_gambar_path,konteks_ai=request.form.get("konteks_ai","").strip(),konteks_ai_pilihan=konteks_ai_pilihan,bab=bab)
        flash("Soal berhasil ditambahkan.","success"); return redirect(url_for("admin.soal"))
    return render_template("admin/soal.html",questions=_tandai_kelengkapan(get_questions()),materials=get_all_materials(),program_map=get_program_map())

def _tandai_kelengkapan(questions):
    # Tandai tiap soal "lengkap" (semua 4 pilihan sudah ada teks/gambar) atau
    # masih "draft" (misalnya baru diimpor dari teks dan belum diisi jawabannya).
    for q in questions:
        pilihan=q.get("pilihan") or ["","","",""]
        pilihan_gambar=q.get("pilihan_gambar") or [None,None,None,None]
        q["lengkap"]=all((pilihan[i] if i<len(pilihan) else "") or (pilihan_gambar[i] if i<len(pilihan_gambar) else None) for i in range(4))
    return questions

@admin_bp.route("/soal/<question_id>/hapus",methods=["POST"])
@admin_required
def hapus_soal(question_id): delete_question(question_id); flash("Soal dihapus.","info"); return redirect(url_for("admin.soal"))

@admin_bp.route("/soal/<question_id>/edit",methods=["GET","POST"])
@admin_required
def edit_soal(question_id):
    question=get_question(question_id)
    if not question:
        flash("Soal tidak ditemukan.","danger"); return redirect(url_for("admin.soal"))
    if request.method=="POST":
        jenjang=request.form.get("jenjang",""); kelas=request.form.get("kelas",""); mapel=request.form.get("mapel","").strip()
        if not validate_program_item(jenjang, kelas, mapel):
            flash("Jenjang, kelas, atau mata pelajaran tidak sesuai program Binar Cerdas.","danger"); return redirect(url_for("admin.edit_soal",question_id=question_id))
        pilihan=[request.form.get("pilihan_a",""),request.form.get("pilihan_b",""),request.form.get("pilihan_c",""),request.form.get("pilihan_d","")]
        pilihan_gambar=[request.form.get(f"pilihan_{l}_gambar_url","").strip() or None for l in ("a","b","c","d")]
        pilihan_gambar_path=[request.form.get(f"pilihan_{l}_gambar_path","").strip() or None for l in ("a","b","c","d")]
        if any(not (t or g) for t,g in zip(pilihan,pilihan_gambar)):
            flash("Tiap pilihan jawaban harus punya teks atau gambar (boleh salah satu).","danger"); return redirect(url_for("admin.edit_soal",question_id=question_id))
        gambar_url=request.form.get("gambar_url","").strip() or None; gambar_path=request.form.get("gambar_path","").strip() or None
        konteks_ai_pilihan=[request.form.get(f"konteks_ai_{l}","").strip() for l in ("a","b","c","d")]
        material_id=request.form.get("material_id") or None
        bab=request.form.get("bab","").strip()
        if material_id and not bab:
            linked=get_material(material_id); bab=(linked or {}).get("bab","")
        update_question(
            question_id,
            jenjang=jenjang,kelas=kelas,mapel=mapel,
            bab=bab,
            tipe=request.form.get("tipe","latihan"),
            material_id=material_id,
            pertanyaan=request.form.get("pertanyaan",""),
            pilihan=pilihan,
            jawaban_benar=request.form.get("jawaban_benar","A"),
            penjelasan=request.form.get("penjelasan",""),
            konteks_ai=request.form.get("konteks_ai","").strip(),
            konteks_ai_pilihan=konteks_ai_pilihan,
            gambar_url=gambar_url,gambar_path=gambar_path,
            pilihan_gambar=pilihan_gambar,pilihan_gambar_path=pilihan_gambar_path,
        )
        flash("Soal berhasil diperbarui.","success"); return redirect(url_for("admin.soal"))
    return render_template("admin/edit_soal.html",question=question,materials=get_all_materials(),program_map=get_program_map())

@admin_bp.route("/soal/bulk-edit",methods=["POST"])
@admin_required
def bulk_edit_soal():
    """Edit banyak soal sekaligus dari tabel Bank Soal, tapi cuma untuk field
    Mapel, Bab, Tahapan Materi, dan Tipe. Pertanyaan/pilihan/jawaban benar
    sengaja gak bisa diedit rame-rame di sini -- tetap lewat tombol Edit
    satu-satu, biar gak salah pencet pas ngedit banyak baris sekaligus."""
    ids=request.form.getlist("ids")
    diperbarui=0
    for qid in ids:
        question=get_question(qid)
        if not question:
            continue
        mapel=request.form.get(f"mapel_{qid}","").strip() or question.get("mapel")
        if not validate_program_item(question.get("jenjang"),question.get("kelas"),mapel):
            continue
        tipe=request.form.get(f"tipe_{qid}","").strip() or question.get("tipe","latihan")
        material_id=request.form.get(f"material_id_{qid}","").strip() or None
        bab=request.form.get(f"bab_{qid}","").strip()
        if material_id and not bab:
            linked=get_material(material_id); bab=(linked or {}).get("bab","")
        update_question(qid,mapel=mapel,bab=bab,tipe=tipe,material_id=material_id)
        diperbarui+=1
    flash(f"{diperbarui} soal berhasil diperbarui sekaligus.","success")
    return redirect(url_for("admin.soal"))

@admin_bp.route("/soal/impor",methods=["POST"])
@admin_required
def impor_soal():
    jenjang=request.form.get("jenjang",""); kelas=request.form.get("kelas",""); mapel=request.form.get("mapel","").strip()
    if not validate_program_item(jenjang, kelas, mapel):
        flash("Jenjang, kelas, atau mata pelajaran tidak sesuai program Binar Cerdas.","danger"); return redirect(url_for("admin.soal"))
    tipe=request.form.get("tipe","latihan"); material_id=request.form.get("material_id") or None; bab=request.form.get("bab","").strip()
    if material_id and not bab:
        linked=get_material(material_id); bab=(linked or {}).get("bab","")

    mode=request.form.get("mode","sederhana")
    teks=request.form.get("teks_soal","")

    if mode=="lengkap":
        # Mode lengkap: soal + pilihan A-D + jawaban benar diimpor sekaligus.
        # Jenjang/Kelas/Mapel/Tipe/Bab/Tahapan Materi di atas berlaku SAMA
        # buat semua soal yang diimpor di batch ini -- makanya wajib dipilih
        # dulu sebelum impor jalan, biar soal gak nyasar ke kategori yang salah.
        berhasil,gagal=parse_full_mcq(teks)
        if not berhasil and not gagal:
            flash("Gak ada soal yang kebaca dari teks yang ditempel. Cek lagi formatnya (harus ada nomor, pilihan A-D, dan baris JAWABAN).","danger")
            return redirect(url_for("admin.soal"))
        for soal in berhasil:
            create_question(jenjang,kelas,mapel,tipe,soal["pertanyaan"],soal["pilihan"],soal["jawaban_benar"],"",material_id,bab=bab)
        if berhasil:
            pesan=f"{len(berhasil)} soal lengkap (pertanyaan + pilihan + jawaban benar) berhasil diimpor."
        else:
            pesan="Gak ada satupun soal yang berhasil diimpor."
        if gagal:
            detail="; ".join(f"No.{g['nomor']}: {g['alasan']}" for g in gagal)
            pesan+=f" {len(gagal)} soal GAGAL diimpor (gak disimpan, biar gak ada data ngaco) -- {detail}"
            flash(pesan,"warning" if berhasil else "danger")
        else:
            flash(pesan,"success")
        return redirect(url_for("admin.soal"))

    daftar_pertanyaan=parse_numbered_questions(teks)
    if not daftar_pertanyaan:
        flash("Gak ada soal yang kebaca dari teks yang ditempel. Pastikan tiap soal diawali nomor, misal '1. ...', '2. ...'.","danger"); return redirect(url_for("admin.soal"))
    for pertanyaan in daftar_pertanyaan:
        create_question(jenjang,kelas,mapel,tipe,pertanyaan,["","","",""],"A","",material_id,bab=bab)
    flash(f"{len(daftar_pertanyaan)} soal berhasil diimpor. Lengkapi pilihan jawaban tiap soal lewat tombol Edit ya.","success")
    return redirect(url_for("admin.soal"))