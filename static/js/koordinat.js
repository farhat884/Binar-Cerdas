// ============================================================================
// KOORDINAT.JS — mini "LaTeX" khusus buat gambar bidang kartesius (segitiga,
// titik, vektor translasi, dll) di soal Transformasi Geometri / Matematika.
//
// KENAPA BUKAN TIKZ ASLI?
// TikZ butuh proses compile LaTeX penuh (pdflatex) yang berat & lambat kalau
// dijalanin tiap kali render soal di server (apalagi di Vercel serverless).
// Jadi solusinya: bikin syntax teks sederhana sendiri yang di-parse & di-
// gambar langsung di browser pakai SVG murni (mirip cara MathJax nge-render
// $...$ jadi rumus). Hasilnya jauh lebih ringan & instan.
//
// CARA PAKAI (di kolom "Pertanyaan" / "Penjelasan" admin, biasa aja, gak
// perlu HTML):
//
//   [[plot]]
//   A(1,1) B(4,1) C(1,3)
//   A'(3,4) B'(6,4) C'(3,6)
//   [[/plot]]
//
// Aturan tiap baris di dalam [[plot]]...[[/plot]]:
//   - 1 titik  -> digambar sebagai titik/dot aja.
//   - 2 titik  -> digambar sebagai garis/segmen.
//   - 3+ titik -> digambar sebagai bangun tertutup (segitiga/segi-n) dengan
//                 isian warna tipis. Tiap baris otomatis dapat warna beda
//                 (baris 1 hijau, baris 2 oranye, baris 3 biru, dst).
//   - Baris diawali "titik:" -> semua titik di baris itu digambar lepas
//     (gak disambung garis). Contoh: titik: O(0,0)
//   - Baris diawali "vektor:" -> gambar panah dari satu titik ke titik lain.
//     Contoh: vektor: (1,1)->(4,3)
//
// Bounding box (batas sumbu) dihitung otomatis dari semua titik yang ada.
// Kalau mau override manual, tambahin atribut di tag pembuka:
//   [[plot xmin=-2 xmax=8 ymin=-2 ymax=8]]
// ============================================================================

(function () {
  var PLOT_REGEX = /\[\[plot([^\]]*)\]\]([\s\S]*?)\[\[\/plot\]\]/gi;
  var POINT_REGEX = /([A-Za-z][A-Za-z0-9]*'*)?\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)/g;
  var VECTOR_REGEX = /\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)\s*(?:->|=>|\u2192)\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)/;
  var COLORS = ["#3B6D11", "#993C1D", "#185FA5", "#712B13", "#534AB7", "#04342C"];
  var svgCounter = 0;

  function parseAttrs(str) {
    var attrs = {};
    var re = /(\w+)\s*=\s*(-?\d+(?:\.\d+)?)/g;
    var m;
    while ((m = re.exec(str || "")) !== null) attrs[m[1]] = parseFloat(m[2]);
    return attrs;
  }

  function parseBlock(body) {
    var lines = body.split("\n").map(function (s) { return s.trim(); }).filter(Boolean);
    var shapes = [];
    var vectors = [];
    var allPoints = [];
    var colorIdx = 0;

    lines.forEach(function (line) {
      var lower = line.toLowerCase();

      if (lower.indexOf("vektor:") === 0 || lower.indexOf("vector:") === 0) {
        var rest = line.substring(line.indexOf(":") + 1);
        var vm = rest.match(VECTOR_REGEX);
        if (vm) {
          var from = { x: parseFloat(vm[1]), y: parseFloat(vm[2]) };
          var to = { x: parseFloat(vm[3]), y: parseFloat(vm[4]) };
          var labelMatch = rest.match(/\|\s*(.+)$/);
          vectors.push({ from: from, to: to, label: labelMatch ? labelMatch[1].trim() : "" });
          allPoints.push(from, to);
        }
        return;
      }

      var isPointOnly = lower.indexOf("titik:") === 0 || lower.indexOf("point:") === 0;
      var content = isPointOnly ? line.substring(line.indexOf(":") + 1) : line;
      var pts = [];
      var pm;
      POINT_REGEX.lastIndex = 0;
      while ((pm = POINT_REGEX.exec(content)) !== null) {
        pts.push({ label: pm[1] || "", x: parseFloat(pm[2]), y: parseFloat(pm[3]) });
      }
      if (!pts.length) return;
      allPoints = allPoints.concat(pts);

      var type = "dot";
      if (!isPointOnly) {
        if (pts.length === 2) type = "segment";
        else if (pts.length >= 3) type = "polygon";
      }
      shapes.push({ type: type, points: pts, color: COLORS[colorIdx % COLORS.length] });
      if (!isPointOnly) colorIdx++;
    });

    return { shapes: shapes, vectors: vectors, allPoints: allPoints };
  }

  function buildSvg(parsed, attrs) {
    var pts = parsed.allPoints;
    var xs = pts.map(function (p) { return p.x; }).concat([0]);
    var ys = pts.map(function (p) { return p.y; }).concat([0]);

    var xmin = attrs.xmin !== undefined ? attrs.xmin : Math.floor(Math.min.apply(null, xs) - 1);
    var xmax = attrs.xmax !== undefined ? attrs.xmax : Math.ceil(Math.max.apply(null, xs) + 1);
    var ymin = attrs.ymin !== undefined ? attrs.ymin : Math.floor(Math.min.apply(null, ys) - 1);
    var ymax = attrs.ymax !== undefined ? attrs.ymax : Math.ceil(Math.max.apply(null, ys) + 1);
    if (xmax <= xmin) xmax = xmin + 2;
    if (ymax <= ymin) ymax = ymin + 2;

    var PX_PER_UNIT = 40, MAX_W = 520, MAX_H = 380, PAD = 34;
    var rangeX = xmax - xmin, rangeY = ymax - ymin;
    var scale = PX_PER_UNIT;
    if (rangeX * scale > MAX_W) scale = MAX_W / rangeX;
    if (rangeY * scale > MAX_H) scale = MAX_H / rangeY;

    var w = rangeX * scale, h = rangeY * scale;
    var svgW = w + PAD * 2, svgH = h + PAD * 2;

    function X(x) { return PAD + (x - xmin) * scale; }
    function Y(y) { return PAD + (ymax - y) * scale; }

    var id = "kplot" + (++svgCounter);
    var parts = [];
    parts.push(
      '<svg width="100%" viewBox="0 0 ' + svgW + " " + svgH + '" xmlns="http://www.w3.org/2000/svg" ' +
      'style="max-width:' + Math.min(svgW, 480) + 'px;height:auto;display:block;font-family:inherit">'
    );
    parts.push(
      '<defs><marker id="' + id + 'arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" ' +
      'orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" ' +
      'stroke-linecap="round" stroke-linejoin="round"/></marker></defs>'
    );

    // grid tipis
    for (var gx = Math.ceil(xmin); gx <= xmax; gx++) {
      parts.push('<line x1="' + X(gx) + '" y1="' + Y(ymin) + '" x2="' + X(gx) + '" y2="' + Y(ymax) + '" stroke="#000" stroke-opacity="0.06" stroke-width="1"/>');
    }
    for (var gy = Math.ceil(ymin); gy <= ymax; gy++) {
      parts.push('<line x1="' + X(xmin) + '" y1="' + Y(gy) + '" x2="' + X(xmax) + '" y2="' + Y(gy) + '" stroke="#000" stroke-opacity="0.06" stroke-width="1"/>');
    }

    // sumbu x & y (kalau 0 ada di dalam rentang)
    if (xmin <= 0 && xmax >= 0) {
      parts.push('<line x1="' + X(0) + '" y1="' + Y(ymin) + '" x2="' + X(0) + '" y2="' + Y(ymax) + '" stroke="#444441" stroke-width="1"/>');
    }
    if (ymin <= 0 && ymax >= 0) {
      parts.push('<line x1="' + X(xmin) + '" y1="' + Y(0) + '" x2="' + X(xmax) + '" y2="' + Y(0) + '" stroke="#444441" stroke-width="1"/>');
    }

    // angka di sumbu (skip 0 biar gak numpuk sama label "O")
    var stepLabel = rangeX > 12 || rangeY > 12 ? 2 : 1;
    for (var lx = Math.ceil(xmin); lx <= xmax; lx++) {
      if (lx === 0 || lx % stepLabel !== 0) continue;
      parts.push('<text x="' + X(lx) + '" y="' + (Y(0) + 14) + '" font-size="11" fill="#5F5E5A" text-anchor="middle">' + lx + "</text>");
    }
    for (var ly = Math.ceil(ymin); ly <= ymax; ly++) {
      if (ly === 0 || ly % stepLabel !== 0) continue;
      parts.push('<text x="' + (X(0) - 8) + '" y="' + (Y(ly) + 4) + '" font-size="11" fill="#5F5E5A" text-anchor="end">' + ly + "</text>");
    }
    if (xmin <= 0 && xmax >= 0 && ymin <= 0 && ymax >= 0) {
      parts.push('<text x="' + (X(0) - 8) + '" y="' + (Y(0) + 14) + '" font-size="11" fill="#5F5E5A" text-anchor="end">O</text>');
    }

    // bangun (polygon/segmen/titik)
    parsed.shapes.forEach(function (shape) {
      var coords = shape.points.map(function (p) { return X(p.x) + "," + Y(p.y); }).join(" ");
      if (shape.type === "polygon") {
        parts.push('<polygon points="' + coords + '" fill="' + shape.color + '" fill-opacity="0.15" stroke="' + shape.color + '" stroke-width="1.5"/>');
      } else if (shape.type === "segment") {
        parts.push('<polyline points="' + coords + '" fill="none" stroke="' + shape.color + '" stroke-width="1.5"/>');
      }
      shape.points.forEach(function (p) {
        parts.push('<circle cx="' + X(p.x) + '" cy="' + Y(p.y) + '" r="3" fill="' + shape.color + '"/>');
        if (p.label) {
          var lbl = p.label + "(" + trimNum(p.x) + "," + trimNum(p.y) + ")";
          parts.push('<text x="' + (X(p.x) + 6) + '" y="' + (Y(p.y) - 6) + '" font-size="11" fill="' + shape.color + '" font-weight="600">' + escapeXml(lbl) + "</text>");
        }
      });
    });

    // vektor (panah)
    parsed.vectors.forEach(function (v) {
      var col = "#993C1D";
      parts.push('<line x1="' + X(v.from.x) + '" y1="' + Y(v.from.y) + '" x2="' + X(v.to.x) + '" y2="' + Y(v.to.y) + '" stroke="' + col + '" stroke-width="1.5" marker-end="url(#' + id + 'arrow)"/>');
      if (v.label) {
        var mx = (X(v.from.x) + X(v.to.x)) / 2, my = (Y(v.from.y) + Y(v.to.y)) / 2;
        parts.push('<text x="' + mx + '" y="' + (my - 6) + '" font-size="11" fill="' + col + '" font-weight="600" text-anchor="middle">' + escapeXml(v.label) + "</text>");
      }
    });

    parts.push("</svg>");
    return parts.join("");
  }

  function trimNum(n) {
    return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
  }

  function escapeXml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function renderMatch(fullMatch, attrsStr, body) {
    try {
      var attrs = parseAttrs(attrsStr);
      var parsed = parseBlock(body);
      if (!parsed.shapes.length && !parsed.vectors.length) return null;
      return buildSvg(parsed, attrs);
    } catch (e) {
      console.error("koordinat.js gagal render plot:", e);
      return null;
    }
  }

  // Cari semua text node di dalam `root` yang mengandung [[plot]]...[[/plot]],
  // lalu ganti bagian itu jadi elemen <span> berisi SVG hasil render.
  window.renderKoordinatPlots = function (root) {
    var target = root || document.body;
    var walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT, null);
    var nodes = [];
    var n;
    while ((n = walker.nextNode())) {
      if (n.nodeValue && n.nodeValue.indexOf("[[plot") !== -1) nodes.push(n);
    }

    nodes.forEach(function (textNode) {
      var text = textNode.nodeValue;
      PLOT_REGEX.lastIndex = 0;
      var lastIndex = 0;
      var frag = document.createDocumentFragment();
      var m;
      var found = false;

      while ((m = PLOT_REGEX.exec(text)) !== null) {
        var svgHtml = renderMatch(m[0], m[1], m[2]);
        if (svgHtml === null) continue;
        found = true;
        if (m.index > lastIndex) {
          frag.appendChild(document.createTextNode(text.substring(lastIndex, m.index)));
        }
        var wrap = document.createElement("span");
        wrap.className = "koordinat-plot";
        wrap.style.display = "block";
        wrap.style.margin = "10px 0";
        wrap.innerHTML = svgHtml;
        frag.appendChild(wrap);
        lastIndex = PLOT_REGEX.lastIndex;
      }

      if (!found) return;
      if (lastIndex < text.length) {
        frag.appendChild(document.createTextNode(text.substring(lastIndex)));
      }
      textNode.parentNode.replaceChild(frag, textNode);
    });
  };
})();
