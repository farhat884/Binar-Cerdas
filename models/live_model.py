"""Model Live Quiz backed by Turso/libSQL."""
import datetime, random
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso, json_dumps, json_loads, as_int

SESSIONS="live_sessions"; PARTICIPANTS="live_participants"
STATUS_LOBI="lobi"; STATUS_SOAL="soal"; STATUS_JEDA="jeda"; STATUS_SELESAI="selesai"
DURASI_DEFAULT=20

# Kolom tambahan untuk mode "kelas live": papan tulis bersama, izin coret
# siswa, kontrol kuis, dan pembagian soal per siswa. Materi/PDF sengaja TIDAK
# ada lagi di sini -- layar siswa sekarang cuma papan tulis (pas dinyalakan
# admin) atau skor+peringkat, dan soal kuis diambil langsung dari Bank Soal
# berdasarkan Kelas+Mapel+Bab, bukan ditautkan ke materi.
LIVE_EXTRA_COLUMNS = {
    "mode": "TEXT DEFAULT 'mengajar'",
    "drawing": "TEXT DEFAULT '[]'",
    "student_draw_enabled": "TEXT DEFAULT 'false'",
    # Daftar user_id siswa yang diizinkan mencoret di papan tulis. Diatur
    # pengajar KAPAN SAJA selagi kelas berlangsung (bukan pas lobi), dan
    # pengajar pilih sendiri siapa yang boleh -- bukan on/off buat semua.
    "draw_allowed_ids": "TEXT DEFAULT '[]'",
    # Saklar utama papan tulis: nyala -> otomatis tampil ke layar SEMUA siswa
    # (siapa yang boleh ikut nyoret tetap diatur terpisah lewat draw_allowed_ids).
    "papan_aktif": "TEXT DEFAULT 'false'",
    "quiz_enabled": "TEXT DEFAULT 'false'",
    "quiz_question_ids": "TEXT DEFAULT '[]'",
    "quiz_assignments": "TEXT DEFAULT '{}'",
    # "Kelas Hari Ini" ditujukan untuk jenjang/kelas tertentu (misal "Kelas 11"),
    # tapi siswa kelas lain tetap bisa ikut nebeng sementara -> lihat get_today_open_sessions().
    "target_kelas": "TEXT DEFAULT ''",
    # Sumber soal buat "Kuis Cepat" per-checkpoint: dipilih dari Bank Soal
    # lewat Kelas+Mapel+Bab langsung (bukan ditautkan ke tahapan materi lagi).
    "quiz_kelas": "TEXT DEFAULT ''",
    "quiz_mapel": "TEXT DEFAULT ''",
    "quiz_bab": "TEXT DEFAULT ''",
    # Nama "bagian/checkpoint" kuis yang sedang aktif (kalau dinyalakan lewat
    # tombol Kuis Cepat), cuma buat ditampilkan di layar, bukan sumber soal.
    "active_checkpoint": "TEXT DEFAULT ''",
}

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
    d=dict(d); d["questions"]=json_loads(d.get("questions"), []); d["drawing"]=json_loads(d.get("drawing"), []); d["quiz_question_ids"]=json_loads(d.get("quiz_question_ids"), []); d["quiz_assignments"]=json_loads(d.get("quiz_assignments"), {}); d["student_draw_enabled"]=str(d.get("student_draw_enabled","false")).lower() in ("true","1","yes","on"); d["quiz_enabled"]=str(d.get("quiz_enabled","false")).lower() in ("true","1","yes","on"); d["papan_aktif"]=str(d.get("papan_aktif","false")).lower() in ("true","1","yes","on"); d["mode"]=d.get("mode") or "mengajar"; d["current_index"]=as_int(d.get("current_index"),-1); d["durasi_detik"]=as_int(d.get("durasi_detik"),DURASI_DEFAULT); d["target_kelas"]=d.get("target_kelas") or ""; d["quiz_kelas"]=d.get("quiz_kelas") or ""; d["quiz_mapel"]=d.get("quiz_mapel") or ""; d["quiz_bab"]=d.get("quiz_bab") or ""; d["active_checkpoint"]=d.get("active_checkpoint") or ""; d["draw_allowed_ids"]=json_loads(d.get("draw_allowed_ids"), []); return d

def _decode_participant(d):
    if not d:return None
    d=dict(d); d["jawaban"]=json_loads(d.get("jawaban"), {}); d["skor"]=as_int(d.get("skor"),0); return d

def _generate_kode():
    alfabet="ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        kode="".join(random.choice(alfabet) for _ in range(6))
        if not get_session_by_kode(kode):return kode

def create_session(admin_id,judul,mapel="",durasi_detik=DURASI_DEFAULT,target_kelas=""):
    sid=new_id(); data={"id":sid,"admin_id":admin_id,"judul":judul or "Kelas Hari Ini","mapel":mapel or "","target_kelas":target_kelas or "","kode":_generate_kode(),"status":STATUS_LOBI,"mode":"mengajar","drawing":[],"student_draw_enabled":False,"papan_aktif":False,"quiz_enabled":False,"quiz_question_ids":[],"quiz_assignments":{},"quiz_kelas":"","quiz_mapel":"","quiz_bab":"","questions":[],"current_index":-1,"durasi_detik":int(durasi_detik) if durasi_detik else DURASI_DEFAULT,"current_started_at":None,"created_at":utcnow_iso()}
    execute("""INSERT INTO live_sessions (id,admin_id,judul,mapel,kode,status,questions,current_index,durasi_detik,current_started_at,created_at,mode,drawing,student_draw_enabled,papan_aktif,quiz_enabled,quiz_question_ids,quiz_assignments,target_kelas,quiz_kelas,quiz_mapel,quiz_bab) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(sid,data["admin_id"],data["judul"],data["mapel"],data["kode"],data["status"],"[]",-1,data["durasi_detik"],None,data["created_at"],"mengajar","[]","false","false","false","[]","{}",data["target_kelas"],"","",""))
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
    execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=?,mode=? WHERE id=?",(STATUS_SOAL,0,utcnow_iso(),"kuis",session_id)); return get_session(session_id)

def advance_session(session_id):
    sess=get_session(session_id)
    if not sess:return None
    if sess["status"]==STATUS_SOAL:execute("UPDATE live_sessions SET status=? WHERE id=?",(STATUS_JEDA,session_id))
    elif sess["status"]==STATUS_JEDA:
        next_index=sess["current_index"]+1
        if next_index>=len(sess.get("questions") or []):
            # Pada Kelas Live, setelah kuis terakhir selesai kita kembali
            # otomatis ke papan/materi, bukan menutup kelas.
            if sess.get("mode") == "kuis" or sess.get("quiz_enabled"):
                execute("UPDATE live_sessions SET status=?,mode=?,quiz_enabled=?,active_checkpoint=?,current_started_at=? WHERE id=?",
                        ("mengajar","mengajar","false","",None,session_id))
            else:
                execute("UPDATE live_sessions SET status=? WHERE id=?",(STATUS_SELESAI,session_id))
        else:
            execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=? WHERE id=?",(STATUS_SOAL,next_index,utcnow_iso(),session_id))
    return get_session(session_id)
def end_session(session_id):execute("UPDATE live_sessions SET status=? WHERE id=?",(STATUS_SELESAI,session_id)); return get_session(session_id)
def end_quiz_to_teaching(session_id):
    execute("UPDATE live_sessions SET status=?,mode=?,quiz_enabled=?,active_checkpoint=?,current_started_at=? WHERE id=?",
            ("mengajar","mengajar","false","",None,session_id))
    return get_session(session_id)
def reset_session(session_id):
    execute("UPDATE live_participants SET skor=?,jawaban=? WHERE session_id=?",(0,"{}",session_id)); execute("UPDATE live_sessions SET status=?,current_index=?,current_started_at=?,mode=?,quiz_enabled=?,active_checkpoint=?,papan_aktif=? WHERE id=?",(STATUS_LOBI,-1,None,"mengajar","false","","false",session_id)); return get_session(session_id)
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
    if idx<0 or idx>=len(questions):return None,"Soal ini bukan soal yang sedang aktif."
    # Tiap siswa bisa punya urutan soal sendiri (diacak per-siswa) lewat
    # quiz_assignments -- jadi soal "aktif" buat siswa ITU belum tentu sama
    # dengan questions[idx] (urutan global/default). Validasi harus pakai
    # urutan milik siswa itu sendiri kalau ada, baru fallback ke urutan
    # global kalau siswa itu gak punya assignment (mode lama/tanpa acak).
    order=(sess.get("quiz_assignments") or {}).get(user_id)
    expected_id=order[idx] if order and 0<=idx<len(order) else questions[idx]["id"]
    if expected_id!=question_id:return None,"Soal ini bukan soal yang sedang aktif."
    data=get_participant(session_id,user_id)
    if not data:return None,"Kamu belum join sesi ini."
    jawaban=data.get("jawaban") or {}
    if question_id in jawaban:return jawaban[question_id],None
    benar=selected==q.get("jawaban_benar"); waktu_ms=max(0,int(waktu_ms or 0)); skor_soal=hitung_skor(benar,waktu_ms,sess.get("durasi_detik",DURASI_DEFAULT)); hasil={"selected":selected,"benar":benar,"skor":skor_soal,"waktu_ms":waktu_ms}; jawaban[question_id]=hasil
    execute("UPDATE live_participants SET jawaban=?,skor=? WHERE id=?",(json_dumps(jawaban),data.get("skor",0)+skor_soal,_participant_id(session_id,user_id))); return hasil,None



def set_quiz_source(session_id, kelas, mapel, bab):
    """Set sumber soal 'Kuis Cepat' untuk kelas ini lewat Kelas+Mapel+Bab
    langsung dari Bank Soal (bukan ditautkan ke materi/tahapan lagi).
    Cuma boleh diubah selagi sesi masih di lobi -- lihat pengecekan di
    routes/live_routes.py:kelas_config()."""
    execute("UPDATE live_sessions SET quiz_kelas=?, quiz_mapel=?, quiz_bab=? WHERE id=?",
            (kelas or "", mapel or "", bab or "", session_id))
    return get_session(session_id)

def set_draw_allowed(session_id, user_ids):
    """Set daftar siswa yang diizinkan mencoret di papan tulis saat ini.
    Dipanggil pengajar kapan saja selama kelas berjalan; menggantikan
    seluruh daftar sebelumnya (bukan nambah satu-satu)."""
    execute("UPDATE live_sessions SET draw_allowed_ids=? WHERE id=?",
            (json_dumps(list(dict.fromkeys(user_ids or []))), session_id))
    return get_session(session_id)

def set_papan_aktif(session_id, aktif):
    """Saklar utama papan tulis. Nyala -> layar SEMUA siswa otomatis pindah
    nampilin papan tulis (lewat polling /status), gantiin tampilan materi
    yang sudah dihapus. Mati & kuis lagi gak aktif -> siswa balik lihat
    skor + papan peringkat (lihat routes/live_routes.py:status())."""
    execute("UPDATE live_sessions SET papan_aktif=? WHERE id=?",
            ("true" if aktif else "false", session_id))
    return get_session(session_id)

def set_student_draw(session_id, enabled):
    execute("UPDATE live_sessions SET student_draw_enabled=? WHERE id=?",
            ("true" if enabled else "false", session_id))
    return get_session(session_id)

def set_quiz_enabled(session_id, enabled):
    execute("UPDATE live_sessions SET quiz_enabled=? WHERE id=?",
            ("true" if enabled else "false", session_id))
    return get_session(session_id)

def set_drawing(session_id, drawing):
    execute("UPDATE live_sessions SET drawing=? WHERE id=?", (json_dumps(drawing or []), session_id))

def add_drawing_stroke(session_id, stroke):
    sess=get_session(session_id)
    if not sess: return
    drawing=sess.get("drawing") or []
    drawing.append(stroke)
    # Batasi agar payload tidak tumbuh tanpa batas.
    drawing=drawing[-2000:]
    set_drawing(session_id, drawing)

def clear_drawing(session_id):
    set_drawing(session_id, [])

def set_quiz_questions(session_id, questions):
    ids=[q.get("id") for q in (questions or []) if q.get("id")]
    execute("UPDATE live_sessions SET questions=?, quiz_question_ids=? WHERE id=?",
            (json_dumps(questions or []), json_dumps(ids), session_id))

def set_quiz_assignments(session_id, assignments):
    execute("UPDATE live_sessions SET quiz_assignments=? WHERE id=?", (json_dumps(assignments or {}), session_id))

def activate_checkpoint_quiz(session_id, checkpoint, questions, target_user_ids, acak_per_siswa=True):
    """Nyalain 'Kuis Cepat' buat SATU bagian/checkpoint, kapan pun saat kelas
    sedang berjalan (bukan cuma waktu lobi) -- gaya Ruang Guru: pengajar lagi
    ngejelasin, tiba-tiba nyalain kuis singkat soal bagian yang barusan
    dibahas. `questions` sudah berupa hasil random-pick DARI BANK SOAL saat
    tombol ini diklik, jadi tiap kali dinyalakan (walau checkpoint yang sama)
    soalnya bisa beda -- cuma tipe/bagiannya yang sama."""
    if not questions or not target_user_ids:
        return None
    set_quiz_questions(session_id, questions)
    assignments = {}
    order_base = [q["id"] for q in questions]
    for uid in target_user_ids:
        order = list(order_base)
        if acak_per_siswa:
            random.shuffle(order)
        assignments[uid] = order
    set_quiz_assignments(session_id, assignments)
    execute("UPDATE live_sessions SET active_checkpoint=? WHERE id=?", ((checkpoint or "").strip(), session_id))
    set_quiz_enabled(session_id, True)
    start_session(session_id)
    return get_session(session_id)