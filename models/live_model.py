"""
Model untuk fitur "Latihan Soal Live" (gaya Kahoot):
  - Admin bikin SATU sesi live, isi soal pilgan (pertanyaan + pilihan A-D + jawaban
    benar) langsung di sesi itu -- terpisah dari Bank Soal biasa, jadi gak nyampur.
  - Sesi dapat KODE unik (6 karakter) yang dibagikan ke siswa buat join.
  - Admin yang kontrol jalannya soal (mulai, tampilkan jawaban, soal berikutnya),
    semua siswa yang join lihat soal yang SAMA secara bersamaan.
  - Siswa dapat skor tiap soal: makin cepat & benar, makin gede skornya (mirip Kahoot).

Kenapa polling, bukan WebSocket: app ini di-deploy sebagai serverless function
(lihat vercel.json), jadi gak ada proses yang nyala terus buat pegang koneksi
WebSocket. Sinkronisasi "live"-nya dilakukan lewat status tersimpan di Firestore
yang di-poll berkala oleh browser admin & siswa (lihat live_admin.js / live_siswa.js).
"""
import datetime
import random
import string

from firebase_config import db

SESSIONS = "live_sessions"
PARTICIPANTS = "live_participants"

STATUS_LOBI = "lobi"          # sesi dibuat, siswa boleh join, belum mulai
STATUS_SOAL = "soal"          # satu soal lagi aktif, siswa lagi jawab, timer jalan
STATUS_JEDA = "jeda"          # soal ditutup, jawaban benar + leaderboard sementara ditampilkan
STATUS_SELESAI = "selesai"    # sesi sudah berakhir, leaderboard final

DURASI_DEFAULT = 20  # detik per soal


def _doc(doc):
    d = doc.to_dict()
    d["id"] = doc.id
    return d


def _generate_kode():
    """Kode 6 huruf/angka kapital, gampang didikte lisan di kelas."""
    alfabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # tanpa O/0/I/1 biar gak ketuker
    while True:
        kode = "".join(random.choice(alfabet) for _ in range(6))
        if not get_session_by_kode(kode):
            return kode


def create_session(admin_id, judul, mapel="", durasi_detik=DURASI_DEFAULT):
    ref = db.collection(SESSIONS).document()
    data = {
        "admin_id": admin_id,
        "judul": judul or "Latihan Soal Live",
        "mapel": mapel or "",
        "kode": _generate_kode(),
        "status": STATUS_LOBI,
        "questions": [],          # list of {id, pertanyaan, pilihan:[a,b,c,d], jawaban_benar, penjelasan}
        "current_index": -1,
        "durasi_detik": int(durasi_detik) if durasi_detik else DURASI_DEFAULT,
        "current_started_at": None,
        "created_at": datetime.datetime.utcnow(),
    }
    ref.set(data)
    data["id"] = ref.id
    return data


def get_session(session_id):
    d = db.collection(SESSIONS).document(session_id).get()
    return _doc(d) if d.exists else None


def get_session_by_kode(kode):
    kode = (kode or "").strip().upper()
    if not kode:
        return None
    q = db.collection(SESSIONS).where("kode", "==", kode).limit(1).stream()
    for d in q:
        return _doc(d)
    return None


def get_sessions_by_admin(admin_id):
    out = [_doc(d) for d in db.collection(SESSIONS).where("admin_id", "==", admin_id).stream()]
    return sorted(out, key=lambda x: str(x.get("created_at") or ""), reverse=True)


def delete_session(session_id):
    for d in db.collection(PARTICIPANTS).where("session_id", "==", session_id).stream():
        d.reference.delete()
    db.collection(SESSIONS).document(session_id).delete()


def add_question(session_id, pertanyaan, pilihan, jawaban_benar, penjelasan=""):
    """Nambah SATU soal ke sesi. Dipanggil berkali-kali dari form input soal
    (satu form, satu soal, sama kayak alur Bank Soal biasa) sebelum sesi dimulai."""
    sess = get_session(session_id)
    if not sess:
        return None
    questions = sess.get("questions") or []
    qid = f"q{len(questions) + 1}_{int(datetime.datetime.utcnow().timestamp())}"
    questions.append({
        "id": qid,
        "pertanyaan": pertanyaan,
        "pilihan": pilihan,
        "jawaban_benar": jawaban_benar,
        "penjelasan": penjelasan or "",
    })
    db.collection(SESSIONS).document(session_id).update({"questions": questions})
    return qid


def add_questions_bulk(session_id, soal_list):
    """Nambah BANYAK soal sekaligus (dipakai fitur impor massal). `soal_list` = list
    of dict {pertanyaan, pilihan:[a,b,c,d], jawaban_benar, penjelasan(optional)}."""
    sess = get_session(session_id)
    if not sess:
        return 0
    questions = sess.get("questions") or []
    base = len(questions)
    now_ts = int(datetime.datetime.utcnow().timestamp())
    for i, soal in enumerate(soal_list):
        qid = f"q{base + i + 1}_{now_ts}_{i}"
        questions.append({
            "id": qid,
            "pertanyaan": soal["pertanyaan"],
            "pilihan": soal["pilihan"],
            "jawaban_benar": soal["jawaban_benar"],
            "penjelasan": soal.get("penjelasan", "") or "",
        })
    db.collection(SESSIONS).document(session_id).update({"questions": questions})
    return len(soal_list)


def delete_question(session_id, question_id):
    sess = get_session(session_id)
    if not sess:
        return
    questions = [q for q in (sess.get("questions") or []) if q.get("id") != question_id]
    db.collection(SESSIONS).document(session_id).update({"questions": questions})


def start_session(session_id):
    """Mulai sesi: soal nomor 1 langsung aktif & timer mulai jalan."""
    sess = get_session(session_id)
    if not sess or not sess.get("questions"):
        return None
    db.collection(SESSIONS).document(session_id).update({
        "status": STATUS_SOAL,
        "current_index": 0,
        "current_started_at": datetime.datetime.now(datetime.timezone.utc),
    })
    return get_session(session_id)


def advance_session(session_id):
    """Satu tombol admin "Lanjut" yang berperilaku dua tahap, mirip Kahoot:
    - kalau lagi status SOAL  -> tutup soal ini, pindah ke JEDA (reveal jawaban + leaderboard)
    - kalau lagi status JEDA  -> lanjut ke soal berikutnya (atau SELESAI kalau sudah abis)
    """
    sess = get_session(session_id)
    if not sess:
        return None
    ref = db.collection(SESSIONS).document(session_id)
    if sess["status"] == STATUS_SOAL:
        ref.update({"status": STATUS_JEDA})
    elif sess["status"] == STATUS_JEDA:
        next_index = sess["current_index"] + 1
        if next_index >= len(sess.get("questions") or []):
            ref.update({"status": STATUS_SELESAI})
        else:
            ref.update({
                "status": STATUS_SOAL,
                "current_index": next_index,
                "current_started_at": datetime.datetime.now(datetime.timezone.utc),
            })
    return get_session(session_id)


def end_session(session_id):
    db.collection(SESSIONS).document(session_id).update({"status": STATUS_SELESAI})
    return get_session(session_id)


def reset_session(session_id):
    """Ulang dari lobi lagi (soal & peserta tetap, skor & jawaban dihapus)."""
    for d in db.collection(PARTICIPANTS).where("session_id", "==", session_id).stream():
        d.reference.update({"skor": 0, "jawaban": {}})
    db.collection(SESSIONS).document(session_id).update({
        "status": STATUS_LOBI,
        "current_index": -1,
        "current_started_at": None,
    })
    return get_session(session_id)


def _participant_id(session_id, user_id):
    return f"{session_id}__{user_id}"


def join_session(session_id, user_id, nama):
    ref = db.collection(PARTICIPANTS).document(_participant_id(session_id, user_id))
    snap = ref.get()
    if snap.exists:
        return snap.to_dict()
    data = {
        "session_id": session_id,
        "user_id": user_id,
        "nama": nama,
        "skor": 0,
        "jawaban": {},  # question_id -> {selected, benar, skor, waktu_ms}
        "joined_at": datetime.datetime.utcnow(),
    }
    ref.set(data)
    return data


def get_participant(session_id, user_id):
    d = db.collection(PARTICIPANTS).document(_participant_id(session_id, user_id)).get()
    return d.to_dict() if d.exists else None


def get_participants(session_id):
    out = [_doc(d) for d in db.collection(PARTICIPANTS).where("session_id", "==", session_id).stream()]
    return sorted(out, key=lambda x: str(x.get("joined_at") or ""))


def get_leaderboard(session_id):
    out = get_participants(session_id)
    return sorted(out, key=lambda x: x.get("skor", 0), reverse=True)


def hitung_skor(benar, waktu_ms, durasi_detik):
    """Skor gaya Kahoot: benar = 500 dasar + bonus kecepatan sampai 500 lagi
    (makin cepat jawab dari total waktu yang tersedia, bonusnya makin gede)."""
    if not benar:
        return 0
    durasi_ms = max(1, durasi_detik * 1000)
    sisa_rasio = max(0.0, min(1.0, 1 - (waktu_ms / durasi_ms)))
    return int(500 + round(500 * sisa_rasio))


def submit_answer(session_id, user_id, question_id, selected, waktu_ms):
    sess = get_session(session_id)
    if not sess:
        return None, "Sesi tidak ditemukan."
    if sess["status"] != STATUS_SOAL:
        return None, "Soal ini sudah ditutup."
    questions = sess.get("questions") or []
    q = next((x for x in questions if x["id"] == question_id), None)
    if not q:
        return None, "Soal tidak ditemukan."
    idx = sess.get("current_index", -1)
    if idx < 0 or idx >= len(questions) or questions[idx]["id"] != question_id:
        return None, "Soal ini bukan soal yang sedang aktif."

    ref = db.collection(PARTICIPANTS).document(_participant_id(session_id, user_id))
    snap = ref.get()
    if not snap.exists:
        return None, "Kamu belum join sesi ini."
    data = snap.to_dict()
    jawaban = data.get("jawaban") or {}
    if question_id in jawaban:
        return jawaban[question_id], None  # sudah pernah jawab, idempotent

    benar = selected == q.get("jawaban_benar")
    waktu_ms = max(0, int(waktu_ms or 0))
    skor_soal = hitung_skor(benar, waktu_ms, sess.get("durasi_detik", DURASI_DEFAULT))
    hasil = {"selected": selected, "benar": benar, "skor": skor_soal, "waktu_ms": waktu_ms}
    jawaban[question_id] = hasil
    ref.update({"jawaban": jawaban, "skor": data.get("skor", 0) + skor_soal})
    return hasil, None
