-- Tabel untuk users
DROP TABLE IF EXISTS "users";
CREATE TABLE IF NOT EXISTS "users" (
  "id" TEXT,
  "email" TEXT,
  "sisa_pertemuan" TEXT,
  "password" TEXT,
  "role" TEXT,
  "kelas" TEXT,
  "phone" TEXT,
  "jenjang" TEXT,
  "created_at" TEXT,
  "name" TEXT,
  "total_pertemuan_dibeli" TEXT,
  "akses_materi_gratis" TEXT
);

INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('HVFTv67SyRgmpipE4GKW', 'oyadi65@gmail.com', '0', 'scrypt:32768:8:1$5MRrVS0uwNT0yrCz$4b43b0af7a9b33d7e183960aabb6dde385854ef2d5b0587f44a28f02778d9489bc6d56df180b0de5ba764b0deb832f8c4b612eced761e03b30a6031e2ebe3fc7', 'siswa', '11', '081231591508', 'SMA', '{"_seconds":1787482638,"_nanoseconds":341289000}', 'Rizky Mulya Permana', '0', NULL);
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('Hbaa0Gxsmx1J1ho3HD0f', 'sekar@gmail.com', '100', 'scrypt:32768:8:1$MUf3WQPcZv1pouOm$8a2c4b1af690bb96371e5d27d23103cc60774cce93b0b3d376b29647fd166c0584f7e5512e7f6a441a36e60be38a97a714b17f2662098b6e1ef72b05e3df5a8d', 'siswa', '8', '0812-8418-3419', 'SMP', '{"_seconds":1788418275,"_nanoseconds":308323000}', 'Wildayanti Sekar Sasih', '100', NULL);
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('S2IGhxBCfeQ40qgtQPro', 'marko@gmail.com', '93', 'scrypt:32768:8:1$wiQI031MmbCWjpbd$498568a0a672d58fecc705311d74e25bbe2275be5b095d5af63a82173df13a54da44c2fc03faac446e4b74f70814945b0c7725c1fa30d8f356e658ab8508e3a8', 'siswa', '11', '0895346161387', 'SMA', '{"_seconds":1788089804,"_nanoseconds":160493000}', 'Juju', '100', NULL);
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('XJ3Ao6tWDnj41DGhXD6R', 'charisa.marthadps18@gmail.com', '0', 'scrypt:32768:8:1$eQ2WbLY58Wd2avyU$b038dfa7ee8f777ce956a4f028ec798d14f631c1a89f0f0e30a0747edc0ce418ede2ea53150b9685492469c718fd36ed5c62787bbcf06e67115592ce068fad5a', 'siswa', '11', '081212120218', 'SMA', '{"_seconds":1788101419,"_nanoseconds":738476000}', 'Charisa', '0', NULL);
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('gVA7Y1Bgh0mmaxWsMzGW', 'nailahkeney3715@gmail.com', '1', 'scrypt:32768:8:1$GP6KVPNcaF04VZpz$e57c84879df16216f60962a0ef39f47415adf0f0cae3c92d3c74a4741fe40ac9008c7639cb0b5d35755ec8d8186b73e59fd3e7297cdbf53d9df8475e1a0d49f2', 'siswa', '11', '0853-1104-9890', 'SMA', '{"_seconds":1787572061,"_nanoseconds":939023000}', 'Keneysha Nailah Arkana', '5', NULL);
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('k8cyaD5lk0aKS44yhQb5', 'destyananda@gmail.con', '0', 'scrypt:32768:8:1$EAm9TQXgGBc8asgG$977662d1280d4f57b2fcb6f9415521d065cfa20c72fe9328d95a26e073db8ecd04f9355c75b7b531a7d15333a717c3fb5e006a995a86fa8855ad5fd36cfe16a2', 'siswa', '11', '08111487208', 'SMA', '{"_seconds":1787576397,"_nanoseconds":694183000}', 'Quina Destyananda', '0', NULL);
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('loYyLXkg7qta0czE0WnM', 'farhatchandrapermana@gmail.com', '0', 'scrypt:32768:8:1$SbjMErb0uFyIeowT$4aa9a8a55ffdf29777e676dc810873879ab332860f6161ba5486693d2cc1f720a62b4c4fa47103faedb9d337b1f4db008f12372d922bcbf0df00e7471dc03b50', 'admin', NULL, '0895346161387', NULL, '{"_seconds":1787383014,"_nanoseconds":652640000}', 'Binar Cerdas', '0', NULL);
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('nX06nVkmBqslkU5gQo1L', 'charisa@gmail.com', '0', 'scrypt:32768:8:1$RdaaalnzwqWMA08b$50f65fc356ce112d588b3f9f2b66c096011c63177d2474648cf6baa64738342d71dedcb26a26ff2d07b03263373474b3b28defdf43e4f1a42c14e09d0b3642d9', 'admin', NULL, '0812-1212-0218', NULL, '{"_seconds":1787413498,"_nanoseconds":851811000}', 'Ka Caca', '0', 'false');
INSERT INTO "users" ("id", "email", "sisa_pertemuan", "password", "role", "kelas", "phone", "jenjang", "created_at", "name", "total_pertemuan_dibeli", "akses_materi_gratis") VALUES ('oQm7py3kCZcxlWBsZh2B', 'andikaaskharr@gmail.com', '1', 'scrypt:32768:8:1$E6YRxPiO2XvOxvVf$b640bfb6e39e857e56a9f158b4bc6ee9409c4d5aa8d4762545867c71f934050cf88312c6aeb3e71b3322d8faf254cdcad79060498c231cb268570fe756da3d43', 'siswa', '11', '081213372173', 'SMA', '{"_seconds":1788528578,"_nanoseconds":755447000}', 'ANDIKA ASKHAR EFFENDI', '2', NULL);
