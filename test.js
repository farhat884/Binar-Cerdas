const db = require('./db.js');

async function cekData() {
  try {
    const hasil = await db.execute('SELECT name, email, role FROM users');
    console.log("Koneksi Berhasil! Ini data dari Turso:");
    console.table(hasil.rows);
  } catch (error) {
    console.error("Koneksi gagal:", error);
  }
}

cekData();