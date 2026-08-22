"""Penjelasan AI. Simpan GROQ_API_KEY hanya di environment variable."""
import os, re, sys, traceback
import requests

ATURAN_FORMAT = (
    "ATURAN FORMAT PENTING: tulis sebagai teks biasa saja. "
    "JANGAN pakai markdown (jangan pakai tanda bintang **, tanda pagar #, atau tabel). "
    "JANGAN pakai notasi LaTeX (jangan pakai \\(, \\), \\[, \\], atau \\begin). "
    "Tulis pangkat dengan cara biasa, misalnya x^4 atau x pangkat 4, bukan notasi matematika khusus. "
    "Kalau perlu langkah bernomor, tulis seperti '1) ...' lalu ganti baris (enter) sebelum nomor berikutnya, "
    "jangan digabung jadi satu paragraf panjang."
)

GAYA_BICARA = (
    "Kamu berperan sebagai tutor yang santai dan asyik, ngomong LANGSUNG ke siswanya pakai 'kamu' "
    "(bukan nulis laporan analisis pakai kata 'siswa'). Boleh pakai kata-kata santai kayak 'nih', 'yuk', "
    "'gapapa', tapi tetap sopan dan jelas, jangan kaku atau terlalu formal. "
    "Kalau jawabannya salah, sampaikan dengan santai dan gak bikin down, misalnya gaya 'jawaban kamu masih "
    "kurang tepat nih, tapi gapapa yuk kita bahas', baru lanjut jelasin letak kesalahan dan cara yang benar."
)


def _bersihkan_format(teks):
    """Buang sisa markdown/LaTeX kalau AI masih kebawa nulisnya, biar tampil rapi sebagai teks biasa."""
    if not teks:
        return teks
    teks = re.sub(r"\\\((.*?)\\\)", r"\1", teks)
    teks = re.sub(r"\\\[(.*?)\\\]", r"\1", teks, flags=re.S)
    teks = re.sub(r"\\begin\{.*?\}|\\end\{.*?\}", "", teks)
    teks = teks.replace("&", " ").replace("\\quad", "  ")
    teks = re.sub(r"\*\*(.*?)\*\*", r"\1", teks)
    teks = re.sub(r"(?<!\d)\*(?!\d)", "", teks)
    teks = re.sub(r"[ \t]+", " ", teks)
    teks = re.sub(r"\n{3,}", "\n\n", teks)
    return teks.strip()


def _panggil_groq(messages, fallback):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return fallback

    payload = {
        "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
        "messages": messages,
        "temperature": 0.4,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; BinarCerdas/1.0; +https://binarcerdas.app)",
        "Accept": "application/json",
    }
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=20,
        )
        if not r.ok:
            print(f"[ai_service] Groq HTTPError {r.status_code}: {r.text[:500]}", file=sys.stderr)
            return fallback
        data = r.json()
        return _bersihkan_format(data["choices"][0]["message"]["content"].strip())
    except Exception as e:
        print(f"[ai_service] Groq call failed: {repr(e)}", file=sys.stderr)
        traceback.print_exc()
        return fallback


def explain_answer(question, selected, correct, fallback="", benar=None):
    fallback_final = fallback or f"Jawaban yang benar adalah {correct}. Coba periksa kembali konsep utama pada materi ini."
    if not os.environ.get("GROQ_API_KEY"):
        return fallback_final

    status = (
        "Jawaban kamu BENAR! Konfirmasi itu dengan santai, lalu tetap jelasin langkah/konsep penyelesaiannya "
        "supaya pemahamannya makin kuat, misalnya kenapa tiap suku/bagian ditambah, dikurangi, atau dipakai seperti itu."
        if benar is True else
        "Jawaban kamu SALAH. Sampaikan dengan santai dan gak bikin down, lalu jelasin letak kesalahannya dan "
        "langkah penyelesaian yang benar secara runtut."
        if benar is False else
        "Jelaskan mengapa jawaban berikut benar atau salah."
    )
    prompt = (
        f"{GAYA_BICARA} {status} "
        f"Soal: {question}. Jawaban siswa: {selected}. Jawaban benar: {correct}. "
        "Maksimal 180 kata, fokus pada konsep dan langkah penyelesaian, bukan cuma menyebut benar/salah. "
        f"{ATURAN_FORMAT}"
    )
    messages = [{"role": "user", "content": prompt}]
    return _panggil_groq(messages, fallback_final)


def tanya_lanjutan(question, selected, correct, benar, riwayat, pesan_baru):
    """Chat lanjutan kalau siswa masih mau tanya-tanya soal penjelasannya."""
    fallback = "Maaf, AI-nya lagi belum bisa jawab pertanyaan ini. Coba tanya lagi sebentar lagi, ya."
    if not os.environ.get("GROQ_API_KEY"):
        return fallback

    status_benar = "benar" if benar else "salah"
    system_content = (
        f"{GAYA_BICARA} Kamu sedang chat singkat sama siswa buat bantu dia paham soal ini. Boleh nanya balik "
        "kalau perlu biar makin jelas, tapi tetap fokus ke soal ini aja, jangan melenceng ke topik lain. "
        f"Konteks soal: {question}. Jawaban siswa waktu itu: {selected}. Jawaban yang benar: {correct}. "
        f"Jawaban siswa tadi {status_benar}. "
        "Jawab tiap pesan maksimal sekitar 100 kata. "
        f"{ATURAN_FORMAT}"
    )
    messages = [{"role": "system", "content": system_content}]
    for m in (riwayat or [])[-8:]:
        role = m.get("role") if m.get("role") in ("user", "assistant") else "user"
        content = str(m.get("content", ""))[:1000]
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": str(pesan_baru)[:1000]})

    return _panggil_groq(messages, fallback)