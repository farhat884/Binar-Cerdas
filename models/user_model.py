"""Model users backed by Turso/libSQL."""
from werkzeug.security import generate_password_hash, check_password_hash
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso, as_int

COLLECTION = "users"


def _user(row):
    if not row:
        return None
    row = dict(row)
    row["id"] = row.get("id")
    row["sisa_pertemuan"] = as_int(row.get("sisa_pertemuan"), 0)
    row["total_pertemuan_dibeli"] = as_int(row.get("total_pertemuan_dibeli"), 0)
    return row


def create_user(name, email, password, phone, role="siswa", jenjang=None, kelas=None):
    email = email.lower().strip()
    if get_user_by_email(email):
        return None, "Email sudah terdaftar. Silakan login."
    user_id = new_id()
    data = {
        "id": user_id,
        "name": name,
        "email": email,
        "password": generate_password_hash(password),
        "phone": phone,
        "role": role,
        "jenjang": jenjang,
        "kelas": kelas,
        "sisa_pertemuan": 0,
        "total_pertemuan_dibeli": 0,
        "created_at": utcnow_iso(),
    }
    execute("""INSERT INTO users
        (id,name,email,password,phone,role,jenjang,kelas,sisa_pertemuan,total_pertemuan_dibeli,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        data["id"], data["name"], data["email"], data["password"], data["phone"],
        data["role"], data["jenjang"], data["kelas"], 0, 0, data["created_at"],
    ))
    return data, None


def get_user_by_email(email):
    return _user(fetch_one("SELECT * FROM users WHERE lower(email)=lower(?) LIMIT 1", (email.lower().strip(),)))


def get_user_by_id(user_id):
    return _user(fetch_one("SELECT * FROM users WHERE id=? LIMIT 1", (user_id,)))


def verify_password(user, password):
    return check_password_hash(user["password"], password)


def get_all_siswa():
    return [_user(x) for x in fetch_all("SELECT * FROM users WHERE role='siswa' ORDER BY name ASC")]


def tambah_pertemuan(user_id, jumlah):
    try:
        jumlah = int(jumlah)
    except (ValueError, TypeError):
        raise ValueError("Jumlah pertemuan harus berupa angka.")
    if jumlah <= 0:
        raise ValueError("Jumlah pertemuan harus lebih dari 0.")
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Data siswa tidak ditemukan.")
    sisa = int(user.get("sisa_pertemuan", 0)) + jumlah
    total = int(user.get("total_pertemuan_dibeli", 0)) + jumlah
    execute("UPDATE users SET sisa_pertemuan=?, total_pertemuan_dibeli=? WHERE id=?", (sisa, total, user_id))
    return sisa


def kurangi_pertemuan(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return False, "Siswa tidak ditemukan."
    sisa = int(user.get("sisa_pertemuan", 0))
    if sisa <= 0:
        return False, "Sisa pertemuan siswa ini sudah 0."
    execute("UPDATE users SET sisa_pertemuan=? WHERE id=?", (sisa - 1, user_id))
    return True, None


def gunakan_pertemuan_untuk_materi(user_id):
    ok, error = kurangi_pertemuan(user_id)
    if not ok:
        raise ValueError(error)
    return int(get_user_by_id(user_id).get("sisa_pertemuan", 0))


def delete_siswa(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return False, "Siswa tidak ditemukan."
    if user.get("role") != "siswa":
        return False, "Akun ini bukan akun siswa, tidak bisa dihapus lewat sini."
    execute("DELETE FROM users WHERE id=? AND role='siswa'", (user_id,))
    return True, None
