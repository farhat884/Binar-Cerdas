const fs = require("fs");

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

function convertJsonToSql(collectionName) {
  const jsonFile = `${collectionName}.json`;
  const sqlFile = `${collectionName}.sql`;

  try {
    if (!fs.existsSync(jsonFile)) {
      console.log(`File ${jsonFile} tidak ditemukan, dilewati.`);
      return;
    }

    const data = JSON.parse(fs.readFileSync(jsonFile, "utf8"));
    if (!Array.isArray(data) || data.length === 0) {
      console.log(`File ${jsonFile} kosong, dilewati.`);
      return;
    }

    const columns = Array.from(new Set(data.flatMap(obj => Object.keys(obj))));

    let sqlContent = `-- Tabel untuk ${collectionName}\n`;
    // Hapus tabel lama jika sudah ada agar struktur kolom selalu segar
    sqlContent += `DROP TABLE IF EXISTS "${collectionName}";\n`;
    sqlContent += `CREATE TABLE IF NOT EXISTS "${collectionName}" (\n`;
    sqlContent += columns.map(col => `  "${col}" TEXT`).join(",\n");
    sqlContent += `\n);\n\n`;

    data.forEach(item => {
      const values = columns.map(col => {
        const val = item[col];
        if (val === undefined || val === null) return "NULL";
        if (typeof val === "object") return `'${JSON.stringify(val).replace(/'/g, "''")}'`;
        return `'${String(val).replace(/'/g, "''")}'`;
      });
      sqlContent += `INSERT INTO "${collectionName}" (${columns.map(c => `"${c}"`).join(", ")}) VALUES (${values.join(", ")});\n`;
    });

    fs.writeFileSync(sqlFile, sqlContent);
    console.log(`Berhasil mengubah ${jsonFile} menjadi ${sqlFile}!`);
  } catch (error) {
    console.error(`Gagal mengonversi ${jsonFile}:`, error);
  }
}

collections.forEach(col => convertJsonToSql(col));