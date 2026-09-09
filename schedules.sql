-- Tabel untuk schedules
DROP TABLE IF EXISTS "schedules";
CREATE TABLE IF NOT EXISTS "schedules" (
  "id" TEXT,
  "hari" TEXT,
  "jam" TEXT,
  "mapel" TEXT,
  "kelas" TEXT,
  "created_at" TEXT,
  "jenjang" TEXT
);

INSERT INTO "schedules" ("id", "hari", "jam", "mapel", "kelas", "created_at", "jenjang") VALUES ('8JOYhrjCeeC5AashpHpZ', 'Senin, 28 Oktober 2027', '19.45-21.00', 'Matematika', '12', '{"_seconds":1787389815,"_nanoseconds":107282000}', 'SMA');
