const fs = require("fs");
const admin = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
const { cert } = require("firebase-admin/app");

const serviceAccount = require("./serviceAccountKey.json");

admin.initializeApp({
  credential: cert(serviceAccount)
});

const db = getFirestore();

// 🔥 GANTI sesuai collection kamu
const collections = ["users", "soal", "materi", "progress"];

async function exportAll() {
  for (const colName of collections) {
    console.log(`Exporting ${colName}...`);

    const snapshot = await db.collection(colName).get();

    const data = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));

    fs.writeFileSync(
      `${colName}.json`,
      JSON.stringify(data, null, 2)
    );

    console.log(`✅ ${colName}.json berhasil dibuat`);
  }

  console.log("🎉 Semua data berhasil di-export!");
}

exportAll();