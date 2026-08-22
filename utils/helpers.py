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