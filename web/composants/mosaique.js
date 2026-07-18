// Mosaïque A4 (L9) — imprime un grand arbre à taille LISIBLE, réparti sur
// plusieurs feuilles A4 avec repères de coupe et numéro de tuile (à assembler
// au mur). Rasterise le SVG affiché puis le découpe en pages.
//
// Limite connue : les photos (pastille « photo ») ne sont pas rasterisées par
// le navigateur quand le SVG est chargé comme image — la mosaïque est prévue
// pour les grands arbres texte / monogramme (le cas d'usage). 100 % local.
import { toast } from "./toast.js";

// Formats d'impression courants (mm). La feuille = la taille des tuiles :
// A4 = beaucoup de petites feuilles ; A0 = une grande affiche (copie-service).
const FORMATS = {
  A4: { court: 210, long: 297 },
  A3: { court: 297, long: 420 },
  A0: { court: 841, long: 1189 },
};

export async function imprimerMosaique(svgOrig,
    { orientation = "portrait", echelle = 1, format = "A4" } = {}) {
  if (!svgOrig) { toast("Rien à imprimer."); return; }
  const fmt = FORMATS[format] || FORMATS.A4;
  const svg = svgOrig.cloneNode(true);
  svg.style.width = ""; svg.style.height = ""; svg.style.maxWidth = "";
  const vb = (svg.getAttribute("viewBox") || "0 0 1 1").split(/\s+/).map(Number);
  const wSvg = vb[2] || 1, hSvg = vb[3] || 1;

  // Grandes feuilles (A0) : on baisse le dpi pour garder un canvas raisonnable.
  const dpi = format === "A0" ? 96 : format === "A3" ? 120 : 150;
  const pxParMm = dpi / 25.4;
  const mmParPx = 0.30 * echelle;                 // taille d'impression du SVG
  const wMm = wSvg * mmParPx, hMm = hSvg * mmParPx;
  const marge = 8;
  const pageW = orientation === "paysage" ? fmt.long : fmt.court;
  const pageH = orientation === "paysage" ? fmt.court : fmt.long;
  const utileW = pageW - 2 * marge, utileH = pageH - 2 * marge;
  const cols = Math.max(1, Math.ceil(wMm / utileW));
  const rows = Math.max(1, Math.ceil(hMm / utileH));

  let img;
  try { img = await svgVersImage(svg); }
  catch { toast("Rasterisation impossible."); return; }

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(cols * utileW * pxParMm));
  canvas.height = Math.max(1, Math.round(rows * utileH * pxParMm));
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, Math.round(wMm * pxParMm), Math.round(hMm * pxParMm));

  const tuileW = Math.round(utileW * pxParMm), tuileH = Math.round(utileH * pxParMm);
  const pages = [];
  try {
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const t = document.createElement("canvas");
      t.width = tuileW; t.height = tuileH;
      const tc = t.getContext("2d");
      tc.fillStyle = "#fff"; tc.fillRect(0, 0, tuileW, tuileH);
      tc.drawImage(canvas, c * tuileW, r * tuileH, tuileW, tuileH, 0, 0, tuileW, tuileH);
      pages.push({ url: t.toDataURL("image/png"), r, c });
    }
  } catch {
    toast("Impression mosaïque impossible (photos non rasterisables). "
      + "Réglez la pastille sur « Monogramme ».");
    return;
  }

  const cadre = document.createElement("iframe");
  cadre.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  document.body.append(cadre);
  const doc = cadre.contentDocument;
  doc.open();
  doc.write(pagesHTML(pages, pageW, pageH, marge, utileW, utileH));
  doc.close();
  setTimeout(() => {
    cadre.contentWindow.focus(); cadre.contentWindow.print();
    setTimeout(() => cadre.remove(), 1500);
  }, 400);
  toast(cols * rows + " feuille(s) " + format
    + (cols * rows > 1 ? " — assemblez selon les repères de coupe." : " — affiche unique."));
}

function svgVersImage(svg) {
  return new Promise((res, rej) => {
    const s = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = rej;
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(s);
  });
}

function pagesHTML(pages, pageW, pageH, marge, utileW, utileH) {
  const feuilles = pages.map((p) =>
    '<div class="feuille"><div class="rep">Ligne ' + (p.r + 1)
    + ' · Colonne ' + (p.c + 1) + '</div><img src="' + p.url + '"></div>').join("");
  return "<!doctype html><html><head><meta charset='utf-8'><style>"
    + "@page{size:" + pageW + "mm " + pageH + "mm;margin:" + marge + "mm}"
    + "html,body{margin:0}"
    + ".feuille{position:relative;width:" + utileW + "mm;height:" + utileH + "mm;"
    + "page-break-after:always;overflow:hidden}"
    + ".feuille img{width:" + utileW + "mm;height:" + utileH + "mm;display:block}"
    + ".rep{position:absolute;top:1mm;left:1mm;font:8pt 'Segoe UI',sans-serif;color:#aaa}"
    + ".feuille::before,.feuille::after{content:'';position:absolute;width:5mm;height:5mm}"
    + ".feuille::before{top:0;left:0;border-top:0.3mm solid #333;border-left:0.3mm solid #333}"
    + ".feuille::after{bottom:0;right:0;border-bottom:0.3mm solid #333;border-right:0.3mm solid #333}"
    + "</style></head><body>" + feuilles + "</body></html>";
}
