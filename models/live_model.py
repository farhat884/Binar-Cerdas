"""Model Live Quiz backed by Turso/libSQL."""
import datetime, random
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso, json_dumps, json_loads, as_int

SESSIONS="live_sessions"; PARTICIPANTS="live_participants"
STATUS_LOBI="lobi"; STATUS_SOAL="soal"; STATUS_JEDA="jeda"; STATUS_SELESAI="selesai"
DURASI_DEFAULT=20

# Kolom tambahan untuk mode "kelas live": kontrol kuis & pembagian soal per
# siswa. Materi/PDF & papan tulis sengaja TIDAK ada lagi di sini -- layar
# siswa cuma dua kondisi: menunggu (skor + papan peringkat gaya podium) atau
# lagi ngerjain kuis tahap tertentu. Soal kuis diambil langsung dari Bank
# Soal berdasarkan Kelas+Mapel+Bab, dikelompokkan per tahapan/checkpoint.
LIVE_EXTRA_COLUMNS = {
    "mode": "TEXT DEFAULT 'mengajar'",
    "quiz_enabled": "TEXT DEFAULT 'false'",
    "quiz_question_ids": "TEXT DEFAULT '[]'",
    "quiz_assignments": "TEXT DEFAULT '{}'",
    # "Kelas Hari Ini" ditujukan untuk jenjang/kelas tertentu (misal "Kelas 11"),
    # tapi siswa kelas lain tetap bisa ikut nebeng sementara -> lihat get_today_open_sessions().
    "target_kelas": "TEXT DEFAULT ''",
    # Sumber soal Live mengikuti Kelas+Mapel+Bab lalu Tahapan Materi.
    # Soal tanpa Tahapan Materi tidak boleh masuk ke sesi Live.
    "quiz_kelas": "TEXT DEFAULT ''",
    "quiz_mapel": "TEXT DEFAULT ''",
    "quiz_bab": "TEXT DEFAULT ''",
    # Nama "bagian/checkpoint" kuis yang sedang aktif (kalau dinyalakan lewat
    # tombol Kuis Cepat), cuma buat ditampilkan di layar, bukan sumber soal.
    "active_checkpoint": "TEXT DEFAULT ''",
    # Latihan UAS: pengajar dapat membekukan pengerjaan tanpa mengubah posisi soal siswa.
    "quiz_paused": "TEXT DEFAULT 'false'",
}

def ensure_live_participant_columns():
    try:
        cols = {str(r.get("name")) for r in fetch_all("PRAGMA table_info(live_participants)")}
        if "current_question_id" not in cols:
            execute("ALTER TABLE live_participants ADD COLUMN current_question_id TEXT DEFAULT ''")
    except Exception:
        pass

ensure_live_participant_columns()

def ensure_live_columns():
    try:
        cols = {str(r.get("name")) for r in fetch_all("PRAGMA table_info(live_sessions)")}
        for name, ddl in LIVE_EXTRA_COLUMNS.items():
            if name not in cols:
                execute(f"ALTER TABLE live_sessions ADD COLUMN {name} {ddl}")
    except Exception:
        # Pada database baru, tabel dibuat oleh schema yang sudah ada.
        pass

ensure_live_columns()

def _decode_session(d):
    if not d:return None
    d=dict(d); d["questions"]=json_loads(d.get("questions"), []); d["quiz_question_ids"]=json_loads(d.get("quiz_question_ids"), []); d["quiz_assignments"]=json_loads(d.get("quiz_assignments"), {}); d["quiz_enabled"]=str(d.get("quiz_enabled","false")).lower() in ("true","1","yes","on"); d["mode"]=d.get("mode") or "mengajar"; d["current_index"]=as_int(d.get("current_index"),-1); d["durasi_detik"]=as_int(d.get("durasi_detik"),DURASI_DEFAULT); d["target_kelas"]=d.get("target_kelas") or ""; d["quiz_kelas"]=d.get("quiz_kelas") or ""; d["quiz_mapel"]=d.get("quiz_mapel") or ""; d["quiz_bab"]=d.get("quiz_bab") or ""; d["active_checkpoint"]=d.get("active_checkpoint") or ""; return d

def _decode_participant(d):
    if not d:return None
    d=dict(d); d["jawaban"]=json_loads(d.get("jawaban"), {}); d["skor"]=as_int(d.get("skor"),0); d["current_question_id"]=d.get("current_question_id") or ""; return d

def _generate_kode():
    alfabet="ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        kode="".join(random.choice(alfabet) for _ in range(6))
        if not get_session_by_kode(kode):return kode

def create_session(admin_id,judul,mapel="",durasi_detik=DURASI_DEFAULT,target_kelas=""):
    sid=new_id(); data={"id":sid,"admin_id":admin_id,"judul":judul or "Kelas Hari Ini","mapel":mapel or "","target_kelas":target_kelas or "","kode":_generate_kode(),"status":STATUS_LOBI,"mode":"mengajar","quiz_enabled":False,"quiz_question_ids":[],"quiz_assignments":{},"quiz_kelas":"","quiz_mapel":"","quiz_bab":"","quiz_paused":False,"questions":[],"current_index":-1,"durasi_detik":int(durasi_detik) if durasi_detik else DURASI_DEFAULT,"current_started_at":None,"created_at":utcnow_iso()}
    execute("""INSERT INTO live_sessions (id,admin_id,judul,mapel,kode,status,questions,current_index,durasi_detik,current_started_at,created_at,mode,quiz_enabled,quiz_question_ids,quiz_assignments,target_kelas,quiz_kelas,quiz_mapel,quiz_bab,quiz_paused) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(sid,data["admin_id"],data["judul"],data["mapel"],data["kode"],data["status"],"[]",-1,data["durasi_detik"],None,data["created_at"],"mengajar","false","[]","{}",data["target_kelas"],"","","","false"))
    return data

def get_session(session_id):return _decode_session(fetch_one("SELECT * FROM live_sessions WHERE id=? LIMIT 1",(session_id,)))
def get_session_by_kode(kode):
    kode=(kode or "").strip().upper()
    if not kode:return None
    return _decode_session(fetch_one("SELECT * FROM live_sessions WHERE upper(kode)=? LIMIT 1",(kode,)))
def get_sessions_by_admin(admin_id):return sorted([_decode_session(x) for x in fetch_all("SELECT * FROM live_sessions WHERE admin_id=?",(admin_id,))],key=lambda x:str(x.get("created_at") or ""),reverse=True)
def delete_session(session_id):execute("DELETE FROM live_participants WHERE session_id=?",(session_id,)); execute("DELETE FROM live_sessions WHERE id=?",(session_id,))

WIB_OFFSET = datetime.timedelta(hours=7)

def _tanggal_wib(iso_str):
    """Ambil tanggal (YYYY-MM-DD) versi WIB dari timestamp UTC yang tersimpan
    di kolom created_at. Perlu ini karena semua timestamp di aplikasi disimpan
    dalam UTC, sementara pengguna beroperasi di WIB (UTC+7) -- tanpa geser ini,
    kelas yang dibuat jam 00:00-06:59 WIB akan dianggap "kemarin" begitu
    tanggal UTC berganti, dan hilang dari daftar Kelas Hari Ini."""
    s = str(iso_str or "")
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return (dt + WIB_OFFSET).date().isoformat()
    except ValueError:
        return s[:10]

def get_today_open_sessions(kelas_siswa=None):
    """Daftar 'Kelas Hari Ini' yang bisa di-browse siswa: dibuat hari ini dan
    belum berstatus selesai. Kelas yang jenjangnya cocok dengan kelas siswa
    ditaruh di paling atas, tapi siswa kelas lain tetap bisa lihat & gabung
    sementara (misal anak kelas 10 mau nyimak kelas 11)."""
    hari_ini = (datetime.datetime.now(datetime.timezone.utc) + WIB_OFFSET).date().isoformat()
    semua = [_decode_session(x) for x in fetch_all(
        "SELECT * FROM live_sessions WHERE status != ? ORDER BY created_at DESC", (STATUS_SELESAI,)
    )]
    semua = [s for s in semua if _tanggal_wib(s.get("created_at")) == hari_ini]

    def cocok(s):
        if not kelas_siswa or not s.get("target_kelas"):
            return 1
        return 0 if str(s.get("target_kelas")).strip().lower() == str(kelas_siswa).strip().lower() else 1

    return sorted(semua, key=cocok)

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

def start_class(session_id):
    sess=get_session(session_id)
    if not sess: return None
    execute("UPDATE live_sessions SET status=?,mode=?,current_index=?,current_started_at=? WHERE id=?",
            ("mengajar","mengajar",-1,None,session_id))
    return get_session(session_id)

def start_session(session_id):
    sess=get_session(session_id)
    if not sess or not sess.get("questions"):return None
    execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=?,mode=?,quiz_paused=? WHERE id=?",(STATUS_SOAL,0,utcnow_iso(),"kuis","false",session_id)); return get_session(session_id)

def advance_session(session_id):
    sess=get_session(session_id)
    if not sess:return None
    if sess["status"]==STATUS_SOAL:execute("UPDATE live_sessions SET status=? WHERE id=?",(STATUS_JEDA,session_id))
    elif sess["status"]==STATUS_JEDA:
        next_index=sess["current_index"]+1
        if next_index>=len(sess.get("questions") or []):
            # Pada Kelas Live, setelah kuis terakhir selesai kita kembali
            # otomatis ke mode menunggu (skor + podium), bukan menutup kelas.
            if sess.get("mode") == "kuis" or sess.get("quiz_enabled"):
                execute("UPDATE live_sessions SET status=?,mode=?,quiz_enabled=?,quiz_paused=?,active_checkpoint=?,current_started_at=? WHERE id=?",
                        ("mengajar","mengajar","false","false","",None,session_id))
            else:
                execute("UPDATE live_sessions SET status=?,quiz_paused=? WHERE id=?",(STATUS_SELESAI,"false",session_id))
        else:
            execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=? WHERE id=?",(STATUS_SOAL,next_index,utcnow_iso(),session_id))
    return get_session(session_id)
def end_session(session_id):execute("UPDATE live_sessions SET status=?,quiz_paused=? WHERE id=?",(STATUS_SELESAI,"false",session_id)); return get_session(session_id)
def end_quiz_to_teaching(session_id):
    execute("UPDATE live_sessions SET status=?,mode=?,quiz_enabled=?,quiz_paused=?,active_checkpoint=?,current_started_at=? WHERE id=?",
            ("mengajar","mengajar","false","false","",None,session_id))
    return get_session(session_id)
def reset_session(session_id):
    execute("UPDATE live_participants SET skor=?,jawaban=?,current_question_id=? WHERE session_id=?",(0,"{}","",session_id)); execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=?,mode=?,quiz_enabled=?,quiz_paused=?,active_checkpoint=? WHERE id=?",(STATUS_LOBI,-1,None,"mengajar","false","false","",session_id)); return get_session(session_id)
def _participant_id(session_id,user_id):return f"{session_id}__{user_id}"
def join_session(session_id,user_id,nama):
    pid=_participant_id(session_id,user_id); old=get_participant(session_id,user_id)
    if old:return old
    data={"id":pid,"session_id":session_id,"user_id":user_id,"nama":nama,"skor":0,"jawaban":{},"joined_at":utcnow_iso()}
    execute("INSERT INTO live_participants (id,session_id,user_id,nama,skor,jawaban,joined_at,current_question_id) VALUES (?,?,?,?,?,?,?,?)",(pid,session_id,user_id,nama,0,"{}",data["joined_at"],"")); return data
def get_participant(session_id,user_id):return _decode_participant(fetch_one("SELECT * FROM live_participants WHERE id=? LIMIT 1",(_participant_id(session_id,user_id),)))
def get_participants(session_id):return sorted([_decode_participant(x) for x in fetch_all("SELECT * FROM live_participants WHERE session_id=?",(session_id,))],key=lambda x:str(x.get("joined_at") or ""))
def get_leaderboard(session_id):return sorted(get_participants(session_id),key=lambda x:x.get("skor",0),reverse=True)
def _normalisasi_opsi(value):
    """Normalisasi kunci jawaban A-D agar penilaian live konsisten."""
    value = str(value or "").strip().upper()
    if value and value[0] in "ABCD":
        return value[0]
    return value


def hitung_skor(benar, waktu_ms=0, durasi_detik=DURASI_DEFAULT):
    """Latihan UAS tidak memakai timer: jawaban benar mendapat skor tetap."""
    return 1000 if benar else 0

def set_current_question(session_id, user_id, question_id):
    data = get_participant(session_id, user_id)
    if not data:
        return None, "Kamu belum join sesi ini."
    sess = get_session(session_id)
    if not sess or not sess.get("quiz_enabled"):
        return None, "Kuis belum aktif."
    order = (sess.get("quiz_assignments") or {}).get(user_id) or []
    if question_id not in order:
        return None, "Soal tidak tersedia untuk kamu."
    execute("UPDATE live_participants SET current_question_id=? WHERE id=?", (question_id, _participant_id(session_id,user_id)))
    return {"current_question_id": question_id}, None

def submit_answer(session_id,user_id,question_id,selected,waktu_ms=0):
    sess=get_session(session_id)
    if not sess:return None,"Sesi tidak ditemukan."
    if sess["status"]!=STATUS_SOAL or not sess.get("quiz_enabled"):return None,"Kuis sedang tidak aktif."
    if sess.get("quiz_paused"):return None,"Pengerjaan sedang dijeda oleh pengajar."
    questions=sess.get("questions") or []; q=next((x for x in questions if x["id"]==question_id),None)
    if not q:return None,"Soal tidak ditemukan."
    data=get_participant(session_id,user_id)
    if not data:return None,"Kamu belum join sesi ini."
    order=(sess.get("quiz_assignments") or {}).get(user_id) or []
    if question_id not in order:return None,"Soal ini tidak tersedia untuk kamu."
    jawaban=data.get("jawaban") or {}
    if question_id in jawaban:return jawaban[question_id],None
    selected = _normalisasi_opsi(selected)
    kunci = _normalisasi_opsi(q.get("jawaban_benar"))
    benar=selected==kunci; skor_soal=hitung_skor(benar,0,0)
    hasil={"selected":selected,"benar":benar,"skor":skor_soal,"waktu_ms":0}; jawaban[question_id]=hasil
    execute("UPDATE live_participants SET jawaban=?,skor=? WHERE id=?",(json_dumps(jawaban),data.get("skor",0)+skor_soal,_participant_id(session_id,user_id))); return hasil,None


def set_quiz_paused(session_id, paused):
    execute("UPDATE live_sessions SET quiz_paused=? WHERE id=?", ("true" if paused else "false", session_id))
    return get_session(session_id)

def set_quiz_source(session_id, kelas, mapel, bab):
    """Set konteks sumber soal Live. Tahapan Materi tetap menjadi relasi soal;
    field ini hanya menyimpan Kelas+Mapel+Bab yang sedang dibuka di lobi."""
    execute("UPDATE live_sessions SET quiz_kelas=?, quiz_mapel=?, quiz_bab=? WHERE id=?",
            (kelas or "", mapel or "", bab or "", session_id))
    return get_session(session_id)

def set_quiz_enabled(session_id, enabled):
    execute("UPDATE live_sessions SET quiz_enabled=? WHERE id=?",
            ("true" if enabled else "false", session_id))
    return get_session(session_id)

def set_quiz_questions(session_id, questions):
    ids=[q.get("id") for q in (questions or []) if q.get("id")]
    execute("UPDATE live_sessions SET questions=?, quiz_question_ids=? WHERE id=?",
            (json_dumps(questions or []), json_dumps(ids), session_id))

def set_quiz_assignments(session_id, assignments):
    execute("UPDATE live_sessions SET quiz_assignments=? WHERE id=?", (json_dumps(assignments or {}), session_id))

def activate_checkpoint_quiz(session_id, checkpoint, questions, target_user_ids, acak_per_siswa=False):
    """Nyalakan kuis untuk SATU Tahapan Materi. Urutan soal yang dikirim route
    dipertahankan sama untuk semua siswa; tidak ada pengacakan per siswa."""
    if not questions or not target_user_ids:
        return None
    set_quiz_questions(session_id, questions)
    assignments = {}
    order_base = [q["id"] for q in questions]
    for uid in target_user_ids:
        # Semua siswa mendapat urutan yang sama persis. Parameter lama tetap
        # diterima agar sesi/database lama tidak rusak, tetapi tidak dipakai.
        assignments[uid] = list(order_base)
    set_quiz_assignments(session_id, assignments)
    execute("UPDATE live_sessions SET active_checkpoint=? WHERE id=?", ((checkpoint or "").strip(), session_id))
    set_quiz_enabled(session_id, True)
    start_session(session_id)
    return get_session(session_id)