-- Tabel untuk material_progress
DROP TABLE IF EXISTS "material_progress";
CREATE TABLE IF NOT EXISTS "material_progress" (
  "id" TEXT,
  "updated_at" TEXT,
  "user_id" TEXT,
  "material_id" TEXT,
  "completed" TEXT
);

INSERT INTO "material_progress" ("id", "updated_at", "user_id", "material_id", "completed") VALUES ('S2IGhxBCfeQ40qgtQPro_zOXK7QyFoYcLSSPr4VQO', '{"_seconds":1788374006,"_nanoseconds":37539000}', 'S2IGhxBCfeQ40qgtQPro', 'zOXK7QyFoYcLSSPr4VQO', 'true');
