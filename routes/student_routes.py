from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from auth.decorators import student_required
from models.user_model import get_user_by_id, gunakan_pertemuan_untuk_materi
from models.program_model import get_all_schedules
from models.registration_model import buat_pendaftaran,get_pendaftaran_by_user,HARGA_PER_PAKET,PERTEMUAN_PER_PAKET,MAKS_PAKET_SEKALIGUS
from models.materi_model import get_materials_for_user,get_material,has_access,grant_access,mark_progress,get_progress_for_user
from models.soal_model import get_questions,get_question,save_attempt,get_attempts
from services.ai_service import explain_answer,tanya_lanjutan
from utils.helpers import format_rupiah
student_bp=Blueprint("student",__name__)

def _user(): return get_user_by_id(session["user_id"])

def _sidebar_user(): return _user()

@student_bp.route("/dashboard")
@student_required
def dashboard():
    user=_user(); riwayat=get_pendaftaran_by_user(user["id"])[:5]
    materials=get_materials_for_user(user); progress=get_progress_for_user(user["id"])
    completed=sum(1 for x in progress.values() if x.get("completed")); total=len(materials)
    return render_template("student/dashboard.html",user=user,riwayat=riwayat,material_count=total,material_completed=completed)

@student_bp.route("/jadwal")
@student_required
def jadwal(): return render_template("student/jadwal.html",user=_user(),jadwal=get_all_schedules())

@student_bp.route("/daftar-les",methods=["GET","POST"])
@student_required
def daftar_les():
    user=_user()
    if request.method=="POST":
        try: jumlah=max(1,min(int(request.form.get("jumlah_paket",1)),MAKS_PAKET_SEKALIGUS))
        except (ValueError,TypeError): jumlah=1
        metode=request.form.get("metode_pembayaran","").strip(); nama=request.form.get("nama_pengirim","").strip(); tanggal=request.form.get("tanggal_transfer","").strip(); ref=request.form.get("referensi_transfer","").strip()
        if metode not in {"Transfer BCA","QRIS"}: flash("Pilih metode pembayaran yang tersedia.","danger"); return redirect(url_for("student.daftar_les"))
        if not all([nama,tanggal,ref]): flash("Lengkapi data pembayaran terlebih dahulu.","danger"); return redirect(url_for("student.daftar_les"))
        buat_pendaftaran(user["id"],user["name"],jumlah,metode,nama,tanggal,ref)
        flash("Pembelian paket berhasil dikirim! Menunggu persetujuan admin.","success"); return redirect(url_for("student.riwayat"))
    return render_template("student/daftar_les.html",user=user,harga_per_paket=HARGA_PER_PAKET,pertemuan_per_paket=PERTEMUAN_PER_PAKET,maks_paket=MAKS_PAKET_SEKALIGUS)

@student_bp.route("/riwayat")
@student_required
def riwayat():
    user=_user(); return render_template("student/riwayat.html",user=user,riwayat=get_pendaftaran_by_user(user["id"]),format_rupiah=format_rupiah)

@student_bp.route("/materi")
@student_required
def materi():
    user=_user(); mats=get_materials_for_user(user); progress=get_progress_for_user(user["id"])
    for m in mats: m["can_access"]=has_access(user,m["id"]); m["progress"]=progress.get(m["id"],{})
    return render_template("student/materi.html",user=user,materials=mats)

@student_bp.route("/materi/<material_id>")
@student_required
def detail_materi(material_id):
    user=_user(); material=get_material(material_id)
    if not material: flash("Materi tidak ditemukan.","danger"); return redirect(url_for("student.materi"))
    if material["jenjang"]!=str(user.get("jenjang")) or str(material["kelas"])!=str(user.get("kelas")): flash("Materi ini bukan untuk jenjang atau kelas kamu.","danger"); return redirect(url_for("student.materi"))
    allowed=has_access(user,material_id); latihan=get_questions(material_id=material_id,tipe="latihan")
    return render_template("student/detail_materi.html",user=user,material=material,allowed=allowed,latihan=latihan)

@student_bp.route("/materi/<material_id>/buka",methods=["POST"])
@student_required
def buka_materi(material_id):
    user=_user(); material=get_material(material_id)
    if not material: flash("Materi tidak ditemukan.","danger"); return redirect(url_for("student.materi"))
    if material.get("jenjang") != str(user.get("jenjang")) or str(material.get("kelas")) != str(user.get("kelas")):
        flash("Materi ini bukan untuk kelas kamu.","danger"); return redirect(url_for("student.materi"))
    if has_access(user,material_id): return redirect(url_for("student.detail_materi",material_id=material_id))
    try: sisa=gunakan_pertemuan_untuk_materi(user["id"]); grant_access(user["id"],material_id,"kuota"); flash(f"Akses materi berhasil dibuka. Sisa pertemuan: {sisa}.","success")
    except ValueError as e: flash(str(e),"danger")
    return redirect(url_for("student.detail_materi",material_id=material_id))

@student_bp.route("/materi/<material_id>/selesai",methods=["POST"])
@student_required
def selesai_materi(material_id):
    user=_user();
    if not has_access(user,material_id): flash("Buka akses materi terlebih dahulu.","danger"); return redirect(url_for("student.detail_materi",material_id=material_id))
    mark_progress(user["id"],material_id,True); flash("Materi ditandai selesai. Bagus! 🎉","success"); return redirect(url_for("student.detail_materi",material_id=material_id))

@student_bp.route("/latihan/<question_id>/jawab",methods=["POST"])
@student_required
def jawab_latihan(question_id):
    user=_user(); q=get_question(question_id)
    if not q: flash("Soal tidak ditemukan.","danger"); return redirect(url_for("student.materi"))
    if q.get("material_id") and not has_access(user,q.get("material_id")):
        flash("Buka akses materi terlebih dahulu.","danger"); return redirect(url_for("student.materi"))
    selected=request.form.get("jawaban",""); benar=selected==q.get("jawaban_benar")
    ai=explain_answer(q["pertanyaan"],selected,q["jawaban_benar"],q.get("penjelasan",""),benar=benar)
    return render_template("student/hasil_jawaban.html",user=user,question=q,selected=selected,benar=benar,penjelasan_ai=ai)

@student_bp.route("/soal/<question_id>/tanya-ai",methods=["POST"])
@student_required
def tanya_ai_soal(question_id):
    user=_user(); q=get_question(question_id)
    if not q: return jsonify({"error":"Soal tidak ditemukan."}),404
    if q.get("material_id") and not has_access(user,q.get("material_id")):
        return jsonify({"error":"Kamu belum punya akses ke materi ini."}),403
    data=request.get_json(silent=True) or {}
    pesan=str(data.get("pesan","")).strip()
    if not pesan: return jsonify({"error":"Pertanyaan gak boleh kosong."}),400
    if len(pesan)>500: return jsonify({"error":"Pertanyaannya kepanjangan, coba diringkas ya."}),400
    selected=str(data.get("selected",""))[:200]
    benar=selected==q.get("jawaban_benar")
    riwayat_mentah=data.get("riwayat") or []
    riwayat=[m for m in riwayat_mentah if isinstance(m,dict)][-8:]
    balasan=tanya_lanjutan(q["pertanyaan"],selected,q["jawaban_benar"],benar,riwayat,pesan)
    return jsonify({"balasan":balasan})

@student_bp.route("/ujian/<tipe>/<mapel>",methods=["GET","POST"])
@student_required
def ujian(tipe,mapel):
    tipe=tipe.upper(); user=_user()
    if tipe not in {"UTS","UAS"}: flash("Jenis latihan tidak valid.","danger"); return redirect(url_for("student.materi"))
    questions=get_questions(jenjang=user.get("jenjang"),kelas=user.get("kelas"),mapel=mapel,tipe=tipe)
    if request.method=="POST":
        answers={q["id"]:request.form.get("q_"+q["id"],"") for q in questions}; score=sum(1 for q in questions if answers[q["id"]]==q.get("jawaban_benar")); attempt=save_attempt(user["id"],tipe,user.get("jenjang"),user.get("kelas"),mapel,score,len(questions),answers)
        reviews=[]
        for q in questions:
            selected=answers.get(q["id"],""); benar=selected==q.get("jawaban_benar")
            ai=explain_answer(q["pertanyaan"],selected,q["jawaban_benar"],q.get("penjelasan",""),benar=benar)
            reviews.append({"question":q,"selected":selected,"benar":benar,"penjelasan_ai":ai})
        return render_template("student/hasil_ujian.html",user=user,attempt=attempt,questions=questions,answers=answers,reviews=reviews)
    return render_template("student/ujian.html",user=user,tipe=tipe,mapel=mapel,questions=questions)

@student_bp.route("/progress")
@student_required
def progress():
    user=_user(); mats=get_materials_for_user(user); prog=get_progress_for_user(user["id"]); attempts=get_attempts(user["id"])
    per_mapel={}
    for m in mats:
        x=per_mapel.setdefault(m["mapel"],{"total":0,"selesai":0}); x["total"]+=1; x["selesai"]+=1 if prog.get(m["id"],{}).get("completed") else 0
    for x in per_mapel.values(): x["percent"]=round(x["selesai"]*100/x["total"]) if x["total"] else 0
    return render_template("student/progress.html",user=user,per_mapel=per_mapel,attempts=attempts)