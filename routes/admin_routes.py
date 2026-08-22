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
)

from models.materi_model import create_material, get_all_materials, get_material, update_material, delete_material, grant_access, revoke_access, get_access_map_for_user
from services.supabase_storage import create_signed_upload
from models.soal_model import create_question, get_questions, get_question, update_question, delete_question

from utils.helpers import (
    format_rupiah
)


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

@admin_bp.route("/siswa/<user_id>/akses-materi", methods=["GET"])
@admin_required
def akses_materi_siswa(user_id):
    siswa = get_user_by_id(user_id)
    if not siswa:
        flash("Data siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.siswa"))
    materi_siswa = [m for m in get_all_materials() if m.get("jenjang")==str(siswa.get("jenjang") or "") and str(m.get("kelas"))==str(siswa.get("kelas") or "")]
    access_map = get_access_map_for_user(user_id)
    for m in materi_siswa:
        m["akses_gratis"] = access_map.get(m["id"], {}).get("source") == "gratis_admin"
    return render_template("admin/akses_materi_siswa.html", siswa=siswa, materi_siswa=materi_siswa)

@admin_bp.route("/siswa/<user_id>/akses-materi/<material_id>", methods=["POST"])
@admin_required
def toggle_akses_materi_siswa(user_id, material_id):
    siswa = get_user_by_id(user_id)
    material = get_material(material_id)
    if not siswa or not material:
        flash("Data siswa atau materi tidak ditemukan.", "danger")
        return redirect(url_for("admin.siswa"))
    aktifkan = request.form.get("aktif") == "on"
    if aktifkan:
        grant_access(user_id, material_id, source="gratis_admin")
        flash(f"Materi \"{material['judul']}\" digratiskan untuk {siswa['name']}.", "success")
    else:
        revoke_access(user_id, material_id)
        flash(f"Akses gratis materi \"{material['judul']}\" untuk {siswa['name']} dicabut.", "info")
    return redirect(url_for("admin.akses_materi_siswa", user_id=user_id))

@admin_bp.route("/materi/upload-url", methods=["POST"])
@admin_required
def materi_upload_url():
    try:
        data=request.get_json(silent=True) or {}
        return create_signed_upload(data.get("filename", ""))
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
            create_material(jenjang,kelas,mapel,request.form.get("judul","").strip(),request.form.get("pdf_url","").strip(),request.form.get("pdf_path","").strip(),request.form.get("pdf_filename","").strip(),request.form.get("ringkasan","").strip())
            flash("Materi PDF berhasil ditambahkan.","success")
        except (ValueError,RuntimeError) as e: flash(str(e),"danger")
        return redirect(url_for("admin.materi"))
    return render_template("admin/materi.html",materials=get_all_materials())

@admin_bp.route("/materi/<material_id>/edit",methods=["GET","POST"])
@admin_required
def edit_materi(material_id):
    material=get_material(material_id)
    if not material: flash("Materi tidak ditemukan.","danger"); return redirect(url_for("admin.materi"))
    if request.method=="POST":
        try:
            pdf_url=request.form.get("pdf_url","").strip() or None; pdf_path=request.form.get("pdf_path","").strip() or None; pdf_filename=request.form.get("pdf_filename","").strip() or None
            update_material(material_id,pdf_url=pdf_url,pdf_path=pdf_path,pdf_filename=pdf_filename,jenjang=request.form.get("jenjang",""),kelas=request.form.get("kelas",""),mapel=request.form.get("mapel","").strip(),judul=request.form.get("judul","").strip(),ringkasan=request.form.get("ringkasan","").strip())
            flash("Materi berhasil diperbarui.","success")
        except (ValueError,RuntimeError) as e: flash(str(e),"danger")
        return redirect(url_for("admin.materi"))
    return render_template("admin/edit_materi.html",material=material)

@admin_bp.route("/materi/<material_id>/hapus",methods=["POST"])
@admin_required
def hapus_materi(material_id):
    delete_material(material_id); flash("Materi dihapus.","info"); return redirect(url_for("admin.materi"))

@admin_bp.route("/soal",methods=["GET","POST"])
@admin_required
def soal():
    if request.method=="POST":
        jenjang=request.form.get("jenjang",""); kelas=request.form.get("kelas",""); mapel=request.form.get("mapel","").strip()
        if not validate_program_item(jenjang, kelas, mapel):
            flash("Jenjang, kelas, atau mata pelajaran tidak sesuai program Binar Cerdas.","danger"); return redirect(url_for("admin.soal"))
        pilihan=[request.form.get("pilihan_a",""),request.form.get("pilihan_b",""),request.form.get("pilihan_c",""),request.form.get("pilihan_d","")]
        create_question(jenjang,kelas,mapel,request.form.get("tipe","latihan"),request.form.get("pertanyaan",""),pilihan,request.form.get("jawaban_benar","A"),request.form.get("penjelasan",""),request.form.get("material_id") or None)
        flash("Soal berhasil ditambahkan.","success"); return redirect(url_for("admin.soal"))
    return render_template("admin/soal.html",questions=get_questions(),materials=get_all_materials())

@admin_bp.route("/soal/<question_id>/hapus",methods=["POST"])
@admin_required
def hapus_soal(question_id): delete_question(question_id); flash("Soal dihapus.","info"); return redirect(url_for("admin.soal"))