from urllib.parse import unquote_plus


def clean_url_param(raw):
    """Bersihin parameter yang datang dari URL (mis. <mapel>, <bab>) yang
    mengandung spasi.

    Di sebagian environment hosting, request path kadang sampai ke Flask
    dalam kondisi belum ke-decode sepenuhnya (spasi masih berupa literal
    "%20"/"+"), khususnya untuk mapel yang namanya lebih dari satu kata
    seperti "Matematika Tingkat Lanjut" atau "Matematika Wajib". Ini bikin
    perbandingan string di route (mis. cari mapel di database) gagal terus
    walau datanya sebenernya ada, dan muncul pesan "tidak ditemukan".

    Fungsi ini aman dipanggil kapan pun: kalau nilainya udah ke-decode
    dengan benar sama Flask/Werkzeug (kasus normal), fungsi ini gak
    ngubah apa-apa selain strip spasi. Kalau belum ke-decode, fungsi ini
    yang beresin.
    """
    if not raw:
        return raw
    decoded = raw
    for _ in range(2):
        if "%" not in decoded and "+" not in decoded:
            break
        try:
            new_decoded = unquote_plus(decoded)
        except Exception:
            break
        if new_decoded == decoded:
            break
        decoded = new_decoded
    return decoded.strip()


def format_rupiah(angka):
    """
    Mengubah angka menjadi format Rupiah.
    Contoh:
    30000 -> Rp30.000
    """

    try:
        angka = int(angka or 0)
    except (ValueError, TypeError):
        angka = 0

    return f"Rp{angka:,.0f}".replace(",", ".")