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

// Hamburger menu untuk navbar di layar mobile
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("navToggle");
  const nav = document.getElementById("mainNav");
  if (!toggle || !nav) return;

  function tutupMenu() {
    nav.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", () => {
    const terbuka = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", terbuka ? "true" : "false");
  });

  // Tutup menu otomatis kalau salah satu link diklik
  nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", tutupMenu));

  // Tutup menu kalau layar dibesarkan lagi (misal rotasi HP ke landscape/desktop)
  window.addEventListener("resize", () => {
    if (window.innerWidth > 860) tutupMenu();
  });
});
function initAIChat(box) {
  const questionId = box.dataset.questionId;
  const selected = box.dataset.selected || "";
  const url = box.dataset.url;
  const messagesEl = box.querySelector(".ai-chat-messages");
  const input = box.querySelector(".ai-chat-input");
  const sendBtn = box.querySelector(".ai-chat-send");
  let riwayat = [];

  function tambahBubble(role, text) {
    const div = document.createElement("div");
    div.className = "ai-chat-msg " + (role === "user" ? "user" : "ai");
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  async function kirim() {
    const pesan = input.value.trim();
    if (!pesan) return;
    input.value = "";
    sendBtn.disabled = true;
    tambahBubble("user", pesan);
    riwayat.push({ role: "user", content: pesan });
    const pendingEl = tambahBubble("ai", "Mengetik...");
    pendingEl.classList.add("pending");
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pesan: pesan,
          selected: selected,
          riwayat: riwayat.slice(0, -1),
        }),
      });
      const data = await res.json();
      pendingEl.classList.remove("pending");
      if (!res.ok) {
        pendingEl.textContent = data.error || "Gagal mengirim pertanyaan.";
      } else {
        pendingEl.textContent = data.balasan;
        riwayat.push({ role: "assistant", content: data.balasan });
      }
    } catch (err) {
      pendingEl.classList.remove("pending");
      pendingEl.textContent = "Gagal menghubungi AI, coba lagi ya.";
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.addEventListener("click", kirim);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); kirim(); }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".ai-chat").forEach(initAIChat);
});