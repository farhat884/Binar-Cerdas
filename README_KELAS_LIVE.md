# Binar Cerdas — Kelas Live Terintegrasi

Versi ini menambahkan **Kelas Live** yang menggabungkan materi, papan tulis bersama, dan kuis interaktif.

## Fitur baru
- Materi rangkuman/PDF tampil full-screen di layar siswa.
- Admin/pengajar punya papan tulis canvas untuk coretan.
- Admin bisa mengizinkan siswa ikut mencoret; jika tidak diizinkan, canvas siswa read-only.
- Soal kuis dapat dipilih dari Bank Soal berdasarkan **mapel + bab/materi**.
- Admin dapat memilih siswa yang mengerjakan.
- Urutan soal bisa diacak, termasuk opsi acak berbeda untuk tiap siswa.
- Kuis dapat dinyalakan/dimatikan kapan saja saat pengajaran berlangsung.
- Setelah pembahasan soal terakhir, kelas otomatis kembali ke mode mengajar.
- Sinkronisasi menggunakan polling AJAX sehingga tidak membutuhkan WebSocket.

## Menjalankan
1. Salin `.env.example` menjadi `.env`, lalu isi kredensial Turso/Supabase.
2. Install dependency dari `requirements.txt`.
3. Jalankan `python app.py`.

> File `.env` dan `serviceAccountKey.json` dari proyek asli sengaja tidak disertakan dalam ZIP hasil modifikasi agar kredensial tidak ikut tersebar.

## Alur admin
Buat sesi → pilih materi → pilih soal dari bab tersebut → tentukan siswa → mulai kelas → jelaskan di papan/materi → klik **Nyalakan kuis** saat diperlukan → tutup soal untuk pembahasan → lanjut ke soal berikutnya.
