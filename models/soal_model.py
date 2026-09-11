import datetime
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso, json_dumps, json_loads, as_int
from services.supabase_storage import delete_file
COLLECTION="questions"; ATTEMPTS="quiz_attempts"; DRAFTS="quiz_drafts"

# "checkpoint" = tag bagian/tahapan dalam sebuah bab (misal "Pengertian &
# Konsep Gaya", "Jenis-jenis Gaya"). Dipakai supaya pas Kelas Live, pengajar
# bisa tiba-tiba menyalakan kuis pendek untuk SATU tahapan tertentu yang
# baru saja dijelaskan -- soal yang keluar dipilih acak dari bank soal
# bertag sama, jadi tiap kali dinyalakan (walau tahapan yang sama) soalnya
# bisa beda.
#
# PENTING: "checkpoint" BUKAN kolom yang diisi manual terpisah. Nilainya
# selalu disamakan otomatis dengan judul "Tahapan Materi" (material_id) yang
# dipilih pada soal tersebut -- lihat _derive_checkpoint() di bawah. Ini
# sengaja dibuat begitu supaya admin cukup isi SATU field ("Tahapan Materi"),
# bukan dua field yang isinya sama tapi gampang kelewat salah satunya.
QUESTION_EXTRA_COLUMNS = {"checkpoint": "TEXT DEFAULT ''"}

def ensure_question_columns():
    try:
        cols = {str(r.get("name")) for r in fetch_all("PRAGMA table_info(questions)")}
        for name, ddl in QUESTION_EXTRA_COLUMNS.items():
            if name not in cols:
                execute(f"ALTER TABLE questions ADD COLUMN {name} {ddl}")
    except Exception:
        pass

ensure_question_columns()

def _derive_checkpoint(material_id):
    """Checkpoint = judul Tahapan Materi yang ditautkan. Gak ada material_id
    -> gak ada checkpoint (soal itu gak akan muncul di 'Kuis per Tahapan')."""
    if not material_id:
        return ""
    try:
        from models.materi_model import get_material
        m = get_material(material_id)
    except Exception:
        m = None
    return ((m or {}).get("judul") or "").strip()

def _question(d):
    if not d:return None
    d=dict(d)
    for k in ("pilihan","konteks_ai_pilihan","pilihan_gambar","pilihan_gambar_path"):
        d[k]=json_loads(d.get(k), [])
    return d

def _attempt(d):
    if not d:return None
    d=dict(d); d["answers"]=json_loads(d.get("answers"), {}); d["score"]=as_int(d.get("score")); d["total"]=as_int(d.get("total"));
    try:d["percent"]=float(d.get("percent"))
    except (TypeError,ValueError):d["percent"]=0
    return d

def _draft(d):
    if not d:return None
    d=dict(d); d["answers"]=json_loads(d.get("answers"), {}); return d

def create_question(jenjang,kelas,mapel,tipe,pertanyaan,pilihan,jawaban_benar,penjelasan="",material_id=None,gambar_url=None,gambar_path=None,pilihan_gambar=None,pilihan_gambar_path=None,konteks_ai="",konteks_ai_pilihan=None,bab=""):
    qid=new_id(); now=utcnow_iso(); checkpoint=_derive_checkpoint(material_id)
    data={"id":qid,"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"bab":bab or "","tipe":tipe,"material_id":material_id,"pertanyaan":pertanyaan,"pilihan":pilihan,"jawaban_benar":jawaban_benar,"penjelasan":penjelasan,"konteks_ai":konteks_ai or "","konteks_ai_pilihan":konteks_ai_pilihan or ["","","",""],"gambar_url":gambar_url,"gambar_path":gambar_path,"pilihan_gambar":pilihan_gambar or [None,None,None,None],"pilihan_gambar_path":pilihan_gambar_path or [None,None,None,None],"checkpoint":checkpoint,"created_at":now}
    execute("""INSERT INTO questions (id,jenjang,kelas,mapel,bab,tipe,material_id,pertanyaan,pilihan,jawaban_benar,penjelasan,konteks_ai,konteks_ai_pilihan,gambar_url,gambar_path,pilihan_gambar,pilihan_gambar_path,checkpoint,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(qid,jenjang,str(kelas),mapel,bab or "",tipe,material_id,pertanyaan,json_dumps(pilihan),jawaban_benar,penjelasan,konteks_ai or "",json_dumps(konteks_ai_pilihan or ["","","",""]),gambar_url,gambar_path,json_dumps(pilihan_gambar or [None,None,None,None]),json_dumps(pilihan_gambar_path or [None,None,None,None]),checkpoint,now))
    return data

def get_question(qid): return _question(fetch_one("SELECT * FROM questions WHERE id=? LIMIT 1",(qid,)))
def get_questions(**filters):
    rows=fetch_all("SELECT * FROM questions")
    out=[]
    for row in rows:
        x=_question(row)
        if all(str(x.get(k) or "")==str(v) for k,v in filters.items() if v not in (None,"")): out.append(x)
    # Fallback tampilan buat soal LAMA yang sudah tertaut Tahapan Materi tapi
    # kolom checkpoint-nya belum kesimpan (dari sebelum checkpoint disatukan
    # otomatis dengan Tahapan Materi). Dihitung sekali per request kalau ada
    # yang perlu saja -- TIDAK ditulis balik ke DB, biar gak nambah query
    # tulis tiap request (soal ini akan permanen kesimpen begitu soalnya
    # di-edit/disimpan-ulang lewat Bank Soal).
    kosong=[q for q in out if q.get("material_id") and not (q.get("checkpoint") or "").strip()]
    if kosong:
        try:
            from models.materi_model import get_all_materials
            peta={m["id"]:(m.get("judul") or "") for m in get_all_materials()}
            for q in kosong:
                q["checkpoint"]=(peta.get(q.get("material_id")) or "").strip()
        except Exception:
            pass
    return sorted(out,key=lambda x:str(x.get("created_at") or ""))

def get_checkpoints(mapel, bab, tipe="latihan"):
    """Daftar nama 'bagian' (checkpoint) unik untuk mapel+bab tertentu, lengkap
    jumlah soal per bagian. Dipakai buat tombol 'Kuis Cepat' di Kelas Live."""
    qs = get_questions(mapel=mapel, bab=bab, tipe=tipe)
    counts = {}
    for q in qs:
        cp = (q.get("checkpoint") or "").strip()
        if not cp:
            continue
        counts[cp] = counts.get(cp, 0) + 1
    return [{"nama": k, "jumlah": v} for k, v in sorted(counts.items())]

def update_question(qid, **fields):
    json_fields={"pilihan","konteks_ai_pilihan","pilihan_gambar","pilihan_gambar_path"}
    allowed={"jenjang","kelas","mapel","bab","tipe","material_id","pertanyaan","pilihan","jawaban_benar","penjelasan","konteks_ai","konteks_ai_pilihan","gambar_url","gambar_path","pilihan_gambar","pilihan_gambar_path"}
    fields={k:(json_dumps(v) if k in json_fields else v) for k,v in fields.items() if k in allowed}
    if "material_id" in fields:
        # Checkpoint selalu ikut Tahapan Materi -- bukan field terpisah yang
        # bisa nyasar beda sama Tahapan Materi-nya.
        fields["checkpoint"]=_derive_checkpoint(fields["material_id"])
    if not fields:return
    execute("UPDATE questions SET "+", ".join(f"{k}=?" for k in fields)+" WHERE id=?",tuple(fields[k] for k in fields)+(qid,))

def delete_question(qid):
    q=get_question(qid)
    if q:
        if q.get("gambar_path"):delete_file(q.get("gambar_path"))
        for p in (q.get("pilihan_gambar_path") or []):
            if p:delete_file(p)
    execute("DELETE FROM questions WHERE id=?",(qid,))

def save_attempt(user_id,tipe,jenjang,kelas,mapel,score,total,answers,material_id=None,material_judul=None,bab=None):
    aid=new_id(); now=utcnow_iso(); percent=round(score/total*100,2) if total else 0
    execute("""INSERT INTO quiz_attempts (id,user_id,tipe,jenjang,kelas,mapel,material_id,material_judul,bab,score,total,percent,answers,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(aid,user_id,tipe,jenjang,str(kelas),mapel,material_id,material_judul,bab,score,total,percent,json_dumps(answers),now))
    return {"id":aid,"user_id":user_id,"tipe":tipe,"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"material_id":material_id,"material_judul":material_judul,"bab":bab,"score":score,"total":total,"percent":percent,"answers":answers,"created_at":now}

def get_attempts(user_id): return sorted([_attempt(x) for x in fetch_all("SELECT * FROM quiz_attempts WHERE user_id=?",(user_id,))],key=lambda x:str(x.get("created_at") or ""),reverse=True)
def get_attempt(attempt_id): return _attempt(fetch_one("SELECT * FROM quiz_attempts WHERE id=? LIMIT 1",(attempt_id,)))
def get_all_attempts(): return sorted([_attempt(x) for x in fetch_all("SELECT * FROM quiz_attempts")],key=lambda x:str(x.get("created_at") or ""),reverse=True)
def get_all_drafts(): return sorted([_draft(x) for x in fetch_all("SELECT * FROM quiz_drafts")],key=lambda x:str(x.get("updated_at") or ""),reverse=True)
def _draft_id(user_id,scope_type,scope_key): return f"{user_id}__{scope_type}__{scope_key}"
def get_draft(user_id,scope_type,scope_key): return _draft(fetch_one("SELECT * FROM quiz_drafts WHERE id=? LIMIT 1",(_draft_id(user_id,scope_type,scope_key),)))
def ensure_draft(user_id,scope_type,scope_key):
    did=_draft_id(user_id,scope_type,scope_key); old=get_draft(user_id,scope_type,scope_key)
    if old:return old
    now=utcnow_iso(); data={"id":did,"user_id":user_id,"scope_type":scope_type,"scope_key":scope_key,"answers":{},"created_at":now,"updated_at":now}
    execute("INSERT INTO quiz_drafts (id,user_id,scope_type,scope_key,answers,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",(did,user_id,scope_type,scope_key,"{}",now,now)); return data

def save_draft_answer(user_id,scope_type,scope_key,question_id,hasil):
    did=_draft_id(user_id,scope_type,scope_key); data=get_draft(user_id,scope_type,scope_key) or ensure_draft(user_id,scope_type,scope_key); answers=data.get("answers") or {}; answers[question_id]=hasil; now=utcnow_iso()
    execute("UPDATE quiz_drafts SET answers=?,updated_at=? WHERE id=?",(json_dumps(answers),now,did)); data["answers"]=answers; data["updated_at"]=now; return data

def clear_draft(user_id,scope_type,scope_key): execute("DELETE FROM quiz_drafts WHERE id=?",(_draft_id(user_id,scope_type,scope_key),))
def delete_user_quiz_data(user_id): execute("DELETE FROM quiz_attempts WHERE user_id=?",(user_id,)); execute("DELETE FROM quiz_drafts WHERE user_id=?",(user_id,))
