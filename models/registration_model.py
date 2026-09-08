"""Model registrations / pembelian paket, backed by Turso."""
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso

COLLECTION = "registrations"
HARGA_PER_PAKET = 30000
PERTEMUAN_PER_PAKET = 2
MAKS_PAKET_SEKALIGUS = 4


def buat_pendaftaran(user_id, user_name, jumlah_paket, metode_pembayaran, nama_pengirim, tanggal_transfer, referensi_transfer):
    jumlah_paket = max(1, min(int(jumlah_paket), MAKS_PAKET_SEKALIGUS))
    total_pertemuan = jumlah_paket * PERTEMUAN_PER_PAKET
    total_harga = jumlah_paket * HARGA_PER_PAKET
    data = {
        "id": new_id(), "user_id": user_id, "user_name": user_name,
        "jumlah_paket": jumlah_paket, "total_pertemuan": total_pertemuan,
        "total_harga": total_harga, "metode_pembayaran": metode_pembayaran,
        "nama_pengirim": nama_pengirim, "tanggal_transfer": tanggal_transfer,
        "referensi_transfer": referensi_transfer, "status": "pending",
        "catatan_admin": "", "created_at": utcnow_iso(),
    }
    execute("""INSERT INTO registrations
      (id,user_id,user_name,jumlah_paket,total_pertemuan,total_harga,metode_pembayaran,nama_pengirim,tanggal_transfer,referensi_transfer,status,catatan_admin,created_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", tuple(data[k] for k in ["id","user_id","user_name","jumlah_paket","total_pertemuan","total_harga","metode_pembayaran","nama_pengirim","tanggal_transfer","referensi_transfer","status","catatan_admin","created_at"]))
    return data


def get_pendaftaran(reg_id):
    return fetch_one("SELECT * FROM registrations WHERE id=? LIMIT 1", (reg_id,))


def _sort_desc(rows):
    return sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)


def get_pendaftaran_by_status(status="pending"):
    return _sort_desc(fetch_all("SELECT * FROM registrations WHERE status=?", (status,)))


def get_pendaftaran_by_user(user_id):
    return _sort_desc(fetch_all("SELECT * FROM registrations WHERE user_id=?", (user_id,)))


def proses_pendaftaran(reg_id, status, admin_id, catatan=""):
    execute("UPDATE registrations SET status=?, processed_at=?, processed_by=?, catatan_admin=? WHERE id=?", (status, utcnow_iso(), admin_id, catatan, reg_id))
