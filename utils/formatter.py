import re

def to_superscript(text):
    sup_map = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

    def repl(match):
        return match.group(1).translate(sup_map)

    return re.sub(r'\^(\d+)', repl, text)


def clean_latex(text):
    # 3^{4} → 3^4
    text = re.sub(r'\^\{(\d+)\}', r'^\1', text)

    # \times → ×
    text = text.replace('\\times', '×')

    # \div → ÷
    text = text.replace('\\div', '÷')

    # \cdot → ×
    text = text.replace('\\cdot', '×')

    # hapus kurung latex
    text = text.replace('{', '').replace('}', '')

    return text


def normalize_math(text):
    # rapihin spasi operator
    text = re.sub(r'\s*\+\s*', ' + ', text)
    text = re.sub(r'\s*-\s*', ' - ', text)
    text = re.sub(r'\s*×\s*', ' × ', text)
    text = re.sub(r'\s*÷\s*', ' ÷ ', text)

    return text


def clean_steps(text):
    # rapihin numbering biar konsisten
    text = re.sub(r'(\d+)\)\s*', r'\1) ', text)
    return text


def format_ai_output(text):
    text = clean_latex(text)
    text = to_superscript(text)
    text = normalize_math(text)
    text = clean_steps(text)

    return text.strip()


def teks_pilihan(pilihan, huruf):
    """Ubah huruf jawaban (A/B/C/D) jadi teks lengkap 'D. isi pilihannya'.

    Dipakai di halaman review jawaban supaya siswa gak cuma lihat hurufnya doang
    (sebelumnya "Jawaban benar: D" tanpa tau isi si D apa -> bikin bingung).
    Kalau pilihan-nya kosong/gak valid, tetap fallback ke huruf aslinya biar
    gak error di halaman lama/soal yang datanya belum lengkap.
    """
    if not huruf:
        return "-"
    urutan = "ABCD"
    if huruf not in urutan or not pilihan:
        return huruf
    idx = urutan.index(huruf)
    if idx >= len(pilihan) or not pilihan[idx]:
        return huruf
    return f"{huruf}. {pilihan[idx]}"


def parse_numbered_questions(text):
    """
    Pisahin teks yang ditempel (misalnya hasil copy-paste dari Word) yang
    ditulis dengan format bernomor "1. ... 2. ... 3. ..." jadi list
    pertanyaan terpisah, satu soal per elemen.

    Contoh input:
        1. Ibukota Indonesia adalah?
        2. Berapa hasil dari 5 + 3?

    Output: ["Ibukota Indonesia adalah?", "Berapa hasil dari 5 + 3?"]
    """
    if not text or not text.strip():
        return []

    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Cari penanda nomor di awal baris, misal "1." atau "1)"
    matches = list(re.finditer(r'^[ \t]*\d{1,3}[.)]\s+', text, re.MULTILINE))

    if not matches:
        # Gak ketemu penomoran -> anggap tiap baris non-kosong itu 1 soal
        return [line.strip() for line in text.split('\n') if line.strip()]

    questions = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            questions.append(content)
    return questions


# Penanda baris pilihan jawaban, misal "A. isi pilihan" atau "b) isi pilihan"
_OPSI_MARKER_RE = re.compile(r'^[ \t]*([A-Da-d])[.)]\s+', re.MULTILINE)

# Penanda baris jawaban benar, misal "JAWABAN: B", "Jawaban Benar: B",
# "KUNCI: B", "Kunci Jawaban B"
_JAWABAN_MARKER_RE = re.compile(
    r'^[ \t]*(?:JAWABAN(?:\s+BENAR)?|KUNCI(?:\s+JAWABAN)?)\s*[:\-]?\s*([A-Da-d])\b',
    re.MULTILINE | re.IGNORECASE,
)


def parse_full_mcq(text):
    """
    Parser buat impor BANYAK SOAL PILIHAN GANDA LENGKAP sekaligus
    (pertanyaan + pilihan A-D + jawaban benar), dari teks yang
    ditempel/copy-paste (misal dari Word).

    Format yang diharapkan per soal:
        1. Pertanyaan...?
        A. isi pilihan a
        B. isi pilihan b
        C. isi pilihan c
        D. isi pilihan d
        JAWABAN: B

    Sengaja dibikin KETAT (bukan tebak-tebakan urutan baris) supaya gak ada
    soal/pilihan/jawaban yang "ketuker" antar nomor:
    - Tiap pilihan diambil berdasarkan HURUF-nya (A/B/C/D), bukan urutan
      kemunculan baris, jadi tetap kepasang benar walau urutannya keliru.
    - Soal yang pilihannya gak lengkap 4 (A-D) atau jawaban benarnya gak
      ketemu/gak valid TIDAK ikut masuk daftar berhasil -- dilaporkan
      terpisah di `gagal` biar admin bisa perbaiki, bukan disimpan
      asal-asalan/kosong.

    Return: (berhasil, gagal)
      berhasil: list of dict {nomor, pertanyaan, pilihan: [a,b,c,d], jawaban_benar}
      gagal: list of dict {nomor, alasan}
    """
    berhasil = []
    gagal = []
    if not text or not text.strip():
        return berhasil, gagal

    text = text.replace('\r\n', '\n').replace('\r', '\n')

    soal_matches = list(re.finditer(r'^[ \t]*(\d{1,3})[.)]\s+', text, re.MULTILINE))
    if not soal_matches:
        gagal.append({"nomor": "-", "alasan": "Gak ketemu penomoran soal (contoh '1. ', '2. ') di teks yang ditempel."})
        return berhasil, gagal

    for i, m in enumerate(soal_matches):
        nomor_asli = m.group(1)
        block_start = m.end()
        block_end = soal_matches[i + 1].start() if i + 1 < len(soal_matches) else len(text)
        block = text[block_start:block_end].strip('\n')

        opsi_matches = list(_OPSI_MARKER_RE.finditer(block))
        jawaban_match = _JAWABAN_MARKER_RE.search(block)

        # Pertanyaan = semua teks sebelum pilihan pertama (atau baris jawaban
        # kalau gak ada pilihan sama sekali) muncul.
        if opsi_matches:
            pertanyaan_end = opsi_matches[0].start()
        elif jawaban_match:
            pertanyaan_end = jawaban_match.start()
        else:
            pertanyaan_end = len(block)
        pertanyaan = block[:pertanyaan_end].strip()

        if not pertanyaan:
            gagal.append({"nomor": nomor_asli, "alasan": "Teks pertanyaan kosong."})
            continue

        # Ambil isi tiap pilihan berdasarkan HURUFNYA (bukan urutan baris),
        # biar soal yang pilihannya ketulis gak berurutan tetap kepasang benar.
        isi_per_huruf = {}
        dobel = None
        for j, om in enumerate(opsi_matches):
            huruf = om.group(1).upper()
            konten_start = om.end()
            konten_end = opsi_matches[j + 1].start() if j + 1 < len(opsi_matches) else (jawaban_match.start() if jawaban_match else len(block))
            konten = block[konten_start:konten_end].strip()
            if huruf in isi_per_huruf:
                dobel = huruf
                break
            isi_per_huruf[huruf] = konten

        if dobel:
            gagal.append({"nomor": nomor_asli, "alasan": f"Pilihan {dobel} ditulis dobel."})
            continue

        huruf_kurang = [h for h in "ABCD" if h not in isi_per_huruf or not isi_per_huruf[h]]
        if huruf_kurang:
            gagal.append({
                "nomor": nomor_asli,
                "alasan": f"Pilihan {', '.join(huruf_kurang)} belum diisi/gak ketemu.",
            })
            continue

        if not jawaban_match:
            gagal.append({
                "nomor": nomor_asli,
                "alasan": "Baris jawaban benar gak ketemu. Tulis misal 'JAWABAN: B' setelah pilihan D.",
            })
            continue

        berhasil.append({
            "nomor": nomor_asli,
            "pertanyaan": pertanyaan,
            "pilihan": [isi_per_huruf["A"], isi_per_huruf["B"], isi_per_huruf["C"], isi_per_huruf["D"]],
            "jawaban_benar": jawaban_match.group(1).upper(),
        })

    return berhasil, gagal