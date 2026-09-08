import datetime
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso, json_dumps, json_loads, as_int
from services.supabase_storage import delete_file
COLLECTION="questions"; ATTEMPTS="quiz_attempts"; DRAFTS="quiz_drafts"

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
    qid=new_id(); now=utcnow_iso();
    data={"id":qid,"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"bab":bab or "","tipe":tipe,"material_id":material_id,"pertanyaan":pertanyaan,"pilihan":pilihan,"jawaban_benar":jawaban_benar,"penjelasan":penjelasan,"konteks_ai":konteks_ai or "","konteks_ai_pilihan":konteks_ai_pilihan or ["","","",""],"gambar_url":gambar_url,"gambar_path":gambar_path,"pilihan_gambar":pilihan_gambar or [None,None,None,None],"pilihan_gambar_path":pilihan_gambar_path or [None,None,None,None],"created_at":now}
    execute("""INSERT INTO questions (id,jenjang,kelas,mapel,bab,tipe,material_id,pertanyaan,pilihan,jawaban_benar,penjelasan,konteks_ai,konteks_ai_pilihan,gambar_url,gambar_path,pilihan_gambar,pilihan_gambar_path,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(qid,jenjang,str(kelas),mapel,bab or "",tipe,material_id,pertanyaan,json_dumps(pilihan),jawaban_benar,penjelasan,konteks_ai or "",json_dumps(konteks_ai_pilihan or ["","","",""]),gambar_url,gambar_path,json_dumps(pilihan_gambar or [None,None,None,None]),json_dumps(pilihan_gambar_path or [None,None,None,None]),now))
    return data

def get_question(qid): return _question(fetch_one("SELECT * FROM questions WHERE id=? LIMIT 1",(qid,)))
def get_questions(**filters):
    rows=fetch_all("SELECT * FROM questions")
    out=[]
    for row in rows:
        x=_question(row)
        if all(str(x.get(k) or "")==str(v) for k,v in filters.items() if v not in (None,"")): out.append(x)
    return sorted(out,key=lambda x:str(x.get("created_at") or ""))

def update_question(qid, **fields):
    json_fields={"pilihan","konteks_ai_pilihan","pilihan_gambar","pilihan_gambar_path"}
    allowed={"jenjang","kelas","mapel","bab","tipe","material_id","pertanyaan","pilihan","jawaban_benar","penjelasan","konteks_ai","konteks_ai_pilihan","gambar_url","gambar_path","pilihan_gambar","pilihan_gambar_path"}
    fields={k:(json_dumps(v) if k in json_fields else v) for k,v in fields.items() if k in allowed}
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
