-- Tabel untuk registrations
DROP TABLE IF EXISTS "registrations";
CREATE TABLE IF NOT EXISTS "registrations" (
  "id" TEXT,
  "nama_pengirim" TEXT,
  "user_id" TEXT,
  "jumlah_paket" TEXT,
  "total_harga" TEXT,
  "referensi_transfer" TEXT,
  "tanggal_transfer" TEXT,
  "total_pertemuan" TEXT,
  "catatan_admin" TEXT,
  "user_name" TEXT,
  "metode_pembayaran" TEXT,
  "created_at" TEXT,
  "processed_by" TEXT,
  "processed_at" TEXT,
  "status" TEXT
);

INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('5wVpPTsASSe3m0vLIR5W', 'Marko', 'TM24U9OZmO8Xam2uNJ4Y', '1', '30000', '6789', '2026-08-22', '2', '', 'juju', 'QRIS', '{"_seconds":1787404341,"_nanoseconds":208000000}', 'loYyLXkg7qta0czE0WnM', '{"_seconds":1787404386,"_nanoseconds":952560000}', 'approved');
INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('DMj7EitTwyWENvAFr2Qb', 'Farhat', 'xzhzgRXkpItB2jEn8i6N', '1', '30000', '3509', '2026-08-22', '2', '', 'Farhatchandra Permana', 'Transfer BCA', '{"_seconds":1787386781,"_nanoseconds":598000000}', 'loYyLXkg7qta0czE0WnM', '{"_seconds":1787388328,"_nanoseconds":455622000}', 'approved');
INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('EPS6euxPBTrJgmm5BAtK', 'Nofritawaty', 'gVA7Y1Bgh0mmaxWsMzGW', '1', '30000', '0372', '2026-08-31', '2', '', 'Keneysha Nailah Arkana', 'Transfer BCA', '{"_seconds":1788180207,"_nanoseconds":657000000}', 'loYyLXkg7qta0czE0WnM', '{"_seconds":1788180263,"_nanoseconds":25648000}', 'approved');
INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('MTYG9xwTsSaeLygPuB9q', 'Winda kurniawati', 'Eef2aEuVYxlN6SL9PWIb', '1', '30000', '56746', '2026-08-22', '2', '', 'Wildayanti Sekar Sasih', 'QRIS', '{"_seconds":1787391234,"_nanoseconds":179000000}', 'loYyLXkg7qta0czE0WnM', '{"_seconds":1787404389,"_nanoseconds":102846000}', 'approved');
INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('NDu2BMT4DWucWx72374W', 'Nofritawaty', 'gVA7Y1Bgh0mmaxWsMzGW', '1', '30000', '0372', '2026-09-07', '2', '', 'Keneysha Nailah Arkana', 'Transfer BCA', '{"_seconds":1788784939,"_nanoseconds":293000000}', NULL, NULL, 'pending');
INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('XQ1qZUC4SY9IzJSvaXTp', 'Nofritawaty', 'gVA7Y1Bgh0mmaxWsMzGW', '1', '30000', '0372', '2026-08-24', '2', '', 'Keneysha Nailah Arkana', 'Transfer BCA', '{"_seconds":1787573497,"_nanoseconds":913000000}', 'loYyLXkg7qta0czE0WnM', '{"_seconds":1787573628,"_nanoseconds":882553000}', 'approved');
INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('cgUitpnoEHLdOQfjL8OF', 'ANDIKA ASKHAR EFFENDI', 'oQm7py3kCZcxlWBsZh2B', '1', '30000', '5C33', '2026-09-04', '2', '', 'ANDIKA ASKHAR EFFENDI', 'Transfer BCA', '{"_seconds":1788529425,"_nanoseconds":758000000}', 'loYyLXkg7qta0czE0WnM', '{"_seconds":1788724851,"_nanoseconds":497380000}', 'approved');
INSERT INTO "registrations" ("id", "nama_pengirim", "user_id", "jumlah_paket", "total_harga", "referensi_transfer", "tanggal_transfer", "total_pertemuan", "catatan_admin", "user_name", "metode_pembayaran", "created_at", "processed_by", "processed_at", "status") VALUES ('i6RrjuXfzrI4cD5NMIXM', 'Winda kurniawati', 'Eef2aEuVYxlN6SL9PWIb', '1', '30000', '56746', '2026-08-22', '2', '', 'Wildayanti Sekar Sasih', 'QRIS', '{"_seconds":1787391178,"_nanoseconds":501000000}', 'loYyLXkg7qta0czE0WnM', '{"_seconds":1787391194,"_nanoseconds":241577000}', 'approved');
