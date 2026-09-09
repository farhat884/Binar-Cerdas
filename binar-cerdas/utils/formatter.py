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