from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import datetime
from auth.decorators import student_required
from models.user_model import get_user_by_id, gunakan_pertemuan_untuk_materi
from models.program_model import get_all_schedules
from models.registration_model import buat_pendaftaran,get_pendaftaran_by_user,HARGA_PER_PAKET,PERTEMUAN_PER_PAKET,MAKS_PAKET_SEKALIGUS
from models.materi_model import get_materials_for_user,get_material,has_access,grant_access,mark_progress,get_progress_for_user,record_material_view,get_subject_groups_for_user,get_bab_for_user
from models.soal_model import get_questions,get_question,save_attempt,get_attempts,get_attempt,get_draft,save_draft_answer,clear_draft,ensure_draft
from services.ai_service import explain_answer,tanya_lanjutan,evaluasi_hasil_ujian
from utils.helpers import format_rupiah, clean_url_param
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
    user=_user()
    subjects=get_subject_groups_for_user(user)
    progress=get_progress_for_user(user["id"])
    for subject in subjects:
        for bab in subject["bab"]:
            for m in bab["subbab"]:
                m["can_access"]=has_access(user,m["id"])
                m["progress"]=progress.get(m["id"],{})
            bab["selesai"]=sum(1 for m in bab["subbab"] if progress.get(m["id"],{}).get("completed"))
    return render_template("student/materi.html",user=user,subjects=subjects)

@student_bp.route("/materi/mapel/<mapel>")
@student_required
def detail_mapel(mapel):
    mapel=clean_url_param(mapel)
    user=_user()
    subjects=get_subject_groups_for_user(user)
    subject=next((x for x in subjects if x["mapel"]==mapel),None)
    if not subject:
        flash("Mata pelajaran tidak ditemukan.","danger")
        return redirect(url_for("student.materi"))
    progress=get_progress_for_user(user["id"])
    for bab in subject["bab"]:
        for m in bab["subbab"]:
            m["can_access"]=has_access(user,m["id"]); m["progress"]=progress.get(m["id"],{})
        bab["selesai"]=sum(1 for m in bab["subbab"] if progress.get(m["id"],{}).get("completed"))
    return render_template("student/mapel.html",user=user,subject=subject)

@student_bp.route("/materi/mapel/<mapel>/bab/<path:bab>")
@student_required
def detail_bab(mapel,bab):
    mapel=clean_url_param(mapel); bab=clean_url_param(bab)
    user=_user(); chapter=get_bab_for_user(user,mapel,bab)
    if not chapter:
        flash("Bab tidak ditemukan.","danger"); return redirect(url_for("student.detail_mapel",mapel=mapel))
    progress=get_progress_for_user(user["id"])
    for m in chapter["subbab"]:
        m["can_access"]=has_access(user,m["id"]); m["progress"]=progress.get(m["id"],{})
        m["jumlah_latihan"]=len(get_questions(material_id=m["id"],tipe="latihan"))
    # Satu kuota pertemuan membuka SATU BAB sekaligus (semua subbab di dalamnya),
    # bukan per subbab. bab_locked = masih ada minimal 1 subbab yang belum kebuka.
    bab_locked = bool(chapter["subbab"]) and not all(m["can_access"] for m in chapter["subbab"])
    questions=get_questions(jenjang=user.get("jenjang"),kelas=user.get("kelas"),mapel=mapel,bab=bab,tipe="UH")
    return render_template("student/bab.html",user=user,chapter=chapter,mapel=mapel,questions=questions,bab_locked=bab_locked)

def _buka_bab_untuk(user,chapter,mapel,bab):
    """Buka akses ke SEMUA subbab dalam satu bab sekaligus, dengan memotong 1 kuota pertemuan saja."""
    subbab=chapter["subbab"]
    if not subbab:
        flash("Belum ada materi di bab ini.","danger"); return
    if all(has_access(user,m["id"]) for m in subbab):
        return
    try:
        sisa=gunakan_pertemuan_untuk_materi(user["id"])
        for m in subbab:
            grant_access(user["id"],m["id"],"kuota")
        flash(f"Bab \"{bab}\" berhasil dibuka ({len(subbab)} tahap sekaligus). Sisa pertemuan: {sisa}.","success")
    except ValueError as e:
        flash(str(e),"danger")

@student_bp.route("/materi/mapel/<mapel>/bab/<path:bab>/buka",methods=["POST"])
@student_required
def buka_bab(mapel,bab):
    mapel=clean_url_param(mapel); bab=clean_url_param(bab)
    user=_user(); chapter=get_bab_for_user(user,mapel,bab)
    if not chapter:
        flash("Bab tidak ditemukan.","danger"); return redirect(url_for("student.materi"))
    _buka_bab_untuk(user,chapter,mapel,bab)
    return redirect(url_for("student.detail_bab",mapel=mapel,bab=bab))

@student_bp.route("/materi/mapel/<mapel>/bab/<path:bab>/ulangan",methods=["GET","POST"])
@student_required
def ulangan_bab(mapel,bab):
    mapel=clean_url_param(mapel); bab=clean_url_param(bab)
    user=_user(); chapter=get_bab_for_user(user,mapel,bab)
    if not chapter:
        flash("Bab tidak ditemukan.","danger"); return redirect(url_for("student.materi"))
    subbab=chapter["subbab"]
    if not all(has_access(user,m["id"]) for m in subbab):
        flash("Buka akses semua subbab dalam bab ini terlebih dahulu.","danger")
        return redirect(url_for("student.detail_bab",mapel=mapel,bab=bab))
    questions=get_questions(jenjang=user.get("jenjang"),kelas=user.get("kelas"),mapel=mapel,bab=bab,tipe="UH")
    if not questions:
        flash("Belum ada soal ulangan harian untuk bab ini.","danger")
        return redirect(url_for("student.detail_bab",mapel=mapel,bab=bab))
    scope_key=f"UH__{mapel}__{bab}"
    if request.method=="POST":
        answers={q["id"]:request.form.get("q_"+q["id"],"") for q in questions}
        score=sum(1 for q in questions if answers[q["id"]]==q.get("jawaban_benar"))
        riwayat=[a for a in get_attempts(user["id"]) if a.get("tipe")=="UH" and a.get("mapel")==mapel and a.get("bab")==bab]
        attempt=save_attempt(user["id"],"UH",user.get("jenjang"),user.get("kelas"),mapel,score,len(questions),answers,material_judul=f"Ulangan Harian · {bab}",bab=bab)
        clear_draft(user["id"],"ujian",scope_key)
        reviews=[]
        for q in questions:
            selected=answers.get(q["id"],""); benar=selected==q.get("jawaban_benar")
            ai=explain_answer(q["pertanyaan"],selected,q["jawaban_benar"],q.get("penjelasan",""),benar=benar,konteks_ai=q.get("konteks_ai",""),pilihan=q.get("pilihan"),konteks_ai_pilihan=q.get("konteks_ai_pilihan"))
            reviews.append({"question":q,"selected":selected,"benar":benar,"penjelasan_ai":ai})
        evaluasi=evaluasi_hasil_ujian(mapel,"Ulangan Harian",reviews,riwayat=riwayat)
        return render_template("student/hasil_ujian.html",user=user,attempt=attempt,questions=questions,answers=answers,reviews=reviews,evaluasi=evaluasi,riwayat_sebelumnya=riwayat,percobaan_ke=len(riwayat)+1)
    draft=get_draft(user["id"],"ujian",scope_key) or ensure_draft(user["id"],"ujian",scope_key)
    riwayat=[a for a in get_attempts(user["id"]) if a.get("tipe")=="UH" and a.get("mapel")==mapel and a.get("bab")==bab]
    return render_template("student/ujian.html",user=user,tipe="UH",mapel=mapel,questions=questions,draft=draft,scope_key=scope_key,riwayat_sebelumnya=riwayat,bab=bab)

@student_bp.route("/materi/<material_id>")
@student_required
def detail_materi(material_id):
    user=_user(); material=get_material(material_id)
    if not material: flash("Materi tidak ditemukan.","danger"); return redirect(url_for("student.materi"))
    if material["jenjang"]!=str(user.get("jenjang")) or str(material["kelas"])!=str(user.get("kelas")): flash("Materi ini bukan untuk jenjang atau kelas kamu.","danger"); return redirect(url_for("student.materi"))
    allowed=has_access(user,material_id)
    if allowed:
        record_material_view(user["id"],material_id)
    latihan=get_questions(material_id=material_id,tipe="latihan")
    riwayat_latihan=[a for a in get_attempts(user["id"]) if a.get("tipe")=="Latihan Materi" and a.get("material_id")==material_id] if allowed else []
    draft=get_draft(user["id"],"latihan",material_id) if allowed else None
    return render_template("student/detail_materi.html",user=user,material=material,allowed=allowed,latihan=latihan,riwayat_latihan=riwayat_latihan,draft=draft)

@student_bp.route("/latihan")
@student_required
def latihan():
    user=_user(); mats=get_materials_for_user(user); attempts=get_attempts(user["id"])
    latihan_materi=[]
    for m in mats:
        qs=get_questions(material_id=m["id"],tipe="latihan")
        if qs:
            history=[a for a in attempts if a.get("tipe")=="Latihan Materi" and a.get("material_id")==m["id"]]
            latihan_materi.append({"material":m,"jumlah_soal":len(qs),"allowed":has_access(user,m["id"]),"riwayat":history})
    mapels=sorted({m.get("mapel") for m in mats if m.get("mapel")})
    return render_template("student/latihan.html",user=user,latihan_materi=latihan_materi,mapels=mapels)

@student_bp.route("/latihan/materi/<material_id>")
@student_required
def latihan_materi(material_id):
    user=_user(); material=get_material(material_id)
    if not material or not has_access(user,material_id):
        flash("Buka akses materi terlebih dahulu.","danger"); return redirect(url_for("student.detail_materi",material_id=material_id))
    questions=get_questions(material_id=material_id,tipe="latihan")
    if not questions: flash("Belum ada latihan untuk materi ini.","danger"); return redirect(url_for("student.detail_materi",material_id=material_id))
    draft=get_draft(user["id"],"latihan",material_id)
    if not draft:
        draft=ensure_draft(user["id"],"latihan",material_id)
    riwayat_latihan=[a for a in get_attempts(user["id"]) if a.get("tipe")=="Latihan Materi" and a.get("material_id")==material_id]
    return render_template("student/latihan_materi.html",user=user,material=material,allowed=True,latihan=questions,draft=draft,riwayat_latihan=riwayat_latihan)

@student_bp.route("/materi/<material_id>/buka",methods=["POST"])
@student_required
def buka_materi(material_id):
    user=_user(); material=get_material(material_id)
    if not material: flash("Materi tidak ditemukan.","danger"); return redirect(url_for("student.materi"))
    if material.get("jenjang") != str(user.get("jenjang")) or str(material.get("kelas")) != str(user.get("kelas")):
        flash("Materi ini bukan untuk kelas kamu.","danger"); return redirect(url_for("student.materi"))
    if has_access(user,material_id): return redirect(url_for("student.detail_materi",material_id=material_id))
    bab_nama=material.get("bab") or "Bab 1"
    chapter=get_bab_for_user(user,material.get("mapel"),bab_nama) or {"subbab":[material]}
    _buka_bab_untuk(user,chapter,material.get("mapel"),bab_nama)
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
    ai=explain_answer(q["pertanyaan"],selected,q["jawaban_benar"],q.get("penjelasan",""),benar=benar,konteks_ai=q.get("konteks_ai",""),pilihan=q.get("pilihan"),konteks_ai_pilihan=q.get("konteks_ai_pilihan"))
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
    balasan=tanya_lanjutan(q["pertanyaan"],selected,q["jawaban_benar"],benar,riwayat,pesan,konteks_ai=q.get("konteks_ai",""),pilihan=q.get("pilihan"),konteks_ai_pilihan=q.get("konteks_ai_pilihan"))
    return jsonify({"balasan":balasan})

@student_bp.route("/materi/<material_id>/latihan/selesai",methods=["POST"])
@student_required
def selesai_latihan_materi(material_id):
    """AJAX: dipanggil sekali di akhir sesi Latihan Soal per materi (setelah semua nomor dikerjakan),
    buat menyimpan attempt + minta evaluasi/rekomendasi belajar dari AI berdasarkan soal yang salah."""
    user=_user(); material=get_material(material_id)
    if not material: return jsonify({"error":"Materi tidak ditemukan."}),404
    if not has_access(user,material_id): return jsonify({"error":"Kamu belum punya akses ke materi ini."}),403
    questions=get_questions(material_id=material_id,tipe="latihan")
    if not questions: return jsonify({"error":"Belum ada latihan untuk materi ini."}),400
    data=request.get_json(silent=True) or {}
    jawaban_mentah=data.get("answers") or {}
    answers={q["id"]:str(jawaban_mentah.get(q["id"],""))[:10] for q in questions}
    score=sum(1 for q in questions if answers[q["id"]]==q.get("jawaban_benar"))
    total=len(questions)
    riwayat_sebelumnya=[a for a in get_attempts(user["id"]) if a.get("tipe")=="Latihan Materi" and a.get("material_id")==material_id]
    attempt=save_attempt(user["id"],"Latihan Materi",material.get("jenjang"),material.get("kelas"),material.get("mapel"),score,total,answers,material_id=material_id,material_judul=material.get("judul"))
    clear_draft(user["id"],"latihan",material_id)
    reviews=[{"question":q,"selected":answers.get(q["id"],""),"benar":answers.get(q["id"],"")==q.get("jawaban_benar")} for q in questions]
    evaluasi=evaluasi_hasil_ujian(material.get("mapel"),"Latihan Materi",reviews,riwayat=riwayat_sebelumnya)
    return jsonify({"score":score,"total":total,"percent":attempt.get("percent",0),"evaluasi":evaluasi,"percobaan_ke":len(riwayat_sebelumnya)+1,"attempt_id":attempt["id"]})

@student_bp.route("/soal/<question_id>/cek-jawaban",methods=["POST"])
@student_required
def cek_jawaban_soal(question_id):
    """AJAX: cek jawaban satu soal secara langsung (dipakai di latihan UTS/UAS per nomor & latihan materi),
    tanpa reload halaman dan tanpa menyimpan attempt (attempt resmi disimpan saat submit akhir).
    Kalau request menyertakan scope_type + scope_key (dikirim dari halaman ujian/latihan), hasilnya juga
    disimpan ke draft progress -> kalau koneksi putus / logout di tengah jalan, siswa bisa lanjut dari
    situ pas login lagi, gak perlu ngulang dari nomor 1."""
    user=_user(); q=get_question(question_id)
    if not q: return jsonify({"error":"Soal tidak ditemukan."}),404
    if q.get("material_id") and not has_access(user,q.get("material_id")):
        return jsonify({"error":"Kamu belum punya akses ke materi ini."}),403
    data=request.get_json(silent=True) or {}
    selected=str(data.get("jawaban",""))[:10]
    benar=selected==q.get("jawaban_benar")
    ai=explain_answer(q["pertanyaan"],selected,q["jawaban_benar"],q.get("penjelasan",""),benar=benar,konteks_ai=q.get("konteks_ai",""),pilihan=q.get("pilihan"),konteks_ai_pilihan=q.get("konteks_ai_pilihan"))
    scope_type=data.get("scope_type"); scope_key=str(data.get("scope_key") or "")[:200]
    if scope_type in ("ujian","latihan") and scope_key:
        save_draft_answer(user["id"],scope_type,scope_key,question_id,{"selected":selected,"benar":benar,"jawaban_benar":q.get("jawaban_benar"),"penjelasan_ai":ai,"answered_at":datetime.datetime.utcnow()})
    return jsonify({"benar":benar,"jawaban_benar":q.get("jawaban_benar"),"penjelasan_ai":ai})

@student_bp.route("/ujian/<tipe>/<mapel>",methods=["GET","POST"])
@student_required
def ujian(tipe,mapel):
    tipe=tipe.upper(); mapel=clean_url_param(mapel); user=_user()
    if tipe not in {"UTS","UAS"}: flash("Jenis latihan tidak valid.","danger"); return redirect(url_for("student.materi"))
    questions=get_questions(jenjang=user.get("jenjang"),kelas=user.get("kelas"),mapel=mapel,tipe=tipe)
    scope_key=f"{tipe}_{mapel}"
    if request.method=="POST":
        answers={q["id"]:request.form.get("q_"+q["id"],"") for q in questions}; score=sum(1 for q in questions if answers[q["id"]]==q.get("jawaban_benar"))
        riwayat_sebelumnya=[a for a in get_attempts(user["id"]) if a.get("tipe")==tipe and a.get("mapel")==mapel]
        attempt=save_attempt(user["id"],tipe,user.get("jenjang"),user.get("kelas"),mapel,score,len(questions),answers)
        clear_draft(user["id"],"ujian",scope_key)
        reviews=[]
        for q in questions:
            selected=answers.get(q["id"],""); benar=selected==q.get("jawaban_benar")
            ai=explain_answer(q["pertanyaan"],selected,q["jawaban_benar"],q.get("penjelasan",""),benar=benar,konteks_ai=q.get("konteks_ai",""),pilihan=q.get("pilihan"),konteks_ai_pilihan=q.get("konteks_ai_pilihan"))
            reviews.append({"question":q,"selected":selected,"benar":benar,"penjelasan_ai":ai})
        evaluasi=evaluasi_hasil_ujian(mapel,tipe,reviews,riwayat=riwayat_sebelumnya)
        return render_template("student/hasil_ujian.html",user=user,attempt=attempt,questions=questions,answers=answers,reviews=reviews,evaluasi=evaluasi,riwayat_sebelumnya=riwayat_sebelumnya,percobaan_ke=len(riwayat_sebelumnya)+1)
    draft=get_draft(user["id"],"ujian",scope_key)
    if not draft:
        draft=ensure_draft(user["id"],"ujian",scope_key)
    riwayat_sebelumnya=[a for a in get_attempts(user["id"]) if a.get("tipe")==tipe and a.get("mapel")==mapel]
    return render_template("student/ujian.html",user=user,tipe=tipe,mapel=mapel,questions=questions,draft=draft,scope_key=scope_key,riwayat_sebelumnya=riwayat_sebelumnya)

@student_bp.route("/progress/reset-draft",methods=["POST"])
@student_required
def reset_draft():
    """Buang draft progress yang lagi tersimpan (dipakai kalau siswa milih 'Mulai Ulang dari Nomor 1'
    alih-alih lanjut dari draft). Tidak menghapus riwayat nilai/attempt yang sudah pernah disimpan."""
    user=_user(); data=request.get_json(silent=True) or {}
    scope_type=data.get("scope_type"); scope_key=str(data.get("scope_key") or "")[:200]
    if scope_type in ("ujian","latihan") and scope_key: clear_draft(user["id"],scope_type,scope_key)
    return jsonify({"ok":True})

@student_bp.route("/progress/riwayat/<attempt_id>")
@student_required
def riwayat_detail(attempt_id):
    """Review ulang satu percobaan (attempt) yang sudah lewat -> soal apa aja yang dikerjakan,
    jawaban siswa vs jawaban benar. Bisa dibuka lagi kapan pun walau sudah 'ngerjain ulang'
    berkali-kali, soalnya tiap attempt tersimpan terpisah (tidak saling menimpa)."""
    user=_user(); attempt=get_attempt(attempt_id)
    if not attempt or attempt.get("user_id")!=user["id"]:
        flash("Riwayat tidak ditemukan.","danger"); return redirect(url_for("student.progress"))
    if attempt.get("material_id"): questions=get_questions(material_id=attempt["material_id"],tipe="latihan")
    else: questions=get_questions(jenjang=attempt.get("jenjang"),kelas=attempt.get("kelas"),mapel=attempt.get("mapel"),tipe=attempt.get("tipe"))
    answers=attempt.get("answers") or {}
    reviews=[{"question":q,"selected":answers.get(q["id"],""),"benar":answers.get(q["id"],"")==q.get("jawaban_benar")} for q in questions]
    return render_template("student/riwayat_detail.html",user=user,attempt=attempt,reviews=reviews)

@student_bp.route("/progress")
@student_required
def progress():
    user=_user(); mats=get_materials_for_user(user); prog=get_progress_for_user(user["id"]); attempts=get_attempts(user["id"])
    per_mapel={}
    for m in mats:
        x=per_mapel.setdefault(m["mapel"],{"total":0,"selesai":0}); x["total"]+=1; x["selesai"]+=1 if prog.get(m["id"],{}).get("completed") else 0
    for x in per_mapel.values(): x["percent"]=round(x["selesai"]*100/x["total"]) if x["total"] else 0
    # kelompokkan tiap attempt berdasarkan scope-nya (materi yang sama, atau tipe+mapel yang sama)
    # biar kelihatan riwayat & kemajuan dari waktu ke waktu -> tiap percobaan tetap disimpan, gak ada yang hilang.
    kelompok={}
    for a in attempts:
        key=(a.get("material_id") or "")+"|"+a.get("tipe","")+"|"+a.get("mapel","")+"|"+(a.get("bab") or "")
        kelompok.setdefault(key,[]).append(a)
    riwayat_kelompok=[]
    for lst in kelompok.values():
        lst_lama_ke_baru=sorted(lst,key=lambda x:str(x.get("created_at") or ""))
        lst_baru_ke_lama=list(reversed(lst_lama_ke_baru))
        selisih=round(lst_lama_ke_baru[-1].get("percent",0)-lst_lama_ke_baru[0].get("percent",0),1) if len(lst_lama_ke_baru)>1 else None
        terbaru=lst_baru_ke_lama[0]
        riwayat_kelompok.append({
            "label":(terbaru.get("material_judul") or terbaru.get("mapel") or "-")+" · "+terbaru.get("tipe",""),
            "attempts":lst_baru_ke_lama,"jumlah_percobaan":len(lst_baru_ke_lama),
            "selisih":selisih,"terbaik":max(a.get("percent",0) for a in lst_baru_ke_lama),
            "terbaru":terbaru.get("created_at"),
        })
    riwayat_kelompok.sort(key=lambda g:str(g["terbaru"] or ""),reverse=True)
    return render_template("student/progress.html",user=user,per_mapel=per_mapel,attempts=attempts,riwayat_kelompok=riwayat_kelompok)