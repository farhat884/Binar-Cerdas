"""Penjelasan AI. Simpan GROQ_API_KEY hanya di environment variable."""
import os, re, sys, traceback
import requests

ATURAN_FORMAT = (
    "ATURAN FORMAT PENTING: tulis sebagai teks biasa saja, tapi tetap pakai simbol matematika standar "
    "biar kelihatan rapi kayak di buku pelajaran, jangan kaku kayak nulis kode program. "
    "JANGAN pakai markdown (jangan pakai tanda bintang **, tanda pagar #, atau tabel). "
    "JANGAN pakai notasi/perintah LaTeX APAPUN (jangan pakai \\(, \\), \\[, \\], \\begin, \\frac, \\sqrt, "
    "\\Rightarrow, \\le, \\ge, \\neq, \\times, \\cdot, \\div, \\; , \\, , \\! , atau perintah backslash lainnya). "
    "Untuk tanda panah/kesimpulan pakai kata biasa kayak 'maka' atau 'jadi', BUKAN \\Rightarrow. "
    "Untuk kurang dari/lebih dari/sama dengan pakai simbol biasa <, >, =, ≤, ≥ yang diketik langsung, BUKAN "
    "\\le atau \\geq. "
    "Untuk PANGKAT: langsung tulis angka ATAU variabelnya kecil di atas (superscript unicode), contoh x², 5³, "
    "aⁿ, atau x⁽²ⁿ⁺¹⁾ untuk pangkat gabungan. "
    "JANGAN PERNAH pakai tanda caret seperti x^2 atau a^n, dan jangan nulis 'x pangkat 2' pakai kata-kata biasa. "
    "Untuk PERKALIAN pakai tanda ×, jangan pakai tanda bintang *. "
    "Untuk PEMBAGIAN/PECAHAN pakai tanda garis miring wajar seperti 3/4 (tanpa spasi berlebihan di kanan-kiri), "
    "atau tanda ÷ untuk operasi pembagian bilangan bulat, misalnya 12 ÷ 4 = 3. "
    "KHUSUS PEMBAGIAN BERSUSUN/POROGAPIT: JANGAN coba gambar kotak/tabel/garis panjang pakai karakter seperti "
    "_, |, atau strip berulang, soalnya bakal berantakan di layar HP. Jelaskan tiap langkahnya berurutan pakai "
    "kalimat singkat dan angka biasa, misal '1) 24 dibagi 6 dari digit pertama dulu, hasilnya 4' lalu ganti baris "
    "ke langkah berikutnya, bukan digambar sebagai tabel pembagian bersusun. "
    "Untuk AKAR pakai simbol √, misalnya √16 = 4. "
    "Kalau perlu langkah bernomor, tulis seperti '1) ...' lalu ganti baris (enter) sebelum nomor berikutnya, "
    "jangan digabung jadi satu paragraf panjang. "
    "KHUSUS MATRIKS: ini SATU-SATUNYA pengecualian boleh pakai notasi LaTeX (di luar ini tetap ikuti aturan "
    "'jangan pakai LaTeX' di atas). Kalau soal atau penjelasan butuh nampilin matriks, JANGAN ditulis manual "
    "pakai kurung siku teks biasa kayak [[1,2],[3,4]] soalnya keliatan kayak kode program, bukan matriks "
    "matematika. Tulis pakai format: \\[\\begin{bmatrix}1 & 2\\\\3 & 4\\end{bmatrix}\\] — baris dipisah tanda "
    "\\\\ dan kolom dipisah tanda &, itu bakal otomatis dirender jadi matriks berkurung siku yang rapi kayak di "
    "buku pelajaran. Selalu bungkus dengan \\[ dan \\] persis seperti contoh itu."
)

GAYA_BICARA = (
    "Kamu berperan sebagai tutor yang santai dan asyik, ngomong LANGSUNG ke siswanya pakai 'kamu' "
    "(bukan nulis laporan analisis pakai kata 'siswa'). Boleh pakai kata-kata santai kayak 'nih', 'yuk', "
    "'gapapa', tapi tetap sopan dan jelas, jangan kaku atau terlalu formal. "
    "Kalau jawabannya salah, sampaikan dengan santai dan gak bikin down, misalnya gaya 'jawaban kamu masih "
    "kurang tepat nih, tapi gapapa yuk kita bahas', baru lanjut jelasin letak kesalahan dan cara yang benar."
)


_PETA_SUPERSCRIPT = str.maketrans({
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "-": "⁻", "+": "⁺", "(": "⁽", ")": "⁾",
    "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ", "f": "ᶠ", "g": "ᵍ",
    "h": "ʰ", "i": "ⁱ", "j": "ʲ", "k": "ᵏ", "l": "ˡ", "m": "ᵐ", "n": "ⁿ",
    "o": "ᵒ", "p": "ᵖ", "r": "ʳ", "s": "ˢ", "t": "ᵗ", "u": "ᵘ", "v": "ᵛ",
    "w": "ʷ", "x": "ˣ", "y": "ʸ", "z": "ᶻ",
})


def _rapikan_pangkat(teks):
    """Jaring pengaman: kalau AI masih kebawa nulis pangkat pakai caret (x^2, a^n, x^(2n+1), dst)
    atau kata 'x pangkat 2', ubah jadi superscript unicode biar gak kaku. Huruf variabel (x, n, a, ...)
    juga didukung, bukan cuma angka, biar pangkat aljabar (aⁿ, x⁽ᵏ⁺¹⁾) ikut rapi."""
    # x^(2n+1), a^(n+m) -> apapun isi dalam kurung asal pendek, ubah jadi superscript unicode
    teks = re.sub(r"\^\(([^)]{1,12})\)", lambda m: m.group(1).translate(_PETA_SUPERSCRIPT), teks)
    # x^2, 10^12, 2^-3, a^n -> caret diikuti token pendek angka/huruf (bukan potongan kalimat biasa)
    teks = re.sub(r"\^(-?[0-9a-zA-Z]{1,6})\b", lambda m: m.group(1).translate(_PETA_SUPERSCRIPT), teks)
    # "x pangkat 2" / "5 pangkat -3" -> "x²" / "5⁻³" (dibatasi angka biar gak salah tangkap kalimat biasa
    # yang kebetulan mengandung kata "pangkat", misalnya "urutan pangkat dari yang terbesar")
    teks = re.sub(
        r"(?<=\w)\s+pangkat\s+\(?(-?\d+)\)?",
        lambda m: m.group(1).translate(_PETA_SUPERSCRIPT),
        teks,
        flags=re.I,
    )
    return teks


def _rapikan_perkalian(teks):
    """Tanda bintang di antara angka/variabel dianggap perkalian -> ganti simbol × biar gak kayak kode."""
    return re.sub(r"(?<=[0-9a-zA-Z)])\s*\*\s*(?=[0-9a-zA-Z(])", " × ", teks)


_POLA_MATRIKS = re.compile(
    r"\\\[\s*\\begin\{[pbvV]?matrix\}.*?\\end\{[pbvV]?matrix\}\s*\\\]", re.S
)
_PLACEHOLDER_MATRIKS = "\x00MATRIKS{}\x00"


def _lindungi_matriks(teks):
    """Simpan blok matriks LaTeX (\\[\\begin{bmatrix}...\\end{bmatrix}\\]) apa adanya sebelum
    dibersihkan, diganti sementara jadi placeholder, biar gak ikut kehapus/rusak sama pembersih
    LaTeX/markdown umum di bawah (yang memang sengaja buang \\(, \\), \\[, \\], &, dst untuk teks
    biasa). Matriks ini sengaja DIBIARKAN sebagai LaTeX asli supaya dirender MathJax jadi matriks
    berkurung siku yang rapi, bukan teks kurung siku manual."""
    simpanan = []

    def _simpan(m):
        simpanan.append(m.group(0))
        return _PLACEHOLDER_MATRIKS.format(len(simpanan) - 1)

    return _POLA_MATRIKS.sub(_simpan, teks), simpanan


def _kembalikan_matriks(teks, simpanan):
    for i, blok in enumerate(simpanan):
        teks = teks.replace(_PLACEHOLDER_MATRIKS.format(i), blok)
    return teks


_GANTI_SIMBOL_LATEX = {
    r"\Rightarrow": "→", r"\Leftrightarrow": "⇔", r"\rightarrow": "→",
    r"\leftrightarrow": "↔", r"\implies": "→", r"\Longrightarrow": "→",
    r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥",
    r"\neq": "≠", r"\ne": "≠", r"\approx": "≈", r"\sim": "≈",
    r"\pm": "±", r"\mp": "∓", r"\infty": "∞",
    r"\therefore": "jadi,", r"\because": "karena",
    r"\times": "×", r"\cdot": "×", r"\div": "÷",
}


def _bersihkan_format(teks):
    """Buang sisa markdown/LaTeX kalau AI masih kebawa nulisnya, biar tampil rapi sebagai teks biasa.
    (Blok matriks sudah dilindungi jadi placeholder sebelum fungsi ini dipanggil, lihat _panggil_groq)."""
    if not teks:
        return teks
    teks = re.sub(r"\\\((.*?)\\\)", r"\1", teks)
    teks = re.sub(r"\\\[(.*?)\\\]", r"\1", teks, flags=re.S)
    teks = re.sub(r"\\begin\{.*?\}|\\end\{.*?\}", "", teks)
    # Simbol/panah/relasi LaTeX yang kadang masih kebawa AI walau udah dilarang -> ganti unicode/kata biasa
    for cari, ganti in _GANTI_SIMBOL_LATEX.items():
        teks = teks.replace(cari, ganti)
    # \frac{a}{b} -> (a)/(b), \sqrt{a} -> √(a), \text{...} -> isinya polos
    teks = re.sub(r"\\d?frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", teks)
    teks = re.sub(r"\\sqrt\[(\d+)\]\{([^{}]*)\}", r"akar pangkat \1 dari (\2)", teks)
    teks = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", teks)
    teks = re.sub(r"\\text\{([^{}]*)\}", r"\1", teks)
    # \left( \right) dkk -> kurungnya doang, buang perintah \left/\right-nya
    teks = re.sub(r"\\left\s*([(\[|.])", r"\1", teks)
    teks = re.sub(r"\\right\s*([)\]|.])", r"\1", teks)
    # Perintah spasi LaTeX (\; \, \! \: \quad \qquad) -> cukup jadi satu spasi
    teks = re.sub(r"\\(?:quad|qquad|[;,!:])", " ", teks)
    teks = teks.replace("&", " ")
    teks = re.sub(r"\*\*(.*?)\*\*", r"\1", teks)
    teks = _rapikan_perkalian(teks)
    teks = re.sub(r"(?<!\d)\*(?!\d)", "", teks)
    teks = _rapikan_pangkat(teks)
    # Jaring pengaman terakhir: perintah LaTeX lain yang belum kena aturan di atas
    # (misal \displaystyle, \mathrm, \boldsymbol) -> buang backslash+namanya, sisakan isinya kalau ada
    teks = re.sub(r"\\[a-zA-Z]+", "", teks)
    teks = re.sub(r"[{}]", "", teks)
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
        raw = data["choices"][0]["message"]["content"].strip()

        raw_terlindung, simpanan_matriks = _lindungi_matriks(raw)
        clean = _bersihkan_format(raw_terlindung)
        final = _rapikan_final(clean)
        final = _kembalikan_matriks(final, simpanan_matriks)

        return final
    except Exception as e:
        print(f"[ai_service] Groq call failed: {repr(e)}", file=sys.stderr)
        traceback.print_exc()
        return fallback


def _daftar_pilihan(pilihan, konteks_pilihan=None):
    """Format daftar pilihan jawaban (A/B/C/D) jadi teks buat dikasih ke AI, biar AI ngerti isi
    tiap pilihan, bukan cuma huruf 'A'/'B' doang. Pilihan yang teksnya kosong (misal cuma gambar)
    otomatis dilewat -> makanya konteks_ai penting buat jelasin isi gambar pilihan itu.
    konteks_pilihan (opsional): list konteks AI khusus per pilihan (index sejajar sama `pilihan`),
    ditambahkan di belakang tiap pilihan yang punya isi, tanpa mengubah konteks_ai umum yang sudah ada."""
    if not pilihan:
        return ""
    huruf = "ABCD"
    baris = []
    for i, p in enumerate(pilihan):
        if i >= 4 or not p:
            continue
        teks = f"{huruf[i]}) {p}"
        k = konteks_pilihan[i] if konteks_pilihan and i < len(konteks_pilihan) else ""
        if k:
            teks += f" (konteks: {k})"
        baris.append(teks)
    return " Pilihan jawaban yang tersedia: " + " | ".join(baris) + "." if baris else ""


def explain_answer(question, selected, correct, fallback="", benar=None, konteks_ai="", pilihan=None, konteks_ai_pilihan=None):
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
    konteks_tambahan = (
        f" Catatan tambahan (ini konteks internal aja buat bantu kamu mikir, JANGAN disebut-sebut ke siswa "
        f"kalau ini 'konteks tersembunyi' atau semacamnya, langsung pakai aja isinya kayak bagian dari soal): {konteks_ai}."
        if konteks_ai else ""
    )
    pilihan_info = _daftar_pilihan(pilihan, konteks_ai_pilihan)
    prompt = (
        f"{GAYA_BICARA} {status} "
        f"Soal: {question}.{konteks_tambahan}{pilihan_info} Jawaban siswa: {selected}. Jawaban benar: {correct}. "
        "Maksimal 180 kata, fokus pada konsep dan langkah penyelesaian, bukan cuma menyebut benar/salah. "
        f"{ATURAN_FORMAT}"
    )
    messages = [{"role": "user", "content": prompt}]
    return _panggil_groq(messages, fallback_final)


def tanya_lanjutan(question, selected, correct, benar, riwayat, pesan_baru, konteks_ai="", pilihan=None, konteks_ai_pilihan=None):
    """Chat lanjutan kalau siswa masih mau tanya-tanya soal penjelasannya."""
    fallback = "Maaf, AI-nya lagi belum bisa jawab pertanyaan ini. Coba tanya lagi sebentar lagi, ya."
    if not os.environ.get("GROQ_API_KEY"):
        return fallback

    status_benar = "benar" if benar else "salah"
    konteks_tambahan = (
        f" Catatan tambahan (konteks internal aja, JANGAN disebut ke siswa, langsung pakai aja kayak bagian dari "
        f"soal): {konteks_ai}."
        if konteks_ai else ""
    )
    pilihan_info = _daftar_pilihan(pilihan, konteks_ai_pilihan)
    system_content = (
        f"{GAYA_BICARA} Kamu sedang chat singkat sama siswa buat bantu dia paham soal ini. Boleh nanya balik "
        "kalau perlu biar makin jelas, tapi tetap fokus ke soal ini aja, jangan melenceng ke topik lain. "
        f"Konteks soal: {question}.{konteks_tambahan}{pilihan_info} Jawaban siswa waktu itu: {selected}. Jawaban yang benar: {correct}. "
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

def _rapikan_final(teks):
    if not teks:
        return teks

    # 3^{4} → 3^4
    teks = re.sub(r"\^\{(\d+)\}", r"^\1", teks)

    # \times → ×
    teks = teks.replace("\\times", "×")
    teks = teks.replace("\\cdot", "×")
    teks = teks.replace("\\div", "÷")

    # baru convert ke superscript
    teks = _rapikan_pangkat(teks)

    # rapihin spasi operator
    teks = re.sub(r"\s*\+\s*", " + ", teks)
    teks = re.sub(r"\s*-\s*", " - ", teks)
    teks = re.sub(r"\s*×\s*", " × ", teks)
    teks = re.sub(r"\s*÷\s*", " ÷ ", teks)

    return teks.strip()

def evaluasi_hasil_ujian(mapel, tipe, reviews, riwayat=None):
    """Ringkasan + rekomendasi belajar di akhir ujian, berdasarkan soal-soal yang dijawab salah.
    reviews: list of {"question": {...}, "selected": str, "benar": bool}
    riwayat (opsional): list attempt SEBELUMNYA (dari scope yang sama, urutan bebas) -> dipakai biar AI
    bisa nyinggung progress/kemajuan siswa dibanding percobaan-percobaan sebelumnya. Tiap item minimal
    punya field "percent" dan "created_at".
    """
    total = len(reviews)
    salah = [r for r in reviews if not r.get("benar")]
    skor = total - len(salah)
    persen = round(skor * 100 / total) if total else 0

    riwayat = sorted(riwayat or [], key=lambda x: str(x.get("created_at") or ""))
    percobaan_ke = len(riwayat) + 1

    fallback_lines = [f"Kamu benar {skor} dari {total} soal ({persen}%) untuk {mapel} {tipe}."]
    if riwayat:
        terakhir = riwayat[-1].get("percent", 0)
        if persen > terakhir: fallback_lines.append(f"Ini percobaan ke-{percobaan_ke} kamu, dan nilainya naik dari {terakhir}% jadi {persen}% — mantap, ada kemajuan!")
        elif persen < terakhir: fallback_lines.append(f"Ini percobaan ke-{percobaan_ke} kamu. Nilainya turun dikit dari {terakhir}% jadi {persen}% dibanding percobaan sebelumnya, gapapa coba pelajari lagi bagian yang salah ya.")
        else: fallback_lines.append(f"Ini percobaan ke-{percobaan_ke} kamu, nilainya sama kayak percobaan sebelumnya ({persen}%).")
    if salah:
        fallback_lines.append("Bagian yang masih perlu dipelajari lagi:")
        for r in salah[:5]:
            fallback_lines.append(f"- {r['question'].get('pertanyaan', '')[:80]}")
        fallback_lines.append("Coba latihan lagi soal-soal sejenis itu ya, pelan-pelan juga gapapa.")
    else:
        fallback_lines.append("Semua jawaban kamu benar, mantap! Lanjut ke materi berikutnya, ya.")
    fallback = "\n".join(fallback_lines)

    if not os.environ.get("GROQ_API_KEY"):
        return fallback

    if salah:
        daftar_salah = "\n".join(
            f"- Soal: {r['question'].get('pertanyaan', '')[:200]}"
            + (f" | Konteks tambahan: {r['question'].get('konteks_ai', '')[:150]}" if r['question'].get('konteks_ai') else "")
            + _daftar_pilihan(r['question'].get('pilihan'), r['question'].get('konteks_ai_pilihan'))
            + f" | Jawaban siswa: {r.get('selected') or '-'} | "
            f"Jawaban benar: {r['question'].get('jawaban_benar', '')}"
            for r in salah[:10]
        )
        konteks_salah = f"Berikut soal-soal yang dijawab SALAH:\n{daftar_salah}"
    else:
        konteks_salah = "Semua soal dijawab BENAR, tidak ada yang salah."

    konteks_progress = ""
    if riwayat:
        daftar_persen = ", ".join(f"percobaan {i+1}: {r.get('percent',0)}%" for i, r in enumerate(riwayat))
        terakhir = riwayat[-1].get("percent", 0)
        tren = "naik" if persen > terakhir else ("turun" if persen < terakhir else "sama saja")
        konteks_progress = (
            f" Ini percobaan ke-{percobaan_ke} siswa ini untuk {tipe} {mapel} (dia sudah pernah mengerjakan ini "
            f"sebelumnya). Riwayat nilai percobaan-percobaan sebelumnya: {daftar_persen}. Dibanding percobaan "
            f"terakhirnya ({terakhir}%), nilai kali ini {tren}. Singgung progress ini sedikit di kalimat pembuka "
            "(misalnya makin membaik, sempat turun tapi gapapa, atau konsisten), tapi tetap singkat, jangan jadi "
            "poin terpisah."
        )

    prompt = (
        "Kamu tutor yang santai, suportif, dan ngerti gaya belajar Gen Alpha (suka konten singkat, visual, "
        "gamifikasi, dan langsung to the point, gampang bosan kalau kepanjangan atau ceramah). "
        f"Seorang siswa baru selesai latihan {tipe} mata pelajaran {mapel}, hasilnya {skor} dari {total} soal "
        f"benar ({persen}%). {konteks_salah}{konteks_progress} "
        "Tulis evaluasi akhir untuk siswa ini, LANGSUNG ngomong ke siswanya pakai 'kamu'. Isinya: "
        "1) satu-dua kalimat pembuka yang menyemangati sesuai hasilnya (jangan bikin down kalau nilainya rendah), "
        "2) sebutkan secara spesifik bagian/topik apa saja dari soal-soal yang salah tadi yang perlu dipelajari "
        "lagi (kalau semua benar, cukup bilang mantap dan kasih tantangan lanjutan), "
        "3) kasih 2-3 saran belajar yang konkret, singkat, dan relevan buat anak Gen Alpha, misalnya nonton "
        "video pendek/YouTube Shorts soal topik itu, latihan soal berulang dengan target waktu, bikin catatan "
        "singkat pakai gambar/diagram, main kuis interaktif, atau belajar bareng teman lewat voice call. "
        "Maksimal 150 kata, jangan pakai markdown, jangan pakai LaTeX, kalau perlu poin gunakan format "
        "'1) ...' ganti baris. "
        f"{ATURAN_FORMAT}"
    )
    messages = [{"role": "user", "content": prompt}]
    return _panggil_groq(messages, fallback)