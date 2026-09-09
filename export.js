const { initializeApp, cert } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
const fs = require("fs");

const serviceAccount = require("./serviceAccountKey.json");

initializeApp({
  credential: cert(serviceAccount)
});

const db = getFirestore();

// Semua koleksi sesuai hasil check_collections
const collections = [
  "live_participants",
  "live_sessions",
  "material_access",
  "material_progress",
  "materials",
  "questions",
  "quiz_attempts",
  "quiz_drafts",
  "registrations",
  "schedules",
  "users"
];

async function exportCollection(collectionName) {
  try {
    const snapshot = await db.collection(collectionName).get();
    const data = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));

    fs.writeFileSync(`${collectionName}.json`, JSON.stringify(data, null, 2));
    console.log(`Berhasil mengekspor ${data.length} data ke ${collectionName}.json`);
  } catch (error) {
    console.error(`Gagal mengekspor ${collectionName}:`, error);
  }
}

async function exportAll() {
  console.log("Sedang mengambil seluruh data dari Firestore...");
  for (const col of collections) {
    await exportCollection(col);
  }
  console.log("Proses export selesai!");
}

exportAll();