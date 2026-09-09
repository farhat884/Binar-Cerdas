const { initializeApp, cert } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");

const serviceAccount = require("./serviceAccountKey.json");

initializeApp({
  credential: cert(serviceAccount)
});

const db = getFirestore();

async function checkCollections() {
  try {
    const collections = await db.listCollections();
    console.log("--- DAFTAR KOLEKSI DI FIRESTORE ---");
    if (collections.length === 0) {
      console.log("Tidak ada koleksi ditemukan.");
    } else {
      collections.forEach(col => console.log("- " + col.id));
    }
  } catch (error) {
    console.error("Gagal mengambil daftar koleksi:", error);
  }
}

checkCollections();