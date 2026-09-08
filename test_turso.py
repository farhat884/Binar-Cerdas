from database import fetch_all

rows = fetch_all("SELECT id, name, email, role FROM users LIMIT 10")
print("================================")
print("KONEKSI TURSO BERHASIL!")
print("Jumlah user:", len(rows))
print("================================")
for row in rows:
    print((row.get("id"), row.get("name"), row.get("email"), row.get("role")))
