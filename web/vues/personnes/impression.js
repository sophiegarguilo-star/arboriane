// Personnes — impression d'une fiche complète (tous les onglets, prête pour
// classeur). Ouvre une fenêtre HTML autonome et lance l'impression.
import { apiGet } from "../../noyau/api.js";
import { toast } from "../../composants/toast.js";
import { brancheDeSosa, majuscule, modeleAnnee, RESN_LABEL, EVT_LABEL } from "./commun.js";

export async function imprimerFiche(f, pid) {
  const pv = await apiGet("/api/individus/" + pid + "/preuves").catch(() => null);
  const org = window.location.origin;
  const e = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const sections = [];

  // 1) En-tête
  const princ = (f.medias || []).find((m) => m.principale) || (f.medias || [])[0];
  const prof = (f.professions || []).map((p) => p.valeur).filter(Boolean).join(", ");
  const branche = brancheDeSosa(f.sosa);
  const badges = [
    f.sosa ? "Sosa n° " + f.sosa + (f.sosa > 1 ? " · Ancêtre direct" : "") : "",
    branche || "", f.vivant ? "Présumé vivant" : "Décédé",
    f.resn ? (RESN_LABEL[f.resn] || f.resn) : "", ...(f.tags || []).map((t) => "#" + t),
  ].filter(Boolean);
  const initiale = ((f.nom_complet || f.nom || "?").trim().charAt(0) || "?").toUpperCase();
  const avatar = princ
    ? '<img class="portrait" src="' + org + '/media/Photos/' + encodeURIComponent(princ.fichier) + '">'
    : '<div class="mono mono-' + (f.sexe || "U") + '">' + e(initiale) + '</div>';
  sections.push(
    '<header class="tete">'
    + avatar
    + '<div><h1>' + e(f.nom_complet) + (f.nom_suffixe ? " " + e(f.nom_suffixe) : "") + '</h1>'
    + '<div class="sub">' + e([(f.periode || "dates inconnues") + (f.age != null ? " · " + f.age + " ans" : ""), prof].filter(Boolean).join(" · ")) + '</div>'
    + (f.relation_racine && f.racine_nom ? '<div class="rel">' + e(majuscule(f.relation_racine) + " de " + f.racine_nom) + '</div>' : '')
    + (badges.length ? '<div class="badges">' + badges.map((b) => '<span>' + e(b) + '</span>').join("") + '</div>' : '')
    + '</div></header>');

  // 2) Identité
  const dl = (pairs) => {
    const rows = pairs.filter(([, v]) => v != null && v !== "")
      .map(([k, v]) => '<dt>' + e(k) + '</dt><dd>' + e(v) + '</dd>').join("");
    return rows ? '<dl>' + rows + '</dl>' : '';
  };
  const variantes = (f.noms_alternatifs || []).map((v) => [v.prenoms, v.nom].filter(Boolean).join(" ")).filter(Boolean).join(" · ");
  sections.push('<h2 class="grp">Synthèse</h2>');
  sections.push('<section class="bloc"><h2>Identité</h2>' + dl([
    ["Nom de référence", f.nom], ["Prénoms", f.prenoms], ["Prénom usuel", f.prenom_principal],
    ["Préfixe", f.nom_prefixe], ["Suffixe", f.nom_suffixe],
    ["Surnom", f.surnom ? "« " + f.surnom + " »" : ""], ["Nom marital", f.nom_marital],
    ["Variantes", variantes],
    ["Sexe", ({ M: "Masculin", F: "Féminin", X: "Intersexe", N: "Non consigné" })[f.sexe] || "Inconnu"],
    ["Statut", f.vivant ? "Présumé vivant" : "Décédé"],
    ["N° de référence", f.refn], ["Confidentialité", f.resn ? (RESN_LABEL[f.resn] || f.resn) : ""],
    ["Identifiant", f.id],
  ]) + '</section>');

  // 3) Repères de vie
  const nais = f.naissance || {}, dec = f.deces || {};
  const lieuxVie = []; const vus = new Set();
  [(nais.lieu), ...(f.residences || []).map((r) => r.lieu), ...(f.evenements || []).map((ev) => ev.lieu), dec.lieu]
    .forEach((l) => { l = (l || "").trim(); if (l && !vus.has(l.toLowerCase())) { vus.add(l.toLowerCase()); lieuxVie.push(l); } });
  // Unions : distinguer PACS / mariage / union libre, et les afficher TOUTES
  // (même logique que la fiche à l'écran) — pas seulement la première.
  const pacsDe = (u) => (u.evenements || []).find((x) => x && x.type === "EVEN" && (x.precision || "") === "PACS");
  const pacsFinDe = (u) => (u.evenements || []).find((x) => x && x.type === "EVEN" && (x.precision || "").startsWith("Dissolution de PACS"));
  const divorceDe = (u) => (u.evenements || []).find((x) => x && x.type === "DIV");
  const reperesUnions = [];
  (f.unions || []).forEach((u) => {
    if (!u.conjoint) return;
    const pac = pacsDe(u), pacFin = pacsFinDe(u), dv = divorceDe(u);
    const marie = u.mariage && (u.mariage.date || u.mariage.lieu);
    if (pac) reperesUnions.push(["PACS / union libre", u.conjoint.nom
      + (pac.date ? " · depuis " + pac.date : "")
      + (pacFin && pacFin.date ? " → dissous " + pacFin.date : " · en cours")]);
    if (marie || !pac) reperesUnions.push(["Union", u.conjoint.nom
      + (marie ? " · " + [u.mariage.date, u.mariage.lieu].filter(Boolean).join(" à ") : "")]);
    if (dv && (dv.date || dv.lieu)) reperesUnions.push(["Divorce",
      "d'avec " + u.conjoint.nom + " · " + [dv.date, dv.lieu].filter(Boolean).join(" à ")]);
  });
  sections.push('<section class="bloc"><h2>Repères de vie</h2>' + dl([
    ["Naissance", [nais.date, nais.lieu].filter(Boolean).join(" à ")],
    ...reperesUnions,
    ["Décès", [dec.date, dec.lieu].filter(Boolean).join(" à ") + (dec.cause ? " · cause : " + dec.cause : "")],
    ["Profession", prof], ["Lieux de vie", lieuxVie.join(" · ")],
  ]) + '</section>');

  // 4) Vie & chronologie
  const items = [];
  if (nais.date || nais.lieu) items.push({ an: modeleAnnee(nais.date), typ: "nais", lib: "Naissance", txt: [nais.date, nais.lieu].filter(Boolean).join(" à ") });
  (f.unions || []).forEach((u) => {
    const m = u.mariage || {}, nom = u.conjoint ? u.conjoint.nom : "", evs = u.evenements || [];
    if (m.date || m.lieu) items.push({ an: modeleAnnee(m.date), typ: "union", lib: "Mariage",
      txt: (nom ? "avec " + nom : "") + ((m.date || m.lieu) ? " — " + [m.date, m.lieu].filter(Boolean).join(" à ") : "") });
    evs.forEach((ev) => {
      const lib = ev.type === "DIV" ? "Divorce" : ev.type === "ENGA" ? "Fiançailles"
        : ev.type === "EVEN" ? (ev.precision || "Union") : (EVT_LABEL[ev.type] || ev.type);
      const pre = nom ? (ev.type === "DIV" ? "d'avec " + nom : "avec " + nom) : "";
      items.push({ an: modeleAnnee(ev.date), typ: "union", lib,
        txt: pre + ((ev.date || ev.lieu) ? (pre ? " — " : "") + [ev.date, ev.lieu].filter(Boolean).join(" à ") : "") });
    });
    if (nom && !(m.date || m.lieu) && !evs.length)
      items.push({ an: null, typ: "union", lib: "Union", txt: "avec " + nom });
  });
  (f.professions || []).forEach((p) => { if (p.valeur) items.push({ an: null, typ: "prof", lib: "Profession", txt: p.valeur }); });
  (f.residences || []).forEach((r) => { if (r.date || r.lieu) items.push({ an: modeleAnnee(r.date), typ: "resid", lib: "Résidence", txt: [r.date, r.lieu].filter(Boolean).join(" à ") }); });
  (f.evenements || []).forEach((ev) => items.push({ an: modeleAnnee(ev.date), typ: "evt", lib: EVT_LABEL[ev.type] || ev.type, txt: [ev.valeur, [ev.date, ev.lieu].filter(Boolean).join(" à ")].filter(Boolean).join(" — ") }));
  if (dec.date || dec.lieu) items.push({ an: modeleAnnee(dec.date), typ: "deces", lib: "Décès", txt: [dec.date, dec.lieu].filter(Boolean).join(" à ") });
  items.sort((a, b) => (a.an || 9999) - (b.an || 9999));
  const DOT = { nais: ["#3d7a54", "✳"], union: ["#c2681f", "⚭"], deces: ["#55606b", "✝"],
    resid: ["#2d6a6a", "⌂"], prof: ["#8a5a2a", "⚒"], evt: ["#7a7a7a", "◆"] };
  if (items.length) sections.push('<h2 class="grp">Vie &amp; chronologie</h2>'
    + '<section class="bloc"><h2>Chronologie</h2><ul class="chrono">'
    + items.map((it) => { const d = DOT[it.typ] || ["#7a7a7a", "•"];
      return '<li><span class="dot" style="background:' + d[0] + '">' + d[1] + '</span>'
        + '<div><span class="an">' + e(it.an ? String(it.an) : "—") + '</span><b>' + e(it.lib) + '</b>'
        + (it.txt ? " — " + e(it.txt) : "") + '</div></li>'; }).join("") + '</ul></section>');

  // 5) Famille
  const nomsListe = (arr) => (arr || []).map((p) => e(p.nom) + (p.periode ? " (" + e(p.periode) + ")" : "")).join(", ");
  let famHtml = dl([["Parents", nomsListe([...f.peres, ...f.meres])], ["Frères et sœurs", nomsListe(f.fratrie)]]);
  (f.unions || []).forEach((u) => {
    famHtml += '<div class="union"><b>Union' + (u.mariage && (u.mariage.date || u.mariage.lieu) ? " · " + e([u.mariage.date, u.mariage.lieu].filter(Boolean).join(" à ")) : "") + '</b> : '
      + (u.conjoint ? e(u.conjoint.nom) : "conjoint·e inconnu·e")
      + (u.enfants.length ? '<br><i>Enfants :</i> ' + nomsListe(u.enfants) : "") + '</div>';
  });
  sections.push('<h2 class="grp">Famille</h2>');
  sections.push('<section class="bloc"><h2>Parenté</h2>' + famHtml + '</section>');

  // 6) Sources & preuves
  let src = "";
  if (pv && pv.faits && pv.faits.length) {
    src += '<table class="preuves"><tr><th>Fait</th><th>Niveau de preuve</th><th>Sources</th></tr>'
      + pv.faits.map((ft) => '<tr><td>' + e(ft.libelle) + '</td><td>' + e(ft.niveau_texte || ft.niveau) + '</td><td>' + (ft.nb_sources || 0) + '</td></tr>').join("") + '</table>';
  }
  if ((f.sources_liees || []).length) {
    src += '<p><b>Sources rattachées :</b></p><ul>' + f.sources_liees.map((s) =>
      '<li>' + e(s.titre) + (s.type ? " — " + e(s.type) : "") + (s.date ? " (" + e(s.date) + ")" : "") + (s.role ? " · " + e(s.role) : "") + '</li>').join("") + '</ul>';
  }
  if (src) sections.push('<h2 class="grp">Sources &amp; preuves</h2>'
    + '<section class="bloc"><h2>Actes &amp; preuves rattachés</h2>' + src + '</section>');

  // 7-8) Recherche & notes
  const pistes = (f.pistes || []).map((p) => (typeof p === "string" ? { texte: p } : p)).filter((p) => p.texte);
  if (pistes.length || (f.note || "").trim()) sections.push('<h2 class="grp">Recherche &amp; notes</h2>');
  if (pistes.length) sections.push('<section class="bloc"><h2>Pistes de recherche</h2><ul>'
    + pistes.map((p) => '<li>' + (p.faite ? "☑ " : "☐ ") + e(p.texte) + '</li>').join("") + '</ul></section>');
  if ((f.note || "").trim()) sections.push('<section class="bloc"><h2>Note biographique</h2><p>' + e(f.note).replace(/\n/g, "<br>") + '</p></section>');

  // 9) Photos
  if ((f.medias || []).length) sections.push('<h2 class="grp">Photos</h2>'
    + '<section class="bloc"><h2>Portraits &amp; documents</h2><div class="photos">'
    + f.medias.map((m) => '<figure><img src="' + org + '/media/Photos/' + encodeURIComponent(m.fichier) + '"><figcaption>' + e(m.titre || "") + '</figcaption></figure>').join("") + '</div></section>');

  const css = "@page{size:A4;margin:13mm 12mm}"
    + "*{box-sizing:border-box}"
    + "body{font-family:'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif;"
    + "color:#2b2b2b;font-size:10.8pt;line-height:1.5;-webkit-print-color-adjust:exact;print-color-adjust:exact}"
    + "h1{font-size:21pt;color:#1f2d28;margin:0;font-weight:700;letter-spacing:-.01em}"
    + ".sub{color:#6b6b6b;font-size:10.5pt;margin-top:3px}"
    + ".rel{display:inline-block;margin-top:8px;background:#fbe9d6;color:#b5651d;"
    + "border-radius:20px;padding:3px 12px;font-size:9.8pt;font-weight:600}"
    + ".tete{display:flex;gap:16px;align-items:center;padding:2px 2px 15px;margin-bottom:4px;border-bottom:1px solid #eae5d8}"
    + ".portrait{width:78px;height:78px;object-fit:cover;border-radius:50%;border:2px solid #e6e2d6;flex:none}"
    + ".mono{width:78px;height:78px;border-radius:50%;display:flex;align-items:center;justify-content:center;"
    + "font-size:30pt;font-weight:700;color:#fff;flex:none}"
    + ".mono-M{background:#3b6ea5}.mono-F{background:#9c4f86}.mono-N{background:#2d5c47}"
    + ".mono-X{background:#2d5c47}.mono-U{background:#8a8577}"
    + ".badges{margin-top:9px;display:flex;flex-wrap:wrap;gap:5px}"
    + ".badges span{background:#f2efe6;border:1px solid #e4dfd1;border-radius:20px;padding:2px 10px;font-size:9pt;color:#514f47}"
    + ".grp{font-size:13pt;color:#c2681f;font-weight:700;margin:20px 0 2px;padding-bottom:4px;"
    + "border-bottom:2px solid #e0a668;page-break-after:avoid}"
    + ".bloc{background:#fff;border:1px solid #e7e3d7;border-radius:12px;padding:13px 16px;margin:9px 0;"
    + "page-break-inside:avoid;box-shadow:0 1px 2px rgba(60,50,30,.05)}"
    + ".bloc h2{font-size:11.5pt;color:#1f4636;font-weight:700;margin:0 0 9px;border:0;page-break-after:avoid}"
    + "dl{display:grid;grid-template-columns:158px 1fr;gap:6px 12px;margin:0}"
    + "dt{color:#8a857a;font-size:8.6pt;text-transform:uppercase;letter-spacing:.04em;font-weight:600;align-self:start;padding-top:1px}"
    + "dd{margin:0}"
    + ".union{margin:7px 0}"
    + "ul.chrono{list-style:none;padding:0;margin:2px 0 0}"
    + "ul.chrono li{display:flex;align-items:flex-start;gap:10px;padding:5px 0}"
    + "ul.chrono li+li{border-top:1px solid #f0ece1}"
    + ".dot{flex:none;width:22px;height:22px;border-radius:50%;color:#fff;display:flex;"
    + "align-items:center;justify-content:center;font-size:10.5pt;margin-top:1px}"
    + ".an{font-weight:700;color:#c2681f;margin-right:6px}.chrono b{color:#25302b}"
    + "table.preuves{border-collapse:collapse;width:100%;font-size:10pt;margin-top:2px}"
    + "table.preuves th,table.preuves td{border:1px solid #e4dfd1;padding:5px 9px;text-align:left}"
    + "table.preuves th{background:#f3efe6;color:#4a4a44;font-size:9pt;text-transform:uppercase;letter-spacing:.03em}"
    + ".photos{display:flex;flex-wrap:wrap;gap:10px}.photos figure{margin:0;text-align:center}"
    + ".photos img{width:130px;height:130px;object-fit:cover;border-radius:8px;border:1px solid #e0dccf}"
    + ".photos figcaption{font-size:8.6pt;color:#7a7568;margin-top:3px}"
    + "ul{margin:4px 0;padding-left:18px}"
    + "footer{margin-top:22px;color:#a29b8c;font-size:8.4pt;border-top:1px solid #e7e3d7;padding-top:7px}";
  const doc = "<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>"
    + e(f.nom_complet) + " — Arboriane</title><style>" + css + "</style></head><body>"
    + sections.join("")
    + "<footer>Fiche générée avec Arboriane · " + e(f.nom_complet) + "</footer>"
    + "<script>window.onload=function(){setTimeout(function(){window.print()},250)}<\/script></body></html>";
  const w = window.open("", "_blank");
  if (!w) { toast("Autorisez les fenêtres pop-up pour imprimer."); return; }
  w.document.write(doc); w.document.close();
}
