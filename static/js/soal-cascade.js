// Dipakai di form Tambah Soal, Impor Soal, dan Edit Soal (juga Tambah/Edit Materi)
// biar Kelas/Mapel/Bab/Tahapan Materi semuanya jadi dropdown yang saling
// terhubung (bukan ketik manual), jadi gak ada typo yang bikin soal "gak
// kebaca" nyambung ke bab/materinya.
//
// Sebelum script ini dipanggil, halaman harus sudah nyiapin:
//   window.SOAL_PROGRAM_MAP = {"SD":{"kelas":[...],"mapel":[...]}, ...}
//   window.SOAL_MATERIALS   = [{id,jenjang,kelas,mapel,bab,judul,urutan_bab,urutan_subbab}, ...]
//
// wireSoalCascade(prefix, opts) menghubungkan elemen dengan id:
//   {prefix}jenjang, {prefix}kelas, {prefix}mapel, {prefix}tipe (opsional),
//   {prefix}bab, {prefix}wrap_bab (opsional, buat show/hide),
//   {prefix}material_id, {prefix}wrap_material (opsional, buat show/hide)
(function () {
  function populateSelect(sel, options, initialValue, placeholder) {
    if (!sel) return;
    const keep = initialValue !== undefined && initialValue !== null ? initialValue : sel.value;
    sel.innerHTML = "";
    if (placeholder !== null && placeholder !== undefined) {
      const o = document.createElement("option");
      o.value = "";
      o.textContent = placeholder;
      sel.appendChild(o);
    }
    options.forEach((opt) => {
      const o = document.createElement("option");
      o.value = opt.value;
      o.textContent = opt.label;
      sel.appendChild(o);
    });
    if (keep && options.some((o) => String(o.value) === String(keep))) {
      sel.value = keep;
    }
  }

  function wireSoalCascade(prefix, opts) {
    opts = opts || {};
    const jenjangEl = document.getElementById(prefix + "jenjang");
    const kelasEl = document.getElementById(prefix + "kelas");
    const mapelEl = document.getElementById(prefix + "mapel");
    const tipeEl = document.getElementById(prefix + "tipe");
    const babWrap = document.getElementById(prefix + "wrap_bab");
    const babEl = document.getElementById(prefix + "bab");
    const materiWrap = document.getElementById(prefix + "wrap_material");
    const materiEl = document.getElementById(prefix + "material_id");
    if (!jenjangEl || !kelasEl || !mapelEl) return;

    const PROGRAM_MAP = window.SOAL_PROGRAM_MAP || {};
    const MATERIALS = window.SOAL_MATERIALS || [];

    // Simpan nilai awal (dari data yang sudah tersimpan, kalau ini halaman Edit)
    // sebelum select-nya dikosongin & diisi ulang lewat JS.
    const initialKelas = kelasEl.dataset.initial !== undefined ? kelasEl.dataset.initial : kelasEl.value;
    const initialMapel = mapelEl.dataset.initial !== undefined ? mapelEl.dataset.initial : mapelEl.value;
    const initialBab = babEl ? (babEl.dataset.initial !== undefined ? babEl.dataset.initial : babEl.value) : "";
    const initialMateri = materiEl ? (materiEl.dataset.initial !== undefined ? materiEl.dataset.initial : materiEl.value) : "";
    let firstRun = true;

    function syncKelasMapel() {
      const j = jenjangEl.value;
      const prog = PROGRAM_MAP[j] || { kelas: [], mapel: [] };
      populateSelect(kelasEl, prog.kelas.map((k) => ({ value: k, label: k })), firstRun ? initialKelas : undefined);
      populateSelect(mapelEl, prog.mapel.map((m) => ({ value: m, label: m })), firstRun ? initialMapel : undefined);
      syncBab();
    }

    function syncBab() {
      if (!babEl) return;
      const j = jenjangEl.value, k = kelasEl.value, m = mapelEl.value;
      const babs = [];
      const seen = new Set();
      MATERIALS.filter((x) => x.jenjang === j && String(x.kelas) === String(k) && x.mapel === m)
        .sort((a, b) => (a.urutan_bab || 1) - (b.urutan_bab || 1))
        .forEach((x) => {
          if (!seen.has(x.bab)) { seen.add(x.bab); babs.push(x.bab); }
        });
      populateSelect(babEl, babs.map((b) => ({ value: b, label: b })), firstRun ? initialBab : undefined, "-- Pilih Bab --");
      syncMateri();
    }

    function syncMateri() {
      if (!materiEl) return;
      const j = jenjangEl.value, k = kelasEl.value, m = mapelEl.value, b = babEl ? babEl.value : "";
      const list = MATERIALS.filter((x) => x.jenjang === j && String(x.kelas) === String(k) && x.mapel === m && (!b || x.bab === b))
        .sort((a, c) => (a.urutan_subbab || 1) - (c.urutan_subbab || 1));
      populateSelect(materiEl, list.map((x) => ({ value: x.id, label: (x.urutan_subbab || 1) + ". " + x.judul })), firstRun ? initialMateri : undefined, "-- Pilih Tahapan Materi --");
      firstRun = false;
    }

    function syncTipeVisibility() {
      if (!tipeEl) return;
      const t = tipeEl.value;
      const showBab = t === "latihan" || t === "UH";
      const showMateri = t === "latihan";
      if (babWrap) babWrap.style.display = showBab ? "" : "none";
      if (materiWrap) materiWrap.style.display = showMateri ? "" : "none";
      if (!showBab && babEl) babEl.value = "";
      if (!showMateri && materiEl) materiEl.value = "";
    }

    jenjangEl.addEventListener("change", syncKelasMapel);
    kelasEl.addEventListener("change", syncBab);
    mapelEl.addEventListener("change", syncBab);
    if (babEl) babEl.addEventListener("change", syncMateri);
    if (tipeEl) tipeEl.addEventListener("change", syncTipeVisibility);

    syncKelasMapel();
    syncTipeVisibility();
  }

  window.wireSoalCascade = wireSoalCascade;

  // Baris "Edit Banyak Soal Sekaligus" di Bank Soal: tiap baris punya select
  // Mapel, Bab, dan Tahapan Materi sendiri yang saling terhubung (mapel
  // nentuin pilihan bab, bab nentuin pilihan tahapan materi), semuanya
  // dropdown biar gak ada typo. Jenjang & Kelas soal itu sendiri gak diubah
  // di sini (tetap lewat tombol Edit satu-satu).
  window.wireBulkRowSelects = function () {
    const PROGRAM_MAP = window.SOAL_PROGRAM_MAP || {};
    const MATERIALS = window.SOAL_MATERIALS || [];

    function babOptionsFor(jenjang, kelas, mapel) {
      const seen = new Set();
      const babs = [];
      MATERIALS.filter((x) => x.jenjang === jenjang && String(x.kelas) === String(kelas) && x.mapel === mapel)
        .sort((a, b) => (a.urutan_bab || 1) - (b.urutan_bab || 1))
        .forEach((x) => { if (!seen.has(x.bab)) { seen.add(x.bab); babs.push(x.bab); } });
      return babs;
    }

    function materiOptionsFor(jenjang, kelas, mapel, bab) {
      return MATERIALS.filter((x) => x.jenjang === jenjang && String(x.kelas) === String(kelas) && x.mapel === mapel && (!bab || x.bab === bab))
        .sort((a, b) => (a.urutan_subbab || 1) - (b.urutan_subbab || 1));
    }

    function syncRowBab(row, keepCurrent) {
      const mapelSel = row.querySelector(".bulk-mapel-select");
      const babSel = row.querySelector(".bulk-bab-select");
      if (!mapelSel || !babSel) return;
      const jenjang = babSel.dataset.jenjang, kelas = babSel.dataset.kelas;
      const babs = babOptionsFor(jenjang, kelas, mapelSel.value);
      populateSelect(babSel, babs.map((b) => ({ value: b, label: b })), keepCurrent ? babSel.dataset.current : undefined, "-- Pilih Bab --");
      syncRowMateri(row, keepCurrent);
    }

    function syncRowMateri(row, keepCurrent) {
      const mapelSel = row.querySelector(".bulk-mapel-select");
      const babSel = row.querySelector(".bulk-bab-select");
      const materiSel = row.querySelector(".bulk-materi-select");
      if (!mapelSel || !materiSel) return;
      const jenjang = materiSel.dataset.jenjang, kelas = materiSel.dataset.kelas;
      const list = materiOptionsFor(jenjang, kelas, mapelSel.value, babSel ? babSel.value : "");
      populateSelect(materiSel, list.map((x) => ({ value: x.id, label: (x.urutan_subbab || 1) + ". " + x.judul })), keepCurrent ? materiSel.dataset.current : undefined, "-- Tidak ada --");
    }

    document.querySelectorAll(".bulk-mapel-select").forEach((mapelSel) => {
      const row = mapelSel.closest("tr");
      const prog = PROGRAM_MAP[mapelSel.dataset.jenjang] || { mapel: [] };
      populateSelect(mapelSel, prog.mapel.map((m) => ({ value: m, label: m })), mapelSel.dataset.current);
      syncRowBab(row, true);
      mapelSel.addEventListener("change", () => syncRowBab(row, false));
    });
    document.querySelectorAll(".bulk-bab-select").forEach((babSel) => {
      babSel.addEventListener("change", () => syncRowMateri(babSel.closest("tr"), false));
    });
  };

  // Buat select "Bab" di tabel Edit Banyak Soal Sekaligus (Bank Soal) -- tiap
  // baris punya mapel/kelas/jenjang sendiri jadi diisi per-baris dari data
  // materi yang sama, biar milih bukan ketik.
  window.wireBulkBabSelects = function (selector) {
    const MATERIALS = window.SOAL_MATERIALS || [];
    document.querySelectorAll(selector).forEach((sel) => {
      const j = sel.dataset.jenjang, k = sel.dataset.kelas, m = sel.dataset.mapel;
      const current = sel.dataset.current || "";
      const seen = new Set();
      const babs = [];
      MATERIALS.filter((x) => x.jenjang === j && String(x.kelas) === String(k) && x.mapel === m)
        .sort((a, b) => (a.urutan_bab || 1) - (b.urutan_bab || 1))
        .forEach((x) => { if (!seen.has(x.bab)) { seen.add(x.bab); babs.push(x.bab); } });
      if (current && !seen.has(current)) babs.push(current);
      populateSelect(sel, babs.map((b) => ({ value: b, label: b })), current, "-- Pilih Bab --");
    });
  };
})();
