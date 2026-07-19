// Personnes — sections de la fiche : chronologie, pistes, documents,
// sources/preuves, photos.
import { h, vider, actionnable } from "../../noyau/dom.js";
import { aller } from "../../noyau/etat.js";
import { apiGet, apiJson } from "../../noyau/api.js";
import { badge } from "../../composants/badge.js";
import { toast } from "../../composants/toast.js";
import { confirmer } from "../../composants/modale.js";
import { libelleEvt, modeleAnnee, lireBase64, initiale } from "./commun.js";
import { ouvrirVisionneuse } from "../../composants/visionneuse.js";
import { ouvrirCadreur } from "../../composants/cadreur.js";
import { formatNonAffichable, MSG_FORMAT_NON_AFFICHABLE } from "../../composants/media.js";

// Section « Vie & chronologie » — professions, résidences, événements triés.
// icône + couleur par type d'événement (pour la frise chronologique)
const EVT_ICO = {
  Naissance: ["✳️", "nais"], Baptême: ["💧", "nais"], Communion: ["✝", "reli"],
  Confirmation: ["✝", "reli"], Mariage: ["💍", "union"], Divorce: ["💔", "union"],
  PACS: ["🤝", "union"], "Dissolution de PACS": ["🤝", "union"],
  Décès: ["✝️", "dec"],
  Inhumation: ["⚰️", "dec"], Crémation: ["🔥", "dec"], Profession: ["🛠", "prof"],
  Résidence: ["🏠", "resi"], Recensement: ["📋", "resi"], Retraite: ["🏖", "prof"],
  Religion: ["⛪", "reli"], Titre: ["🎖", "reli"], Signalement: ["📏", "evt"],
  Éducation: ["🎓", "evt"], Nationalité: ["🏳", "evt"], Diplôme: ["🎓", "evt"],
  Émigration: ["🚢", "evt"], Immigration: ["🚢", "evt"], Naturalisation: ["📜", "evt"],
};
function iconeEvt(lib) { return EVT_ICO[lib] || ["•", "evt"]; }
// niveau de preuve + source d'un fait (naissance/décès/union) d'après ses
// citations. srcMap : { id_source: titre } (issu de f.sources_liees).
function preuveDe(o, srcMap) {
  const c = (o && o.citations) || [];
  if (!c.length) return null;
  const niveau = Math.max(...c.map((x) => +x.quay || 0)) >= 3 ? "acte" : "source";
  const cit = c.find((x) => x.source) || {};
  return { niveau, sid: cit.source || null, titre: cit.source ? (srcMap[cit.source] || null) : null };
}

// « 12 mars 1902 » ou « 12 mars 1902 à 14:30 » quand l'heure est renseignée.
function dateHeure(ev) {
  const d = ev.date || "";
  return d && ev.heure ? d + " à " + ev.heure : d;
}

export function sectionChronologie(f) {
  const items = [];
  const srcMap = {};
  (f.sources_liees || []).forEach((s) => { srcMap[s.id] = s.titre; });
  const nais = f.naissance || {}, dec = f.deces || {};
  if (nais.date || nais.lieu)
    items.push({ an: modeleAnnee(nais.date), lib: "Naissance", fait: "naissance",
      txt: [dateHeure(nais), nais.lieu].filter(Boolean).join(" à "), preuve: preuveDe(nais, srcMap) });
  (f.unions || []).forEach((u) => {
    // Fiançailles : fait du COUPLE (fam.evenements, balise GEDCOM ENGA), prouvable.
    const fii = (u.evenements || []).findIndex((e) => e && e.type === "ENGA");
    const fi = fii >= 0 ? u.evenements[fii] : null;
    if (fi && (fi.date || fi.lieu))
      items.push({ an: modeleAnnee(fi.date), lib: "Fiançailles",
        fait: "union_evenement:" + fii, famille: u.famille,
        txt: (u.conjoint ? "avec " + u.conjoint.nom : "")
          + " — " + [fi.date, fi.lieu].filter(Boolean).join(" à "),
        preuve: preuveDe(fi, srcMap) });
    const m = u.mariage || {};
    // « Mariage » seulement s'il y a vraiment un mariage (date/lieu). Sinon, si le
    // couple n'a AUCUN événement (ni PACS, ni fiançailles…), on montre une « Union »
    // simple ; un couple pacsé est déjà représenté par sa ligne PACS → pas de doublon.
    const aEvtCouple = (u.evenements || []).some(
      (e) => e && (e.type === "EVEN" || e.type === "ENGA" || e.type === "DIV"));
    if (m.date || m.lieu)
      items.push({ an: modeleAnnee(m.date), lib: "Mariage", fait: "union", famille: u.famille,
        txt: (u.conjoint ? "avec " + u.conjoint.nom : "")
          + " — " + [m.date, m.lieu].filter(Boolean).join(" à "),
        preuve: preuveDe(m, srcMap) });
    else if (u.conjoint && !aEvtCouple)
      items.push({ an: null, lib: "Union", fait: "union", famille: u.famille,
        txt: "avec " + u.conjoint.nom, preuve: preuveDe(m, srcMap) });
    // Divorce : fait du COUPLE (fam.evenements, balise GEDCOM DIV). Prouvable
    // comme le mariage — on cible « union_evenement:<index dans fam.evenements> ».
    const dvi = (u.evenements || []).findIndex((e) => e && e.type === "DIV");
    const dv = dvi >= 0 ? u.evenements[dvi] : null;
    if (dv && (dv.date || dv.lieu))
      items.push({ an: modeleAnnee(dv.date), lib: "Divorce",
        fait: "union_evenement:" + dvi, famille: u.famille,
        txt: (u.conjoint ? "d'avec " + u.conjoint.nom : "")
          + " — " + [dv.date, dv.lieu].filter(Boolean).join(" à "),
        preuve: preuveDe(dv, srcMap) });
    // PACS / union libre (et sa dissolution) : événements de couple « EVEN » typés,
    // prouvables comme le mariage.
    (u.evenements || []).forEach((e, i) => {
      if (!e || e.type !== "EVEN" || !(e.date || e.lieu)) return;
      const lib = e.precision || "Événement du couple";
      items.push({ an: modeleAnnee(e.date), lib, fait: "union_evenement:" + i, famille: u.famille,
        txt: (u.conjoint ? "avec " + u.conjoint.nom : "")
          + " — " + [e.date, e.lieu].filter(Boolean).join(" à "),
        preuve: preuveDe(e, srcMap) });
    });
  });
  // Faits secondaires : index DANS le tableau (pas l'ordre trié) = cible de preuve.
  (f.professions || []).forEach((p, i) => {
    if (p.valeur) items.push({ an: modeleAnnee(p.date), lib: "Profession",
      fait: "profession:" + i, txt: p.valeur, preuve: preuveDe(p, srcMap) });
  });
  (f.residences || []).forEach((r, i) => {
    if (r.date || r.lieu) items.push({ an: modeleAnnee(r.date), lib: "Résidence",
      fait: "residence:" + i, txt: [r.date, r.lieu].filter(Boolean).join(" à "),
      preuve: preuveDe(r, srcMap) });
  });
  (f.evenements || []).forEach((e, i) => {
    const lib = libelleEvt(e);   // « Affectation », « PACS »… plutôt que « Autre événement »
    items.push({ an: modeleAnnee(e.date), lib, fait: "evenement:" + i,
      txt: [e.valeur, [e.date, e.lieu].filter(Boolean).join(" à ")].filter(Boolean).join(" — "),
      preuve: preuveDe(e, srcMap) });
  });
  if (dec.date || dec.lieu)
    items.push({ an: modeleAnnee(dec.date), lib: "Décès", fait: "deces",
      txt: (f.age != null ? "à " + f.age + " ans — " : "") + [dateHeure(dec), dec.lieu].filter(Boolean).join(" à "),
      preuve: preuveDe(dec, srcMap) });
  if (!items.length) return null;
  items.sort((a, b) => (a.an || 9999) - (b.an || 9999));

  const carte = h("div", { class: "carte" }, h("h2", {}, "Vie & chronologie"));
  const frise = h("div", { class: "timeline" });
  // Proches suggérés comme « personnes concernées » d'une preuve : un acte de
  // naissance/décès cite souvent les parents → on les propose pré-remplis.
  const parents = [...(f.peres || []).map((p) => ({ id: p.id, role: "père" })),
                   ...(f.meres || []).map((m) => ({ id: m.id, role: "mère" }))];
  const prochesPour = (fait) => (fait === "naissance" || fait === "deces") ? parents : [];
  items.forEach((it) => {
    const [ico, cls] = iconeEvt(it.lib);
    const pr = it.preuve;
    const badgePreuve = pr
      ? actionnable(h("span", { class: "badge " + (pr.niveau === "acte" ? "ok" : "info")
          + (pr.sid ? " cliquable" : ""), title: pr.sid ? "Ouvrir la source" : "",
          style: pr.sid ? "cursor:pointer" : "",
          onclick: pr.sid ? () => aller("actes", { source: pr.sid }) : null },
          (pr.niveau === "acte" ? "Prouvé par acte" : "Source")))
      : null;
    const btnSource = it.fait
      ? h("button", { class: "lien pousse", style: "font-size:12px;white-space:nowrap",
          title: "Attacher une source à ce fait",
          onclick: () => prouver(f.id, it.fait, it.lib, f.nom_complet,
            { famille: it.famille, proches: prochesPour(it.fait) }) }, "Prouver")
      : null;
    frise.append(h("div", { class: "tl-item" },
      h("div", { class: "tl-ico tl-" + cls }, ico),
      h("div", { class: "tl-corps" },
        h("div", { class: "tl-tete" },
          h("span", { class: "tl-an" }, it.an ? String(it.an) : "—"),
          h("strong", {}, it.lib),
          badgePreuve,
          btnSource),
        it.txt ? h("div", { class: "tl-detail" }, it.txt) : null,
        pr && pr.titre ? actionnable(h("div", { class: "tl-source",
          onclick: () => aller("actes", { source: pr.sid }) }, "📄 " + pr.titre)) : null)));
  });
  carte.append(frise);
  return carte;
}

// Section « Pistes de recherche » — tâches cochables par personne (parité
// avec les annotations de l'ancienne version). Sauvegarde à chaque changement.
export function sectionPistes(f, pid) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "Pistes de recherche"));
  // normalise : accepte les anciennes pistes en simple chaîne
  let pistes = (f.pistes || []).map((p) =>
    (typeof p === "string" ? { texte: p, faite: false } : { texte: p.texte || "", faite: !!p.faite }));

  async function sauver() {
    f.pistes = pistes;
    try { await apiJson("/api/individus/" + pid, "PUT", { pistes }); }
    catch (e) { toast(e.message, { type: "erreur" }); }
  }

  const liste = h("div", {});
  function rendre() {
    vider(liste);
    if (!pistes.length) {
      liste.append(h("div", { class: "vide compacte" },
        "Aucune piste. Notez ce qu'il reste à chercher sur cette personne."));
    }
    pistes.forEach((p, i) => {
      const chk = h("input", { type: "checkbox", checked: p.faite ? "checked" : null });
      chk.addEventListener("change", () => { pistes[i].faite = chk.checked; sauver(); rendre(); });
      liste.append(h("div", { class: "rangee", style: "padding:4px 0" },
        chk,
        h("span", { style: "flex:1" + (p.faite ? ";text-decoration:line-through;color:var(--gris-clair)" : "") }, p.texte),
        h("button", { class: "lien danger", style: "font-size:12px",
          onclick: () => { pistes.splice(i, 1); sauver(); rendre(); } }, "retirer")));
    });
  }
  rendre();

  const inp = h("input", { placeholder: "Nouvelle piste (acte à retrouver, hypothèse…)", style: "flex:1;min-width:200px" });
  const ajouter = () => {
    const t = inp.value.trim();
    if (!t) return;
    pistes.push({ texte: t, faite: false }); inp.value = ""; sauver(); rendre();
  };
  inp.addEventListener("keydown", (e) => { if (e.key === "Enter") ajouter(); });
  carte.append(liste, h("div", { class: "barre-actions", style: "margin-top:10px" },
    inp, h("button", { class: "bouton secondaire petit", onclick: ajouter }, "➕ Ajouter")));
  return carte;
}

// Section « Documents & sources » — sources rattachées à la personne.
export function sectionDocuments(f) {
  const srcs = f.sources_liees || [];
  const carte = h("div", { class: "carte" },
    h("div", { class: "rangee" },
      h("h2", { style: "margin:0" }, "Sources rattachées ", badge(String(srcs.length))),
      h("button", { class: "bouton secondaire petit pousse",
        onclick: () => aller("actes") }, "Toutes les sources →")));
  if (!srcs.length) {
    carte.append(h("div", { class: "vide compacte" },
      "Aucune source rattachée. Ouvrez une source dans « Actes / Sources » pour la relier, "
      + "ou prouvez un fait ci-dessous."));
    return carte;
  }
  const grille = h("div", { class: "grille-cartes", style: "margin-top:10px" });
  srcs.forEach((s) => {
    const vign = s.apercu
      ? h("img", { src: "/media/Sources/" + encodeURIComponent(s.apercu),
          style: "width:100%;height:90px;object-fit:cover;border-radius:6px 6px 0 0" })
      : h("div", { style: "height:90px;display:flex;align-items:center;justify-content:center;"
          + "background:var(--sauge-pale);border-radius:6px 6px 0 0;font-size:26px" }, "📄");
    grille.append(actionnable(h("div", { style: "border:1px solid var(--bord);border-radius:8px;"
      + "overflow:hidden;cursor:pointer", onclick: () => aller("actes", { source: s.id }) },
      vign,
      h("div", { style: "padding:6px 8px" },
        h("div", { style: "font-size:12.5px;font-weight:600;line-height:1.25" }, s.titre),
        h("div", { style: "font-size:11px;color:var(--gris);margin-top:2px" },
          [s.type, s.date].filter(Boolean).join(" · ") || "—"),
        h("div", { style: "font-size:11px;margin-top:3px" },
          badge(s.role, s.sujet ? "info" : ""))))));
  });
  carte.append(grille);
  return carte;
}

const NIVEAU_BADGE = {
  acte: ["Prouvé par acte", "ok"], declare: ["Déclaré", "info"],
  estime: ["Estimé", "attention"], non_qualifie: ["Source non qualifiée", "attention"],
  manquant: ["À prouver", "attention"],
};

// Fiabilité (QUAY 0-3) → libellé court, pour le détail d'une citation.
const QUAY_LIB = { 3: "prouvé par acte", 2: "déclaré", 1: "estimé", 0: "estimé" };

export async function sectionPreuves(pid) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "Preuves par fait"));
  const corps = h("div", {});
  carte.append(corps);
  await rendrePreuves(corps, pid);
  return carte;
}

// Corps de la table, re-rendu après chaque retrait (les index de citations
// changent : on repart TOUJOURS de l'état serveur, jamais d'un index périmé).
async function rendrePreuves(corps, pid) {
  vider(corps);
  const pv = await apiGet("/api/individus/" + pid + "/preuves").catch(() => null);
  if (!pv) { corps.append(h("div", { class: "vide compacte" }, "—")); return; }
  corps.append(h("p", { class: "sous-titre" },
    pv.prouves + " fait(s) sur " + pv.total + " prouvé(s) par acte. "
    + "« Prouver » relie une source à chaque fait ; le nombre de sources se "
    + "déplie pour voir ou retirer chaque preuve."));
  // Tableau léger à colonnes (Fait · Date · Preuve · action) : la date a sa
  // propre colonne — plus de libellé sur deux lignes.
  const tbody = h("tbody", {});
  pv.faits.forEach((f) => {
    const [lib, genre] = NIVEAU_BADGE[f.niveau] || ["?", ""];
    const cits = f.citations || [];
    // ligne de détail (repliée par défaut) : chaque citation, retirable
    let detail = null, btnDeplier = null;
    if (cits.length) {
      const liste = h("div", { style: "padding:2px 0 6px" });
      cits.forEach((c, i) => liste.append(ligneCitation(corps, pid, f, c, i)));
      detail = h("tr", {}, h("td", { colspan: "4", style: "padding:0 10px" }, liste));
      detail.style.display = "none";
      btnDeplier = h("button", { class: "lien", style: "font-size:12px",
        "aria-expanded": "false", title: "Voir / retirer les preuves attachées",
        onclick: () => {
          const ouvert = detail.style.display !== "none";
          detail.style.display = ouvert ? "none" : "";
          btnDeplier.textContent = (ouvert ? "▸ " : "▾ ") + cits.length + " source(s)";
          btnDeplier.setAttribute("aria-expanded", String(!ouvert));
        } }, "▸ " + cits.length + " source(s)");
    }
    tbody.append(h("tr", {},
      h("td", { class: "fait" }, f.libelle),
      h("td", { class: "date" }, f.date || "—"),
      h("td", { class: "preuve" },
        h("span", { class: "rangee serre" }, badge(lib, genre), btnDeplier)),
      h("td", { class: "action" },
        h("button", { class: "bouton secondaire petit pousse",
          onclick: () => prouver(pid, f.fait, f.libelle, "", { famille: f.famille }) }, "Prouver"))));
    if (detail) tbody.append(detail);
  });
  corps.append(h("table", { class: "preuves" },
    h("thead", {}, h("tr", {},
      h("th", {}, "Fait"), h("th", {}, "Date"), h("th", { class: "preuve" }, "Preuve"),
      h("th", { class: "tete-action" }, "Action"))),
    tbody));
}

// Une citation dépliée : titre de source (cliquable), page, fiabilité,
// et « retirer cette preuve » (avec confirmation — la source, elle, reste).
function ligneCitation(corps, pid, f, c, i) {
  return h("div", { class: "rangee", style: "gap:8px;padding:3px 0;flex-wrap:wrap" },
    actionnable(h("span", { class: "lien", style: c.source ? "cursor:pointer" : "",
      title: c.source ? "Ouvrir la source" : "",
      onclick: c.source ? () => aller("actes", { source: c.source }) : null },
      "📄 " + (c.titre || "(source)"))),
    c.page ? h("span", { style: "color:var(--gris);font-size:12.5px" }, c.page) : null,
    c.quay != null
      ? badge(QUAY_LIB[c.quay] || ("fiabilité " + c.quay), c.quay >= 3 ? "ok" : "info")
      : null,
    h("button", { class: "lien danger", style: "font-size:12px;margin-left:auto",
      onclick: async () => {
        if (!await confirmer("Retirer cette preuve du fait « " + f.libelle + " » ? "
          + "La source elle-même n'est pas supprimée : seul le lien avec ce fait est défait.",
          { titre: "Retirer la preuve", valider: "Retirer", danger: true })) return;
        try {
          await apiJson("/api/individus/" + pid + "/retirer-citation", "POST",
            { fait: f.fait, index: i, famille: f.famille || "" });
          toast("Preuve retirée. La source reste dans « Actes / Sources ».");
          await rendrePreuves(corps, pid);
        } catch (e) { toast(e.message, { type: "erreur" }); }
      } }, "retirer cette preuve"));
}

// Prouver un fait = ouvrir LE formulaire de source détaillé (le même qu'Actes /
// Sources), en mode « preuve » : source existante ou nouvelle, avec pièces
// jointes, qui se relie au fait. Un « ← Retour à la fiche » ramène à la personne.
async function prouver(pid, fait, libelle, nom, extra = {}) {
  const { formulaire } = await import("../actes.js");
  formulaire(null, {
    preuve: { pid, fait, libelle, nom, famille: extra.famille || "", proches: extra.proches || [] },
    retour: { label: "Retour à la fiche" + (nom ? " de " + nom : ""),
      // rouvrir sur « Sources & preuves » (là où on était) pour enchaîner les preuves
      action: () => aller("personnes", { fiche: pid, onglet: "sources" }) },
  });
}

const CARNET_LIB = { seance: "Séance", piste: "Piste", trouvaille: "Trouvaille",
  reflexion: "Réflexion", afaire: "À faire", ia: "IA" };
const CARNET_GENRE = { piste: "info", trouvaille: "ok", afaire: "attention" };

// Section « Mentions du carnet » — les notes du carnet de bord qui taguent cette
// personne (pistes, trouvailles, réflexions…). Fait le pont carnet ↔ fiche : une
// trouvaille notée depuis le carnet apparaît ici.
export async function sectionCarnet(pid) {
  const r = await apiGet("/api/carnet/personne/" + pid).catch(() => ({ entrees: [] }));
  const lst = r.entrees || [];
  if (!lst.length) return null;
  const carte = h("div", { class: "carte" }, h("h2", {}, "Mentions du carnet"));
  lst.forEach((e) => {
    const estPiste = e.type === "piste" || e.type === "afaire";
    carte.append(h("div", { style: "padding:8px 0;border-bottom:1px solid var(--bord)" },
      h("div", { class: "rangee serre", style: "flex-wrap:wrap" },
        badge(CARNET_LIB[e.type] || e.type, CARNET_GENRE[e.type] || ""),
        (estPiste && e.statut === "fait") ? badge("✓ fait", "ok") : null,
        h("strong", {}, e.titre || "(sans titre)"),
        h("span", { style: "color:var(--gris-clair);font-size:12px" }, e.date)),
      e.texte ? h("p", { style: "margin:6px 0 0;white-space:pre-wrap" }, e.texte) : null));
  });
  carte.append(h("button", { class: "lien", style: "font-size:12px;margin-top:8px",
    onclick: () => aller("carnet") }, "Ouvrir le carnet →"));
  return carte;
}

export function sectionPhotos(pid, f) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "Photos"));
  const galerie = h("div", { class: "galerie-photos" });
  const urls = () => (f.medias || []).map((m) => "/media/Photos/" + encodeURIComponent(m.fichier));
  // sauvegarde SANS recharger toute la fiche : on reste sur l'onglet Photos.
  const sauver = (msg) => apiJson("/api/individus/" + pid + "/medias", "PUT", { medias: f.medias })
    .then(() => { if (msg) toast(msg); });

  // Le portrait de l'en-tête (construit une seule fois par vueFiche) ne « voit »
  // pas les mutations de f.medias faites ici : on le resynchronise à la volée
  // pour que définir/cadrer/retirer un portrait s'affiche sans recharger la fiche.
  function majPortrait() {
    const el = document.querySelector(".fiche-tete > .portrait");
    if (!el) return;
    const princ = (f.medias || []).find((m) => m.principale) || (f.medias || [])[0];
    if (princ) {
      el.textContent = "";
      el.style.backgroundImage = "url('/media/Photos/" + encodeURIComponent(princ.fichier) + "')";
      el.style.backgroundSize = "cover";
      el.style.backgroundPosition = princ.cadrage || "center";
    } else {
      el.style.backgroundImage = el.style.backgroundSize = el.style.backgroundPosition = "";
      el.textContent = initiale(f.nom_complet);
    }
  }

  function rendre() {
    majPortrait();
    vider(galerie);
    const medias = f.medias || [];
    if (!medias.length) { galerie.append(h("div", { class: "vide compacte" }, "Aucune photo.")); return; }
    medias.forEach((m, i) => {
      const url = "/media/Photos/" + encodeURIComponent(m.fichier);
      const vign = h("img", { class: "photo-vign" + (m.principale ? " principale" : ""), src: url,
        title: "Cliquer pour agrandir", loading: "lazy",
        style: "object-position:" + (m.cadrage || "center"),   // cadrage carré non destructif
        onclick: () => ouvrirVisionneuse(urls(), { index: i, titre: m.titre || f.nom_complet || "" }) });
      const legende = h("input", { class: "photo-legende", placeholder: "Légende…", value: m.titre || "" });
      legende.addEventListener("change", () => { m.titre = legende.value.trim(); sauver("Légende enregistrée."); });
      const gauche = i > 0 ? h("button", { class: "lien", title: "Déplacer avant",
        onclick: () => { [medias[i - 1], medias[i]] = [medias[i], medias[i - 1]]; sauver(); rendre(); } }, "◀") : null;
      const droite = i < medias.length - 1 ? h("button", { class: "lien", title: "Déplacer après",
        onclick: () => { [medias[i + 1], medias[i]] = [medias[i], medias[i + 1]]; sauver(); rendre(); } }, "▶") : null;
      const portrait = m.principale
        ? h("span", { class: "badge ok", style: "font-size:11px" }, "★ portrait")
        : h("button", { class: "lien", title: "Utiliser comme portrait",
            onclick: () => { medias.forEach((x, k) => x.principale = k === i); sauver("Portrait défini."); rendre(); } }, "portrait");
      const cadrer = h("button", { class: "lien", title: "Cadrer (choisir la partie visible)",
        onclick: async () => {
          const c = await ouvrirCadreur(url, m.cadrage);
          if (c) { m.cadrage = c; sauver("Cadrage enregistré."); rendre(); }
        } }, "cadrer");
      const dl = h("a", { class: "lien", href: url, download: m.fichier, title: "Télécharger" }, "⬇");
      const retirer = h("button", { class: "lien danger", title: "Retirer", onclick: async () => {
        if (!await confirmer("Retirer cette photo de la fiche ? (le fichier reste dans le dossier)",
          { titre: "Retirer la photo", valider: "Retirer" })) return;
        medias.splice(i, 1);
        if (medias.length && !medias.some((x) => x.principale)) medias[0].principale = true;
        sauver("Photo retirée."); rendre(); } }, "retirer");
      galerie.append(h("div", { class: "photo-carte" }, vign, legende,
        h("div", { class: "photo-barre" }, gauche, portrait, cadrer, dl, retirer, droite)));
    });
  }
  rendre();

  const input = h("input", { type: "file", multiple: true, style: "display:none",
    accept: "image/jpeg,image/png,image/gif,image/webp,image/avif" });
  input.addEventListener("change", async () => {
    const fichiers = [...input.files];
    const refuses = fichiers.filter((x) => formatNonAffichable(x.name));
    const ok = fichiers.filter((x) => !formatNonAffichable(x.name));
    if (refuses.length) toast(MSG_FORMAT_NON_AFFICHABLE);
    if (!ok.length) return;
    for (const fichier of ok) {
      const data = await lireBase64(fichier);
      const r = await apiJson("/api/media/Photos", "POST", { nom: fichier.name, data });
      f.medias = (f.medias || []).concat([{ fichier: r.fichier, titre: "", principale: !(f.medias || []).length }]);
    }
    await sauver(ok.length + " photo(s) ajoutée(s)."); rendre();
  });
  carte.append(galerie, h("div", { class: "barre-actions", style: "margin-top:12px" },
    h("button", { class: "bouton secondaire petit", onclick: () => input.click() },
      "🖼 Ajouter des photos"), input));
  return carte;
}
