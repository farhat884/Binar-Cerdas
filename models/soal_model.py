import datetime
from firebase_config import db
from services.supabase_storage import delete_file
COLLECTION="questions"; ATTEMPTS="quiz_attempts"; DRAFTS="quiz_drafts"

def _doc(doc): d=doc.to_dict(); d["id"]=doc.id; return d

def create_question(jenjang,kelas,mapel,tipe,pertanyaan,pilihan,jawaban_benar,penjelasan="",material_id=None,gambar_url=None,gambar_path=None,pilihan_gambar=None,pilihan_gambar_path=None,konteks_ai="",konteks_ai_pilihan=None,bab=""):
    ref=db.collection(COLLECTION).document(); data={"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"bab":bab or "","tipe":tipe,"material_id":material_id,"pertanyaan":pertanyaan,"pilihan":pilihan,"jawaban_benar":jawaban_benar,"penjelasan":penjelasan,"konteks_ai":konteks_ai or "","konteks_ai_pilihan":konteks_ai_pilihan or ["","","",""],"gambar_url":gambar_url,"gambar_path":gambar_path,"pilihan_gambar":pilihan_gambar or [None,None,None,None],"pilihan_gambar_path":pilihan_gambar_path or [None,None,None,None],"created_at":datetime.datetime.utcnow()}; ref.set(data); data["id"]=ref.id; return data

def get_question(qid):
    d=db.collection(COLLECTION).document(qid).get(); return _doc(d) if d.exists else None

def get_questions(**filters):
    out=[]
    for d in db.collection(COLLECTION).stream():
        x=_doc(d)
        if all(str(x.get(k) or "")==str(v) for k,v in filters.items() if v not in (None,"")): out.append(x)
    return sorted(out,key=lambda x:str(x.get("created_at") or ""))

def update_question(qid, **fields): db.collection(COLLECTION).document(qid).update(fields)
def delete_question(qid):
    q=get_question(qid)
    if q:
        if q.get("gambar_path"): delete_file(q.get("gambar_path"))
        for p in (q.get("pilihan_gambar_path") or []):
            if p: delete_file(p)
    db.collection(COLLECTION).document(qid).delete()

def save_attempt(user_id,tipe,jenjang,kelas,mapel,score,total,answers,material_id=None,material_judul=None,bab=None):
    """Setiap kali dipanggil SELALU membuat dokumen attempt baru (tidak pernah menimpa attempt lama),
    jadi kalau siswa mengerjakan ulang, nilai sebelumnya tetap tersimpan sebagai riwayat -> dipakai buat
    lihat kemajuan (progress) dan bahan evaluasi AI."""
    ref=db.collection(ATTEMPTS).document()
    data={"user_id":user_id,"tipe":tipe,"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"material_id":material_id,"material_judul":material_judul,"bab":bab,"score":score,"total":total,"percent":round(score/total*100,2) if total else 0,"answers":answers,"created_at":datetime.datetime.utcnow()}
    ref.set(data); data["id"]=ref.id; return data

def get_attempts(user_id):
    out=[_doc(d) for d in db.collection(ATTEMPTS).where("user_id","==",user_id).stream()]
    return sorted(out,key=lambda x:str(x.get("created_at") or ""),reverse=True)

def get_attempt(attempt_id):
    d=db.collection(ATTEMPTS).document(attempt_id).get(); return _doc(d) if d.exists else None


def get_all_attempts():
    """Semua attempt untuk kebutuhan monitoring admin."""
    out=[_doc(d) for d in db.collection(ATTEMPTS).stream()]
    return sorted(out,key=lambda x:str(x.get("created_at") or ""),reverse=True)

def get_all_drafts():
    """Semua draft pengerjaan aktif. Draft ini menyimpan jawaban setiap nomor
    segera setelah siswa menekan tombol Jawab, sehingga admin bisa memantau
    pengerjaan yang sedang berlangsung."""
    out=[_doc(d) for d in db.collection(DRAFTS).stream()]
    return sorted(out,key=lambda x:str(x.get("updated_at") or ""),reverse=True)

# --- Draft pengerjaan (buat resume kalau koneksi putus/lag/logout di tengah ngerjain) ---
# scope_type: "ujian" (UTS/UAS per mapel) atau "latihan" (latihan soal per materi)
# scope_key : "UTS_Matematika" utk ujian, atau material_id utk latihan
def _draft_id(user_id,scope_type,scope_key): return f"{user_id}__{scope_type}__{scope_key}"

def get_draft(user_id,scope_type,scope_key):
    d=db.collection(DRAFTS).document(_draft_id(user_id,scope_type,scope_key)).get()
    return d.to_dict() if d.exists else None

def ensure_draft(user_id,scope_type,scope_key):
    """Buat draft saat siswa mulai halaman latihan/ujian, bahkan sebelum soal
    pertama dijawab, supaya admin bisa melihat bahwa siswa sedang mengerjakan."""
    ref=db.collection(DRAFTS).document(_draft_id(user_id,scope_type,scope_key))
    snap=ref.get()
    if snap.exists:
        return snap.to_dict()
    now=datetime.datetime.utcnow()
    data={"user_id":user_id,"scope_type":scope_type,"scope_key":scope_key,"answers":{},"created_at":now,"updated_at":now}
    ref.set(data)
    return data

def save_draft_answer(user_id,scope_type,scope_key,question_id,hasil):
    """Simpan/perbarui progress SATU nomor ke draft. `hasil` = dict {selected,benar,jawaban_benar,penjelasan_ai}
    supaya pas resume gak perlu manggil AI ulang buat nomor yang udah dijawab."""
    ref=db.collection(DRAFTS).document(_draft_id(user_id,scope_type,scope_key))
    snap=ref.get()
    data=snap.to_dict() if snap.exists else {"user_id":user_id,"scope_type":scope_type,"scope_key":scope_key,"answers":{},"created_at":datetime.datetime.utcnow()}
    answers=data.get("answers") or {}; answers[question_id]=hasil; data["answers"]=answers
    data["updated_at"]=datetime.datetime.utcnow()
    ref.set(data); return data

def clear_draft(user_id,scope_type,scope_key):
    db.collection(DRAFTS).document(_draft_id(user_id,scope_type,scope_key)).delete()

def delete_user_quiz_data(user_id):
    """Hapus semua riwayat pengerjaan (quiz_attempts) & draft yang sedang
    dikerjakan (quiz_drafts) milik satu siswa. Dipanggil saat admin
    menghapus akun siswa, biar gak nyisain dokumen yatim di koleksi
    quiz_attempts/quiz_drafts yang nunjuk ke user_id yang udah gak ada."""
    for d in db.collection(ATTEMPTS).where("user_id","==",user_id).stream():
        d.reference.delete()
    for d in db.collection(DRAFTS).where("user_id","==",user_id).stream():
        d.reference.delete()
