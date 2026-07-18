// Dialogue d'impression / export d'un arbre (SVG) : format, orientation,
// sortie PDF (via impression), PNG (canvas) ou SVG. Ouvre une modale.
import { h } from "../noyau/dom.js";
import { ouvrirModale, fermerModale } from "./modale.js";
import { toast } from "./toast.js";

const FORMATS = { A4: [210, 297], A3: [297, 420] };   // mm

export function dialogueExportArbre(svg, nom = "arbre") {
  if (!svg) { toast("Rien à exporter."); return; }
  // le SVG affiché porte des dimensions px (dues au zoom) : on exporte une
  // copie « propre » sans ces styles, pour que les tailles page/HTML priment.
  svg = svg.cloneNode(true);
  svg.style.width = ""; svg.style.height = ""; svg.style.maxWidth = "";
  const selFormat = h("select", {}, ...Object.keys(FORMATS).map((f) => h("option", { value: f }, f)));
  const selOrient = h("select", {},
    h("option", { value: "portrait" }, "Portrait"),
    h("option", { value: "paysage" }, "Paysage"));

  // Dimensions utiles : la page tourne réellement selon l'orientation, et le
  // SVG est ajusté (en mm) pour tenir dans la zone imprimable en gardant ses
  // proportions — ainsi Portrait/Paysage change bien le rendu.
  function dimsPage() {
    const [court, long] = FORMATS[selFormat.value];
    const paysage = selOrient.value === "paysage";
    const marge = 10;
    const pageW = paysage ? long : court;
    const pageH = paysage ? court : long;
    const vb = (svg.getAttribute("viewBox") || "0 0 1 1").split(/\s+/).map(Number);
    const ratio = (vb[2] || 1) / (vb[3] || 1);
    let w = pageW - 2 * marge;
    let ht = w / ratio;
    if (ht > pageH - 2 * marge) { ht = pageH - 2 * marge; w = ht * ratio; }
    return { pageW, pageH, marge, w, ht };
  }

  function pdf() {
    const { pageW, pageH, marge, w, ht } = dimsPage();
    const cadre = h("iframe", { style: "position:fixed;right:0;bottom:0;width:0;height:0;border:0" });
    document.body.append(cadre);
    const doc = cadre.contentDocument;
    doc.open();
    doc.write("<!doctype html><html><head><meta charset='utf-8'><style>"
      + "@page{size:" + pageW + "mm " + pageH + "mm;margin:" + marge + "mm}"
      + "html,body{margin:0;height:100%}"
      + "body{display:flex;align-items:center;justify-content:center}"
      + "svg{display:block;width:" + w.toFixed(1) + "mm;height:" + ht.toFixed(1) + "mm}"
      + "</style></head><body>" + svg.outerHTML + "</body></html>");
    doc.close();
    setTimeout(() => { cadre.contentWindow.focus(); cadre.contentWindow.print();
      setTimeout(() => cadre.remove(), 1000); }, 300);
    fermerModale();
  }

  // Export HTML autonome et INTERACTIF : un seul fichier, zoom (molette/boutons),
  // déplacement (glisser), plein écran — ouvrable et partageable, sans réseau.
  async function urlDataURI(url) {
    const rep = await fetch(url);
    const blob = await rep.blob();
    return await new Promise((res, rej) => {
      const fr = new FileReader();
      fr.onload = () => res(fr.result); fr.onerror = rej;
      fr.readAsDataURL(blob);
    });
  }

  async function htmlFichier() {
    // page autonome (logo embarqué en base64) : partageable / publiable telle
    // quelle, sans réseau. Aucune barre de défilement : on navigue au glisser
    // et à la molette, l'arbre est recadré via une transformation CSS.
    const [logo, meta] = await Promise.all([
      urlDataURI("/logo-lanceur.png").catch(() => ""),
      fetch("/api/espace").then((r) => r.json()).catch(() => ({})),
    ]);
    const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const nomArbre = esc(meta && meta.nom ? meta.nom : "Arbre généalogique");
    const sousTitre = esc("Arbre généalogique"
      + (meta && meta.personnes ? " · " + meta.personnes + " personnes" : ""));
    const logoImg = logo ? "<img class='logo' src='" + logo + "' alt='Arboriane'>" : "";
    // le SVG exporté doit porter une taille EXPLICITE = son viewBox : sinon il
    // s'étale à 100 % de la page et le cadrage (calculé sur le viewBox) le
    // décale et le rapetisse. On fixe width/height = viewBox sur une copie.
    const svgHtml = (() => {
      const c = svg.cloneNode(true);
      const vb = (c.getAttribute("viewBox") || "0 0 100 100").split(/\s+/).map(Number);
      c.setAttribute("width", vb[2] || 100);
      c.setAttribute("height", vb[3] || 100);
      c.style.width = ""; c.style.height = ""; c.style.maxWidth = "";
      return c.outerHTML;
    })();
    const doc = "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
      + "<meta name='viewport' content='width=device-width,initial-scale=1'>"
      + "<title>" + nomArbre + " — Arboriane</title><style>"
      + ":root{--vert:#1f4636;--terre:#c76b2a}"
      + "*{box-sizing:border-box;scrollbar-width:none;-ms-overflow-style:none}"
      + "*::-webkit-scrollbar{width:0;height:0;display:none}"
      + "html,body{margin:0;height:100%;overflow:hidden;color:#2b2b2b;"
      + "user-select:none;-webkit-user-select:none;"   // le glisser ne sélectionne plus les noms
      + "font-family:'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif}"
      + "body{background:radial-gradient(120% 90% at 50% 0%,#fcf9f2 0%,#ece2cf 100%)}"
      + "header{position:fixed;top:0;left:0;right:0;height:86px;display:flex;align-items:center;gap:16px;"
      + "padding:0 26px;background:rgba(255,255,255,.82);backdrop-filter:blur(8px);"
      + "border-bottom:1px solid #e7dec9;z-index:6}"
      + "header .logo{height:62px;width:auto;flex:none}"
      + "header h1{margin:0;font-size:20px;font-weight:700;color:var(--vert);letter-spacing:-.01em}"
      + "header p{margin:3px 0 0;font-size:12.5px;color:#94886c;letter-spacing:.03em}"
      + "#vp{position:absolute;inset:86px 0 0 0;overflow:hidden;cursor:grab;touch-action:none}"
      + "#vp.drag{cursor:grabbing}#wrap{transform-origin:0 0}#wrap svg{display:block}"
      + ".tb{position:fixed;right:18px;bottom:18px;display:flex;gap:7px;z-index:6}"
      + ".tb button{width:40px;height:40px;border:1px solid #e2dac6;background:rgba(255,255,255,.92);"
      + "border-radius:11px;cursor:pointer;font-size:17px;color:var(--vert);"
      + "box-shadow:0 2px 5px rgba(60,50,30,.09)}"
      + ".tb button:hover{border-color:var(--terre);color:var(--terre)}"
      + "footer{position:fixed;left:20px;bottom:15px;font-size:11px;color:#a99e84;z-index:5}"
      + "footer b{color:var(--vert)}"
      + "@media print{header{position:static}.tb,footer{display:none}"
      + "#vp{position:static;inset:auto;height:auto}#wrap{transform:none!important}}"
      + "</style></head><body>"
      + "<header>" + logoImg + "<div><h1>" + nomArbre + "</h1><p>" + sousTitre + "</p></div></header>"
      + "<div class='tb'><button onclick='z(1.2)' title='Zoom avant'>＋</button>"
      + "<button onclick='z(0.83)' title='Zoom arrière'>－</button>"
      + "<button onclick='fit()' title='Tout voir'>⛶</button>"
      + "<button onclick='fs()' title='Plein écran'>⤢</button></div>"
      + "<div id='vp'><div id='wrap'>" + svgHtml + "</div></div>"
      + "<footer>Créé avec <b>Arboriane</b> · atelier de généalogie local et privé"
      + " · <a href='https://buymeacoffee.com/arborianea5' target='_blank'"
      + " rel='noopener noreferrer' style='color:#c76b2a;text-decoration:none;font-weight:600'>"
      + "☕ Offrir un café</a></footer>"
      + "<script>"
      + "var s=1,tx=0,ty=0,vp=document.getElementById('vp'),wr=document.getElementById('wrap');"
      + "function ap(){wr.style.transform='translate('+tx+'px,'+ty+'px) scale('+s+')';}"
      + "function z(k){s=Math.max(.1,Math.min(6,s*k));ap();}"
      + "function fit(){var g=wr.querySelector('svg'),v=g.viewBox.baseVal,r=vp.getBoundingClientRect();"
      + "s=Math.min(r.width/v.width,r.height/v.height)*.92;s=Math.min(s,1.4);"   // cadré + zoom raisonnable pour un écran classique
      + "tx=(r.width-v.width*s)/2;ty=(r.height-v.height*s)/2;ap();}"
      + "function fs(){if(!document.fullscreenElement)document.documentElement.requestFullscreen();else document.exitFullscreen();}"
      + "var dn=false,ox,oy,tx0,ty0;"
      + "vp.addEventListener('pointerdown',function(e){dn=true;ox=e.clientX;oy=e.clientY;tx0=tx;ty0=ty;vp.classList.add('drag');vp.setPointerCapture(e.pointerId);});"
      + "vp.addEventListener('pointermove',function(e){if(!dn)return;tx=tx0+e.clientX-ox;ty=ty0+e.clientY-oy;ap();});"
      + "vp.addEventListener('pointerup',function(){dn=false;vp.classList.remove('drag');});"
      + "vp.addEventListener('wheel',function(e){e.preventDefault();var r=vp.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,k=e.deltaY<0?1.1:.9,ns=Math.max(.1,Math.min(6,s*k)),f=ns/s;tx=mx-(mx-tx)*f;ty=my-(my-ty)*f;s=ns;ap();},{passive:false});"
      + "window.addEventListener('load',function(){setTimeout(fit,30);});"
      + "<\/script></body></html>";
    const blob = new Blob([doc], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = nom + ".html"; a.click();
    toast("Arbre exporté en page HTML élégante."); fermerModale();
  }

  function png() {
    const xml = new XMLSerializer().serializeToString(svg);
    const vb = svg.getAttribute("viewBox");
    const [ , , vw, vh] = vb ? vb.split(/\s+/).map(Number) : [0, 0, 1200, 900];
    const echelle = 2;
    const canvas = document.createElement("canvas");
    canvas.width = vw * echelle; canvas.height = vh * echelle;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fffdf8"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob); a.download = nom + ".png"; a.click();
        toast("Image PNG exportée."); fermerModale();
      });
    };
    img.onerror = () => { toast("Export PNG impossible — utilisez SVG ou PDF."); };
    img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(xml)));
  }

  function svgFichier() {
    const blob = new Blob([svg.outerHTML], { type: "image/svg+xml" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = nom + ".svg"; a.click();
    toast("Arbre exporté en SVG."); fermerModale();
  }

  ouvrirModale(h("div", {},
    h("div", { style: "display:flex;gap:12px;margin-bottom:16px" },
      h("div", {}, h("label", {}, "Format"), selFormat),
      h("div", {}, h("label", {}, "Orientation"), selOrient)),
    h("p", { class: "sous-titre" },
      "PDF passe par l'impression du navigateur (choisissez « Enregistrer en PDF »)."),
    h("div", { class: "barre-actions" },
      h("button", { class: "bouton", onclick: pdf }, "🖨 Imprimer / PDF"),
      h("button", { class: "bouton secondaire", onclick: png }, "🖼 PNG"),
      h("button", { class: "bouton secondaire", onclick: htmlFichier }, "🌐 HTML"),
      h("button", { class: "bouton secondaire", onclick: svgFichier }, "SVG"),
      h("button", { class: "bouton fantome", onclick: fermerModale }, "Fermer"))),
    { titre: "Imprimer / exporter l'arbre" });
}
