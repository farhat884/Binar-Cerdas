# ✦ Binar Cerdas

Aplikasi bimbingan belajar online (SD, SMP, SMA) dengan Flask + Firebase.
Ada 2 role: **siswa** (lihat jadwal, beli paket, lihat sisa pertemuan) dan
**admin** (verifikasi bukti bayar, approve pendaftaran, kelola sisa pertemuan
tiap siswa, kelola jadwal).

## Struktur Project & Pemisahan Role

```
binar-cerdas/
├── app.py                     # entry point, register semua blueprint
├── firebase_config.py         # init Firestore + Storage
├── auth/decorators.py         # @login_required @admin_required @student_required
├── models/
│   ├── user_model.py          # role, sisa_pertemuan (hanya admin yang boleh ubah)
│   ├── registration_model.py  # pendaftaran/pembelian paket + status approval
│   └── program_model.py       # jadwal kelas
├── routes/
│   ├── auth_routes.py         # /login /register /logout (semua orang, akun baru = siswa)
│   ├── student_routes.py      # /siswa/**  -> HANYA role "siswa"
│   └── admin_routes.py        # /admin/**  -> HANYA role "admin"
├── templates/
│   ├── student/                # dashboard, jadwal, daftar_les, riwayat
│   └── admin/                  # dashboard, pendaftaran, siswa, jadwal
├── static/css/style.css       # design system "Binar" (navy + emas, star-meter)
└── scripts/
    ├── create_admin.py        # buat akun admin pertama (tidak lewat website)
    └── seed_firestore.py      # isi jadwal default
```

**Bagaimana role dipisah?** Saat login, `role` user ("admin" atau "siswa")
disimpan di `session['role']`. Setiap route di `student_routes.py` dibungkus
`@student_required`, setiap route di `admin_routes.py` dibungkus
`@admin_required` (lihat `auth/decorators.py`). Siswa login akan diarahkan ke
`/siswa/dashboard`, admin ke `/admin/dashboard` — keduanya punya tampilan dan
menu navigasi yang sama sekali berbeda.

**Alur sisa pertemuan:**
1. Siswa isi form di `/siswa/daftar-les`, pilih 1–4 paket sekaligus (1 paket =
   2x pertemuan/minggu, jadi 4 paket = 8x pertemuan ≈ 1 bulan), unggah bukti
   transfer → status `pending`, **sisa pertemuan BELUM bertambah**.
2. Admin buka `/admin/pendaftaran`, lihat bukti bayar, klik **Setujui** →
   baru saat itu `sisa_pertemuan` siswa bertambah otomatis.
3. Setiap kali 1 sesi les selesai, admin buka `/admin/siswa` lalu klik
   **−1 Pertemuan** untuk siswa yang bersangkutan.
4. Siswa hanya bisa **melihat** sisa pertemuannya di dashboard (read-only,
   tidak ada tombol ubah di sisi siswa sama sekali).

## 1. Setup Firebase

1. Buka [Firebase Console](https://console.firebase.google.com) → buat project baru, misal `binar-cerdas`.
2. Aktifkan **Firestore Database** (mode production).
3. Aktifkan **Storage** (untuk menyimpan file bukti pembayaran).
4. Buka **Project Settings → Service Accounts → Generate new private key**,
   simpan file JSON hasil download sebagai `serviceAccountKey.json` di root
   project ini (file ini sudah ada di `.gitignore`, jangan pernah di-commit).
5. Salin nama Storage bucket-mu (biasanya `nama-project.appspot.com`).

### Rules Firestore & Storage (disarankan)
Karena semua akses data lewat backend Flask (Firebase Admin SDK, yang selalu
punya akses penuh), set rules client-side ke "tolak semua" supaya data hanya
bisa diakses lewat server-mu:

```
// Firestore rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} { allow read, write: if false; }
  }
}
```

```
// Storage rules
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} { allow read, write: if false; }
  }
}
```

## 2. Jalankan di Lokal

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # lalu isi SECRET_KEY & FIREBASE_STORAGE_BUCKET
# pastikan serviceAccountKey.json sudah ada di root folder

python scripts/seed_firestore.py   # isi jadwal default (sekali saja)
python scripts/create_admin.py     # buat akun admin pertama

python app.py
# buka http://localhost:5000
```

## 3. Push ke GitHub

```bash
git init
git add .
git commit -m "Binar Cerdas - initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/binar-cerdas.git
git push -u origin main
```

`.env` dan `serviceAccountKey.json` **tidak akan ikut ter-push** karena sudah
ada di `.gitignore` — ini memang harus begitu, isinya rahasia.

## 4. Deploy ke Vercel

1. Import repo GitHub ini di [vercel.com/new](https://vercel.com/new).
2. Di **Environment Variables**, isi:
   - `SECRET_KEY` → string acak
   - `FIREBASE_STORAGE_BUCKET` → nama bucket Firebase-mu
   - `FIREBASE_CREDENTIALS_JSON` → **isi seluruh isi file** `serviceAccountKey.json`
     (paste sebagai satu blok JSON, karena Vercel tidak menyimpan file biasa).
3. Deploy. `vercel.json` sudah diatur supaya Vercel menjalankan `app.py`
   lewat runtime Python.
4. Setelah deploy pertama berhasil, jalankan `scripts/create_admin.py` dan
   `scripts/seed_firestore.py` dari lokal (mereka menulis langsung ke
   Firestore yang sama, tidak perlu dijalankan di server Vercel).

## Catatan Paket & Harga

- 1 paket = Rp30.000 → 2x pertemuan/minggu
- Maks 4 paket sekaligus saat daftar = Rp120.000 → 8x pertemuan (≈ 1 bulan)
- Ubah harga/batas di `models/registration_model.py`
  (`HARGA_PER_PAKET`, `MAKS_PAKET_SEKALIGUS`).
