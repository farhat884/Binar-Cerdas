// Cegah browser mobile "mewarisi" posisi scroll & state menu dari halaman
// sebelumnya saat pindah halaman (penyebab tampilan navbar terlihat
// acak/​tertumpuk sesaat setelah klik link di menu hamburger).
if ("scrollRestoration" in history) {
  history.scrollRestoration = "manual";
}
window.scrollTo(0, 0);

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

  // Pastikan menu selalu mulai dalam keadaan tertutup tiap halaman dimuat,
  // bahkan jika browser sempat "mengingat" state terbuka dari halaman lain.
  nav.classList.remove("is-open");
  toggle.setAttribute("aria-expanded", "false");

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
// Render ulang rumus/matriks LaTeX (MathJax) di dalam sebuah elemen.
// Dipanggil tiap kali ada konten baru yang disisipkan lewat innerHTML
// (hasil jawaban, penjelasan AI, chat AI, preview soal di form admin),
// soalnya MathJax cuma otomatis jalan sekali pas halaman pertama dimuat.
window.typesetMath = function (el) {
  const target = el || document.body;
  if (window.MathJax && window.MathJax.typesetPromise) {
    window.MathJax.typesetPromise([target]).catch((err) => console.error("MathJax error:", err));
  }
};

// Ambil teks lengkap satu pilihan jawaban ("D. isi pilihannya") dari dalam
// satu blok soal (qEl), berdasarkan hurufnya (A/B/C/D). Dipakai di halaman
// latihan & ujian supaya hasil "Jawaban kamu" / "Jawaban benar" gak cuma
// nongolin hurufnya doang (dulu siswa bingung liat "D" doang tanpa tau isinya).
// Fallback ke huruf polos kalau labelnya gak ketemu di DOM.
window.teksPilihanDariForm = function (qEl, huruf) {
  if (!huruf) return "-";
  if (!qEl) return huruf;
  const input = qEl.querySelector('input[type="radio"][value="' + CSS.escape(huruf) + '"]');
  const label = input ? input.closest("label") : null;
  if (!label) return huruf;
  const teks = (label.textContent || "").replace(/\s+/g, " ").trim();
  return teks || huruf;
};

// Preview LaTeX langsung di form Bank Soal (biar admin bisa lihat soal
// matriks/pecahan/dll ke-render sebelum disimpan). Tinggal kasih atribut
// data-latex-source="id-elemen-preview" di textarea/input sumbernya.
function initLatexLivePreview() {
  document.querySelectorAll("[data-latex-source]").forEach((sourceEl) => {
    const previewEl = document.getElementById(sourceEl.dataset.latexSource);
    if (!previewEl || previewEl.dataset.latexReady === "1") return;
    previewEl.dataset.latexReady = "1";
    let timer = null;
    const render = () => {
      previewEl.textContent = sourceEl.value.trim() || "Preview bakal muncul di sini...";
      window.typesetMath(previewEl);
    };
    sourceEl.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(render, 300);
    });
    render();
  });
}
document.addEventListener("DOMContentLoaded", initLatexLivePreview);

// Tombol bantu Pangkat (xⁿ) & Bawah/Subscript (xₙ) di tiap field yang punya
// data-latex-source (Pertanyaan & Pilihan A-D, di form Tambah maupun Edit
// Soal). Dibikin biar admin gak perlu hafal syntax LaTeX buat pangkat
// (contoh soal matematika, mis. x^2) atau subscript (contoh rumus kimia,
// mis. C6H12O6 -> C6H12O6 dengan angka di bawah).
//
// Caranya: ketik dulu teksnya biasa (misal "x2" atau "C6H12O6"), lalu BLOK
// angka/huruf yang mau dijadikan pangkat/bawah (misal blok angka "2"-nya
// aja), baru klik tombolnya. Bagian yang diblok bakal otomatis dibungkus
// jadi LaTeX ($basis^{blok}$ atau $basis_{blok}$) dan langsung ke-render di
// preview di bawahnya.
function initLatexToolbar() {
  document.querySelectorAll("[data-latex-source]").forEach((sourceEl) => {
    if (sourceEl.dataset.latexToolbarReady === "1") return;
    sourceEl.dataset.latexToolbarReady = "1";

    const toolbar = document.createElement("div");
    toolbar.className = "latex-toolbar";

    const btnPangkat = document.createElement("button");
    btnPangkat.type = "button";
    btnPangkat.className = "latex-toolbar-btn";
    btnPangkat.innerHTML = "x<sup>n</sup> Pangkat";
    btnPangkat.title = 'Blok angka/hurufnya dulu (misal "2" di "x2"), baru klik tombol ini.';
    btnPangkat.addEventListener("click", () => terapkanLatexPangkatSubscript(sourceEl, "^", "pangkat"));

    const btnSubscript = document.createElement("button");
    btnSubscript.type = "button";
    btnSubscript.className = "latex-toolbar-btn";
    btnSubscript.innerHTML = "x<sub>n</sub> Bawah";
    btnSubscript.title = 'Buat rumus kimia dll: blok angkanya dulu (misal "6" di "C6"), baru klik tombol ini.';
    btnSubscript.addEventListener("click", () => terapkanLatexPangkatSubscript(sourceEl, "_", "bawah/subscript"));

    toolbar.appendChild(btnPangkat);
    toolbar.appendChild(btnSubscript);
    sourceEl.parentNode.insertBefore(toolbar, sourceEl);
  });
}

function terapkanLatexPangkatSubscript(el, simbol, labelJenis) {
  const value = el.value;
  const start = el.selectionStart;
  const end = el.selectionEnd;
  const terpilih = value.slice(start, end);

  if (!terpilih) {
    alert('Blok/pilih dulu angka atau hurufnya di dalam kotak teks (misal blok "2" pada "x2"), baru klik tombol ini.');
    el.focus();
    return;
  }

  // Cari "basis" (huruf/angka/tutup kurung) yang nempel PERSIS sebelum bagian
  // yang diblok, misal basis "x" pada "x2" kalau yang diblok "2"-nya.
  let basisStart = start;
  const basisRegex = /[A-Za-z0-9)\]}]/;
  while (basisStart > 0 && basisRegex.test(value[basisStart - 1])) basisStart--;

  if (basisStart === start) {
    alert("Ketik dulu angka/hurufnya sebelum bagian yang diblok (contoh: ketik \"x\" sebelum blok pangkatnya), baru klik tombol " + labelJenis + " ini.");
    el.focus();
    return;
  }

  const basis = value.slice(basisStart, start);
  const pengganti = "$" + basis + simbol + "{" + terpilih + "}$";
  el.value = value.slice(0, basisStart) + pengganti + value.slice(end);

  const posisiKursor = basisStart + pengganti.length;
  el.setSelectionRange(posisiKursor, posisiKursor);
  el.focus();
  el.dispatchEvent(new Event("input", { bubbles: true }));
}
document.addEventListener("DOMContentLoaded", initLatexToolbar);

function initAIChat(box) {
  if (box.dataset.aiChatReady === "1") return; // jangan pasang listener dobel
  box.dataset.aiChatReady = "1";
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
    window.typesetMath(div);
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
          selected: box.dataset.selected || "",
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
      window.typesetMath(pendingEl);
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