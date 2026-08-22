# Struktur Materi Binar Cerdas

Fitur baru membuat materi bertingkat:

**Mata Pelajaran → Bab → Tahapan/Subbab → Rangkuman + PDF Full + Latihan → Ulangan Harian Bab**

## Cara admin mengisi
1. Buka **Admin → Materi**.
2. Tambahkan setiap tahapan/subbab sebagai satu data materi.
3. Isi **Nama Bab**, **Urutan Bab**, dan **Urutan Tahapan**.
4. Isi **Rangkuman** untuk teks singkat yang langsung terlihat siswa.
5. Upload **PDF Full** seperti mekanisme materi sebelumnya.
6. Buka **Admin → Bank Soal**.
7. Untuk latihan per tahapan, pilih tipe **Latihan Tahapan** dan hubungkan soal ke materi/tahapan.
8. Untuk evaluasi akhir bab, pilih tipe **Ulangan Harian Bab** dan isi **Bab** yang sama persis dengan nama Bab pada materi.

## Tampilan siswa
- `/materi` menampilkan mata pelajaran.
- Klik mapel → daftar Bab.
- Klik Bab → daftar tahapan/subbab.
- Klik tahapan → rangkuman + PDF full + latihan soal.
- Bagian paling bawah Bab → Ulangan Harian Bab.

## Tutorial
Saat pertama kali siswa membuka halaman Materi pada browser/perangkat tersebut, muncul tutorial singkat 4 langkah. Tutorial dapat dilewati dan dapat dibuka kembali melalui tombol **Cara Menggunakan**.

## Data lama
Materi lama yang belum memiliki field `bab`, `urutan_bab`, atau `urutan_subbab` otomatis tetap tampil dan dikelompokkan sementara ke **Bab 1**. Admin disarankan mengedit data lama dari **Admin → Materi** agar struktur bab dan urutannya sesuai.

Soal lama tetap aman. Soal latihan lama yang terhubung `material_id` tetap bekerja seperti sebelumnya.
