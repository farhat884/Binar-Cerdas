// Taburkan bintang kecil di hero secara acak (murni dekoratif, hormati prefers-reduced-motion lewat CSS)
document.addEventListener("DOMContentLoaded", () => {
  const starsWrap = document.querySelector(".hero .stars");
  if (starsWrap) {
    const total = 26;
    for (let i = 0; i < total; i++) {
      const s = document.createElement("span");
      s.style.top = Math.random() * 100 + "%";
      s.style.left = Math.random() * 100 + "%";
      s.style.animationDelay = (Math.random() * 2.6).toFixed(2) + "s";
      starsWrap.appendChild(s);
    }
  }

  // Kalkulator harga & jumlah pertemuan interaktif di form "Daftar Les / Beli Paket"
  const paketInput = document.getElementById("jumlah_paket");
  const hargaOut = document.getElementById("preview-harga");
  const pertemuanOut = document.getElementById("preview-pertemuan");
  if (paketInput && hargaOut && pertemuanOut) {
    const hargaPerPaket = parseInt(paketInput.dataset.harga, 10);
    const pertemuanPerPaket = parseInt(paketInput.dataset.pertemuan, 10);
    const update = () => {
      const jumlah = Math.max(1, Math.min(4, parseInt(paketInput.value || "1", 10)));
      const totalHarga = jumlah * hargaPerPaket;
      const totalPertemuan = jumlah * pertemuanPerPaket;
      hargaOut.textContent = "Rp" + totalHarga.toLocaleString("id-ID");
      pertemuanOut.textContent = totalPertemuan + "x pertemuan";
    };
    paketInput.addEventListener("input", update);
    update();
  }

  // Konfirmasi sebelum aksi admin yang mengubah data siswa
  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
  });

  // Auto-hilangkan flash message setelah beberapa detik
  document.querySelectorAll(".flash .alert").forEach((el, i) => {
    setTimeout(() => {
      el.style.transition = "opacity .4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 5000 + i * 300);
  });
});
