"""Model Live Quiz backed by Turso/libSQL."""
import datetime, random
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso, json_dumps, json_loads, as_int

SESSIONS="live_sessions"; PARTICIPANTS="live_participants"
STATUS_LOBI="lobi"; STATUS_SOAL="soal"; STATUS_JEDA="jeda"; STATUS_SELESAI="selesai"
DURASI_DEFAULT=20

def _decode_session(d):
    if not d:return None
    d=dict(d); d["questions"]=json_loads(d.get("questions"), []); d["current_index"]=as_int(d.get("current_index"),-1); d["durasi_detik"]=as_int(d.get("durasi_detik"),DURASI_DEFAULT); return d

def _decode_participant(d):
    if not d:return None
    d=dict(d); d["jawaban"]=json_loads(d.get("jawaban"), {}); d["skor"]=as_int(d.get("skor"),0); return d

def _generate_kode():
    alfabet="ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        kode="".join(random.choice(alfabet) for _ in range(6))
        if not get_session_by_kode(kode):return kode

def create_session(admin_id,judul,mapel="",durasi_detik=DURASI_DEFAULT):
    sid=new_id(); data={"id":sid,"admin_id":admin_id,"judul":judul or "Latihan Soal Live","mapel":mapel or "","kode":_generate_kode(),"status":STATUS_LOBI,"questions":[],"current_index":-1,"durasi_detik":int(durasi_detik) if durasi_detik else DURASI_DEFAULT,"current_started_at":None,"created_at":utcnow_iso()}
    execute("INSERT INTO live_sessions (id,admin_id,judul,mapel,kode,status,questions,current_index,durasi_detik,current_started_at,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(sid,data["admin_id"],data["judul"],data["mapel"],data["kode"],data["status"],"[]",-1,data["durasi_detik"],None,data["created_at"]))
    return data

def get_session(session_id):return _decode_session(fetch_one("SELECT * FROM live_sessions WHERE id=? LIMIT 1",(session_id,)))
def get_session_by_kode(kode):
    kode=(kode or "").strip().upper()
    if not kode:return None
    return _decode_session(fetch_one("SELECT * FROM live_sessions WHERE upper(kode)=? LIMIT 1",(kode,)))
def get_sessions_by_admin(admin_id):return sorted([_decode_session(x) for x in fetch_all("SELECT * FROM live_sessions WHERE admin_id=?",(admin_id,))],key=lambda x:str(x.get("created_at") or ""),reverse=True)
def delete_session(session_id):execute("DELETE FROM live_participants WHERE session_id=?",(session_id,)); execute("DELETE FROM live_sessions WHERE id=?",(session_id,))

def add_question(session_id,pertanyaan,pilihan,jawaban_benar,penjelasan=""):
    sess=get_session(session_id)
    if not sess:return None
    questions=sess.get("questions") or []; qid=f"q{len(questions)+1}_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"
    questions.append({"id":qid,"pertanyaan":pertanyaan,"pilihan":pilihan,"jawaban_benar":jawaban_benar,"penjelasan":penjelasan or ""})
    execute("UPDATE live_sessions SET questions=? WHERE id=?",(json_dumps(questions),session_id)); return qid

def add_questions_bulk(session_id,soal_list):
    sess=get_session(session_id)
    if not sess:return 0
    questions=sess.get("questions") or []; base=len(questions); now_ts=int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    for i,soal in enumerate(soal_list):questions.append({"id":f"q{base+i+1}_{now_ts}_{i}","pertanyaan":soal["pertanyaan"],"pilihan":soal["pilihan"],"jawaban_benar":soal["jawaban_benar"],"penjelasan":soal.get("penjelasan","") or ""})
    execute("UPDATE live_sessions SET questions=? WHERE id=?",(json_dumps(questions),session_id)); return len(soal_list)

def delete_question(session_id,question_id):
    sess=get_session(session_id)
    if not sess:return
    questions=[q for q in (sess.get("questions") or []) if q.get("id")!=question_id]; execute("UPDATE live_sessions SET questions=? WHERE id=?",(json_dumps(questions),session_id))

def start_session(session_id):
    sess=get_session(session_id)
    if not sess or not sess.get("questions"):return None
    execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=? WHERE id=?",(STATUS_SOAL,0,utcnow_iso(),session_id)); return get_session(session_id)

def advance_session(session_id):
    sess=get_session(session_id)
    if not sess:return None
    if sess["status"]==STATUS_SOAL:execute("UPDATE live_sessions SET status=? WHERE id=?",(STATUS_JEDA,session_id))
    elif sess["status"]==STATUS_JEDA:
        next_index=sess["current_index"]+1
        if next_index>=len(sess.get("questions") or []):execute("UPDATE live_sessions SET status=? WHERE id=?",(STATUS_SELESAI,session_id))
        else:execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=? WHERE id=?",(STATUS_SOAL,next_index,utcnow_iso(),session_id))
    return get_session(session_id)
def end_session(session_id):execute("UPDATE live_sessions SET status=? WHERE id=?",(STATUS_SELESAI,session_id)); return get_session(session_id)
def reset_session(session_id):
    execute("UPDATE live_participants SET skor=?,jawaban=? WHERE session_id=?",(0,"{}",session_id)); execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=? WHERE id=?",(STATUS_LOBI,-1,None,session_id)); return get_session(session_id)
def _participant_id(session_id,user_id):return f"{session_id}__{user_id}"
def join_session(session_id,user_id,nama):
    pid=_participant_id(session_id,user_id); old=get_participant(session_id,user_id)
    if old:return old
    data={"id":pid,"session_id":session_id,"user_id":user_id,"nama":nama,"skor":0,"jawaban":{},"joined_at":utcnow_iso()}
    execute("INSERT INTO live_participants (id,session_id,user_id,nama,skor,jawaban,joined_at) VALUES (?,?,?,?,?,?,?)",(pid,session_id,user_id,nama,0,"{}",data["joined_at"])); return data
def get_participant(session_id,user_id):return _decode_participant(fetch_one("SELECT * FROM live_participants WHERE id=? LIMIT 1",(_participant_id(session_id,user_id),)))
def get_participants(session_id):return sorted([_decode_participant(x) for x in fetch_all("SELECT * FROM live_participants WHERE session_id=?",(session_id,))],key=lambda x:str(x.get("joined_at") or ""))
def get_leaderboard(session_id):return sorted(get_participants(session_id),key=lambda x:x.get("skor",0),reverse=True)
def hitung_skor(benar,waktu_ms,durasi_detik):
    if not benar:return 0
    durasi_ms=max(1,durasi_detik*1000); sisa_rasio=max(0.0,min(1.0,1-(waktu_ms/durasi_ms))); return int(500+round(500*sisa_rasio))
def submit_answer(session_id,user_id,question_id,selected,waktu_ms):
    sess=get_session(session_id)
    if not sess:return None,"Sesi tidak ditemukan."
    if sess["status"]!=STATUS_SOAL:return None,"Soal ini sudah ditutup."
    questions=sess.get("questions") or []; q=next((x for x in questions if x["id"]==question_id),None)
    if not q:return None,"Soal tidak ditemukan."
    idx=sess.get("current_index",-1)
    if idx<0 or idx>=len(questions) or questions[idx]["id"]!=question_id:return None,"Soal ini bukan soal yang sedang aktif."
    data=get_participant(session_id,user_id)
    if not data:return None,"Kamu belum join sesi ini."
    jawaban=data.get("jawaban") or {}
    if question_id in jawaban:return jawaban[question_id],None
    benar=selected==q.get("jawaban_benar"); waktu_ms=max(0,int(waktu_ms or 0)); skor_soal=hitung_skor(benar,waktu_ms,sess.get("durasi_detik",DURASI_DEFAULT)); hasil={"selected":selected,"benar":benar,"skor":skor_soal,"waktu_ms":waktu_ms}; jawaban[question_id]=hasil
    execute("UPDATE live_participants SET jawaban=?,skor=? WHERE id=?",(json_dumps(jawaban),data.get("skor",0)+skor_soal),_participant_id(session_id,user_id)); return hasil,None
