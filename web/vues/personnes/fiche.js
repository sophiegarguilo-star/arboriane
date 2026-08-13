// Personnes — fiche d'une personne : en-tête, onglets (synthèse, chronologie,
// famille, sources, recherche web, photos, GEDCOM), ajout rapide de proches.
import { h, vider } from "../../noyau/dom.js";
import { aller, retour, peutRevenir } from "../../noyau/etat.js";
import { apiGet, apiJson } from "../../noyau/api.js";
import { badge, pastilleSexe } from "../../composants/badge.js";
import { toast } from "../../composants/toast.js";
import { confirmer, choix, ouvrirModale, fermerModale } from "../../composants/modale.js";
import { champPersonne } from "../../composants/champ.js";
import { noterRecent } from "../../noyau/recents.js";
import { blocLiensWeb } from "../../composants/liensWeb.js";
import { RESN_LABEL, TYPE_NOM_LABEL, majuscule, brancheDeSosa,
         initiale, ligneDef } from "./commun.js";
import { imprimerFiche } from "./impression.js";
import { sectionChronologie, sectionPistes, sectionDocuments, sectionPreuves,
         ongletCarnet, sectionPhotos } from "./fiche_sections.js";

// Ajout d'un proche : on ouvre le FORMULAIRE COMPLET unifié (« Nouvelle
// personne ») avec un lien de parenté pré-rempli. `type` ∈ pere | mere |
// conjoint | enfant | fratrie ; `fid` (facultatif) cible une union précise.
function ajoutRelatif(pid, type, nom, fid) {
  aller("personnes", { creer: true,
    lien: { type, ancre: pid, ancreNom: nom, famille: fid || null } });
}

// Petite modale « choisir une personne existante » : renvoie l'id choisi, ou
// null (Annuler / Échap / fond). Résolution unique (motif des modales du projet).
async function choisirPersonne({ titre = "Choisir une personne", exclureId = null } = {}) {
  let liste = [];
  try { liste = await apiGet("/api/individus"); } catch { liste = []; }
  if (exclureId) liste = liste.filter((p) => p.id !== exclureId);
  return new Promise((resolve) => {
    let regle = false;
    const fond = document.getElementById("modale-fond");
    const surFond = (e) => { if (e.target === fond) finir(null); };
    const surTouche = (e) => { if (e.key === "Escape") finir(null); };
    const finir = (val) => {
      if (regle) return;
      regle = true;
      fond.removeEventListener("click", surFond);
      document.removeEventListener("keydown", surTouche);
      fermerModale();
      resolve(val);
    };
    const champ = champPersonne(liste, { placeholder: "Rechercher la personne…" });
    const valider = () => {
      const id = champ.valeur();
      if (!id) { toast("Choisissez d'abord une personne."); return; }
      finir(id);
    };
    const corps = h("div", {},
      champ.element,
      h("div", { class: "barre-actions", style: "justify-content:flex-end;margin-top:16px" },
        h("button", { class: "bouton secondaire", onclick: () => finir(null) }, "Annuler"),
        h("button", { class: "bouton", onclick: valider }, "Valider")));
    ouvrirModale(corps, { titre });
    // Fermeture par clic sur le fond ou Échap = annulation (résout null).
    fond.addEventListener("click", surFond);
    document.addEventListener("keydown", surTouche);
  });
}

// Recharge l'onglet Famille de la fiche après une mutation réussie (re-rend via
// le routeur, qui reconstruit proprement la vue sur le bon onglet).
function rechargerFamille(pid) {
  aller("personnes", { fiche: pid, onglet: "famille" }, true);
}

// Menu « Cet enfant… » : corriger sa mère / son père (ancré sur l'enfant, l'autre
// parent est conservé — cas des deux sœurs) ou le détacher du couple. `pid` = la
// personne dont on affiche la fiche (pour recharger l'onglet Famille).
async function menuEnfant(pid, enfant) {
  const action = await choix(enfant.nom, [
    { cle: "mere", texte: "Changer sa mère", secondaire: true },
    { cle: "pere", texte: "Changer son père", secondaire: true },
    { cle: "detacher", texte: "Détacher de ce couple", danger: true },
  ], { titre: "Cet enfant…" });
  if (!action) return;
  try {
    if (action === "detacher") {
      if (!await confirmer("Détacher « " + enfant.nom + " » de ce couple ?"
        + " (l'enfant reste dans l'arbre, sans parents rattachés)",
        { titre: "Détacher l'enfant", danger: true, valider: "Détacher" })) return;
      await apiJson("/api/individus/" + enfant.id + "/deplacer", "POST", { famille: "" });
      toast("Enfant détaché.");
    } else {
      const titre = action === "mere" ? "Nouvelle mère" : "Nouveau père";
      const id = await choisirPersonne({ titre, exclureId: enfant.id });
      if (!id) return;
      await apiJson("/api/individus/" + enfant.id + "/parent", "POST",
        { role: action, id });
      toast(action === "mere" ? "Mère corrigée." : "Père corrigé.");
    }
    rechargerFamille(pid);
  } catch (e) { toast(e.message || "Modification impossible."); }
}

// Le divorce (et les autres faits du couple) vit dans fam.evenements, type GEDCOM « DIV ».
export function divorceDe(u) {
  return ((u && u.evenements) || []).find((e) => e && e.type === "DIV") || null;
}

// PACS / union libre : événement de couple sans balise GEDCOM standard — stocké
// en « EVEN » typé (precision « PACS » pour le début, « Dissolution de PACS »
// pour la fin). Interopérable : exporté en `1 EVEN / 2 TYPE PACS`.
export function pacsDe(u) {
  return ((u && u.evenements) || []).find(
    (e) => e && e.type === "EVEN" && (e.precision || "") === "PACS") || null;
}
export function pacsFinDe(u) {
  return ((u && u.evenements) || []).find(
    (e) => e && e.type === "EVEN" && (e.precision || "").startsWith("Dissolution de PACS")) || null;
}
function estPacs(e) {
  return e && e.type === "EVEN"
    && ((e.precision || "") === "PACS" || (e.precision || "").startsWith("Dissolution de PACS"));
}

// Édition d'une union : date + lieu du mariage, et divorce. Écran plein, avec
// « ← Retour à la fiche » (motif unifié). Les preuves du mariage sont préservées
// côté serveur : on n'envoie que date/lieu.
async function modifierUnion(pid, u, nom) {
  const vue = document.getElementById("vue");
  const { champDate } = await import("../../composants/champDate.js");
  const { champLieu, chargerLieux } = await import("../../composants/champLieu.js");
  const lieux = await chargerLieux(apiGet);
  const m = u.mariage || {};
  const div = divorceDe(u) || {};
  const fia = ((u.evenements || []).find((e) => e && e.type === "ENGA")) || {};
  const pac = pacsDe(u) || {};
  const pacFin = pacsFinDe(u) || {};
  const retour = () => aller("personnes", { fiche: pid });

  const dFia = champDate(fia.date || "");
  const lFia = champLieu(lieux, { valeur: fia.lieu || "" });
  const dPac = champDate(pac.date || "");
  const lPac = champLieu(lieux, { valeur: pac.lieu || "" });
  const dPacFin = champDate(pacFin.date || "");
  const dMar = champDate(m.date || "");
  const lMar = champLieu(lieux, { valeur: m.lieu || "" });
  const dDiv = champDate(div.date || "");
  const lDiv = champLieu(lieux, { valeur: div.lieu || "" });

  vider(vue);
  vue.append(h("button", { class: "bouton secondaire petit", onclick: retour },
    "← Retour à la fiche" + (nom ? " de " + nom : "")));
  vue.append(h("h1", {}, "Modifier l'union"
    + (u.conjoint ? " avec " + u.conjoint.nom : "")));

  vue.append(h("div", { class: "carte", style: "max-width:620px" },
    h("h2", { style: "margin-top:0" }, "💞 Fiançailles"),
    h("p", { style: "color:var(--gris-clair);font-size:13px;margin:0 0 8px" },
      "Facultatif. Conservées à l'export GEDCOM (balise ENGA)."),
    h("div", { class: "champ" }, h("label", {}, "Date des fiançailles"), dFia.element),
    h("div", { class: "champ" }, h("label", {}, "Lieu des fiançailles"), lFia.element)));

  vue.append(h("div", { class: "carte", style: "max-width:620px" },
    h("h2", { style: "margin-top:0" }, "🤝 PACS / union libre"),
    h("p", { style: "color:var(--gris-clair);font-size:13px;margin:0 0 8px" },
      "Pour un couple non marié. Laissez la date de fin vide si l'union est "
      + "toujours en cours. Conservé à l'export GEDCOM (EVEN / TYPE PACS)."),
    h("div", { class: "champ" }, h("label", {}, "Date du PACS / début de l'union"), dPac.element),
    h("div", { class: "champ" }, h("label", {}, "Lieu"), lPac.element),
    h("div", { class: "champ" }, h("label", {}, "Date de fin (dissolution) — si terminée"), dPacFin.element)));

  vue.append(h("div", { class: "carte", style: "max-width:620px" },
    h("h2", { style: "margin-top:0" }, "💍 Mariage"),
    h("div", { class: "champ" }, h("label", {}, "Date du mariage"), dMar.element),
    h("div", { class: "champ" }, h("label", {}, "Lieu du mariage"), lMar.element)));

  vue.append(h("div", { class: "carte", style: "max-width:620px" },
    h("h2", { style: "margin-top:0" }, "💔 Divorce"),
    h("p", { style: "color:var(--gris-clair);font-size:13px;margin:0 0 8px" },
      "Laissez vide s'il n'y a pas eu de divorce. Le divorce est conservé à "
      + "l'export GEDCOM (balise DIV)."),
    h("div", { class: "champ" }, h("label", {}, "Date du divorce"), dDiv.element),
    h("div", { class: "champ" }, h("label", {}, "Lieu du divorce"), lDiv.element)));

  let enCours = false;
  vue.append(h("div", { class: "barre-actions", style: "max-width:620px" },
    h("button", { class: "bouton", onclick: async () => {
      if (enCours) return;
      enCours = true;
      const dd = dDiv.valeur(), dl = lDiv.valeur();
      const df = dFia.valeur(), lf = lFia.valeur();
      const dp = dPac.valeur(), lp = lPac.valeur(), dpf = dPacFin.valeur();
      // on reconstruit les événements de couple : on garde les « autres »
      // (hors DIV/ENGA/PACS, gérés ici) et on ré-ajoute ce qui est saisi.
      const evenements = (u.evenements || []).filter(
        (e) => e && e.type !== "DIV" && e.type !== "ENGA" && !estPacs(e));
      if (df || lf) evenements.push({ type: "ENGA", date: df, lieu: lf, valeur: "" });
      if (dp || lp) evenements.push({ type: "EVEN", precision: "PACS", date: dp, lieu: lp, valeur: "" });
      if (dpf) evenements.push({ type: "EVEN", precision: "Dissolution de PACS", date: dpf, lieu: "", valeur: "" });
      if (dd || dl) evenements.push({ type: "DIV", date: dd, lieu: dl, valeur: "" });
      try {
        await apiJson("/api/familles/" + u.famille, "PUT",
          { mariage: { date: dMar.valeur(), lieu: lMar.valeur() }, evenements });
        toast("Union enregistrée.");
        retour();
      } catch (e) { toast(e.message); enCours = false; }
    } }, "Enregistrer"),
    h("button", { class: "bouton secondaire", onclick: retour }, "Annuler")));
}

// Impression « à la carte » : une petite fenêtre pour cocher les sections à
// inclure. Le nom/en-tête de la personne est toujours imprimé ; le reste est
// optionnel. Passe le choix à imprimerFiche(f, pid, choix).
function choisirImpression(f, pid) {
  const SECTIONS = [
    ["identite", "Identité"], ["reperes", "Repères de vie"],
    ["chrono", "Vie & chronologie"], ["famille", "Famille"],
    ["sources", "Sources & preuves"], ["notes", "Recherche & notes"],
    ["photos", "Photos"],
  ];
  const cases = {};
  const lignes = SECTIONS.map(([k, lib]) => {
    const chk = h("input", { type: "checkbox", checked: "checked" });
    cases[k] = chk;
    return h("label", { style: "display:flex;gap:8px;align-items:center;padding:5px 0;cursor:pointer" }, chk, lib);
  });
  ouvrirModale(h("div", {},
    h("p", { style: "margin-top:0;font-size:13px;color:var(--gris)" },
      "Cochez les sections à inclure. Le nom de la personne est toujours imprimé."),
    ...lignes,
    h("div", { class: "barre-actions", style: "margin-top:12px" },
      h("button", { class: "bouton", onclick: () => {
        const choix = {};
        SECTIONS.forEach(([k]) => { choix[k] = cases[k].checked; });
        if (!Object.values(choix).some(Boolean)) { toast("Cochez au moins une section."); return; }
        fermerModale();
        imprimerFiche(f, pid, choix);
      } }, "🖨 Imprimer"),
      h("button", { class: "bouton secondaire", onclick: fermerModale }, "Annuler"))),
    { titre: "Que voulez-vous imprimer ?", largeur: 420 });
}

export async function vueFiche(vue, pid, ongletInitial) {
  let f;
  try { f = await apiGet("/api/individus/" + pid); }
  catch { toast("Personne introuvable."); return aller("personnes"); }
  noterRecent({ id: pid, nom: f.nom_complet, periode: f.periode });

  const conjoints = f.unions.map((u) => u.conjoint).filter(Boolean);
  const enfants = f.unions.flatMap((u) => u.enfants);
  const prof = (f.professions || []).map((p) => p.valeur ? p.valeur + (p.date ? " (" + p.date + ")" : "") : "").filter(Boolean).join(", ");
  const branche = brancheDeSosa(f.sosa);

  // ── En-tête ────────────────────────────────────────────────────────────
  const teteInfos = h("div", { style: "flex:1;min-width:0" },
    h("h1", {}, f.nom_complet),
    detailsIdentite(f),
    h("div", { style: "color:var(--gris);margin-top:4px" },
      [(f.periode || "dates inconnues") + (f.age != null ? " · " + f.age + " ans" : ""), prof]
        .filter(Boolean).join(" · ")),
    (f.relation_racine && f.racine_nom)
      ? h("div", { class: "fiche-relation", onclick: () => aller("sosa") },
          "👥 " + majuscule(f.relation_racine) + " de " + f.racine_nom)
      : null,
    h("div", { class: "fiche-badges" },
      f.sosa ? h("span", { class: "badge ok", style: "cursor:pointer",
        onclick: () => aller("sosa") }, "Sosa n° " + f.sosa + (f.sosa > 1 ? " · Ancêtre direct" : "")) : null,
      branche ? badge(branche, "info") : null,
      (f.peres.length || f.meres.length)
        ? badge(f.fratrie.length ? f.fratrie.length + " frère(s)/sœur(s)" : "Enfant unique") : null,
      badge(f.vivant ? "Présumé vivant" : "Décédé", f.vivant ? "attention" : ""),
      (f.resn && f.resn !== "") ? badge(RESN_LABEL[f.resn] || f.resn, "attention") : null,
      ...((f.tags || []).map((t) => badge("#" + t, "info")))),
    h("div", { class: "barre-actions", style: "margin-top:10px" },
      h("span", { style: "font-size:13px;color:var(--gris)" }, "Ajouter à la famille :"),
      f.peres.length ? null : h("button", { class: "bouton secondaire petit",
        onclick: () => ajoutRelatif(pid, "pere", f.nom_complet) }, "＋ Père"),
      f.meres.length ? null : h("button", { class: "bouton secondaire petit",
        onclick: () => ajoutRelatif(pid, "mere", f.nom_complet) }, "＋ Mère"),
      h("button", { class: "bouton secondaire petit", onclick: () => ajoutRelatif(pid, "conjoint", f.nom_complet) }, "＋ Conjoint·e"),
      h("button", { class: "bouton secondaire petit", onclick: () => ajoutRelatif(pid, "enfant", f.nom_complet) }, "＋ Enfant"),
      h("button", { class: "bouton secondaire petit", onclick: () => ajoutRelatif(pid, "fratrie", f.nom_complet) }, "＋ Frère / Sœur")));

  vue.append(h("div", { class: "fiche-tete" },
    portraitFiche(f), teteInfos));

  // étoile favori (L13) — état lu au chargement, bascule à la volée
  const estFav = await apiGet("/api/favoris")
    .then((d) => (d.favoris || []).some((x) => x.id === pid)).catch(() => false);
  const btnFav = h("button", { class: "bouton secondaire petit", onclick: async () => {
    try {
      const r = await apiJson("/api/favoris/basculer", "POST", { id: pid });
      btnFav.textContent = r.favori ? "★ Favori" : "☆ Favori";
      toast(r.favori ? "Ajouté aux favoris." : "Retiré des favoris.");
    } catch (e) { toast(e.message); }
  } }, estFav ? "★ Favori" : "☆ Favori");

  vue.append(h("div", { class: "barre-actions", style: "margin-bottom:16px" },
    btnFav,
    h("button", { class: "bouton secondaire petit",
      onclick: () => peutRevenir() ? retour() : aller("personnes") }, "← Retour"),
    h("button", { class: "bouton secondaire petit", onclick: () => aller("arbre", { racine: pid }) }, "🌳 Arbre"),
    h("button", { class: "bouton secondaire petit", onclick: () => aller("sosa") }, "↑ Sosa"),
    h("button", { class: "bouton secondaire petit", onclick: () => choisirImpression(f, pid) }, "🖨 Imprimer"),
    h("button", { class: "bouton petit", onclick: () => aller("personnes", { editer: pid }) }, "✏️ Modifier"),
    h("button", { class: "bouton danger petit",
      title: "Supprimer cette personne", "aria-label": "Supprimer cette personne",
      onclick: async () => {
        if (!await confirmer("Supprimer « " + f.nom_complet + " » ? Cette action est définitive.",
          { titre: "Supprimer la personne", valider: "Supprimer", danger: true })) return;
        await apiJson("/api/individus/" + pid, "DELETE", {});
        toast("Personne « " + f.nom_complet + " » supprimée.");
        aller("personnes");
      } }, "🗑")));

  // ── Onglets ────────────────────────────────────────────────────────────
  const onglets = [
    ["synthese", "Synthèse", () => panneauSynthese(f, pid)],
    ["chrono", "Vie & chronologie", () => sectionChronologie(f)
      || h("div", { class: "vide" }, "Aucun événement daté pour l'instant.")],
    ["famille", "Famille", () => panneauFamille(f, pid, conjoints, enfants)],
    ["sources", "Sources & preuves", () => panneauSources(f, pid)],
    // « Recherche web » désactivé pour l'instant (code conservé : blocLiensWeb) ;
    // remplacé par un onglet « Carnet » = les notes du carnet qui citent la personne.
    ["carnet", "Carnet", () => ongletCarnet(pid)],
    ["photos", "Photos", () => sectionPhotos(pid, f)],
    ["gedcom", "Données GEDCOM", () => donneesGedcom(f)],
  ];
  const barre = h("div", { class: "fiche-onglets" });
  const panneau = h("div", {});
  // Onglet initial : « synthese » par défaut, mais on peut demander à rouvrir sur
  // un onglet précis (ex. revenir sur « Sources & preuves » après avoir prouvé).
  let actif = (ongletInitial && onglets.some((o) => o[0] === ongletInitial))
    ? ongletInitial : "synthese";
  async function montrer(id) {
    actif = id;
    barre.querySelectorAll("button").forEach((b) => b.classList.toggle("actif", b.dataset.o === id));
    vider(panneau);
    const build = onglets.find((o) => o[0] === id)[2];
    const contenu = await build();
    if (actif !== id) return;         // un autre onglet a été demandé pendant l'attente
    vider(panneau);
    panneau.append(contenu);
  }
  onglets.forEach(([id, lib]) => barre.append(h("button", {
    class: "fiche-onglet", "data-o": id, onclick: () => montrer(id) }, lib)));
  vue.append(barre, panneau);
  montrer(actif);
}

function portraitFiche(f) {
  const princ = (f.medias || []).find((m) => m.principale) || (f.medias || [])[0];
  if (princ) return h("div", { class: "portrait",
    style: "background-image:url('/media/Photos/" + encodeURIComponent(princ.fichier) + "');"
      + "background-size:cover;background-position:" + (princ.cadrage || "center") });
  return h("div", { class: "portrait" }, initiale(f.nom_complet));
}

// ── Onglet Synthèse : résumé, identité, repères de vie ───────────────────
function panneauSynthese(f, pid) {
  const box = h("div", { class: "fiche-sections" });
  if (f.resume_auto || (f.note || "").trim()) {
    box.append(h("div", { class: "carte" },
      h("h2", {}, "Résumé de vie"),
      h("p", {}, (f.note || "").trim() || f.resume_auto),
      !((f.note || "").trim()) && f.resume_auto
        ? h("p", { style: "color:var(--gris-clair);font-size:12px;margin-bottom:0" },
            "Résumé généré automatiquement — ajoutez une note biographique pour le remplacer.")
        : null));
  }
  box.append(h("div", { class: "fiche-2col" }, identiteCard(f), reperesDeVie(f, pid)));
  return box;
}

function identiteCard(f) {
  const variantes = (f.noms_alternatifs || []).map((v) =>
    [v.prenoms, v.nom].filter(Boolean).join(" ")).filter(Boolean).join(" · ");
  const assoc = (f.associations || []).map((a) =>
    (a.role ? a.role + " : " : "") + (a.nom || a.id || "")).filter(Boolean);
  const carte = h("div", { class: "carte" }, h("h2", {}, "Identité"),
    ligneDef("Nom de référence", f.nom),
    ligneDef("Prénoms", f.prenoms),
    ligneDef("Prénom usuel", f.prenom_principal),
    ligneDef("Préfixe (titre)", f.nom_prefixe),
    ligneDef("Suffixe", f.nom_suffixe),
    ligneDef("Surnom", f.surnom ? "« " + f.surnom + " »" : ""),
    ligneDef("Nom marital", f.nom_marital),
    ligneDef("Variantes", variantes),
    ligneDef("Sexe", ({ M: "Masculin", F: "Féminin", X: "Intersexe", N: "Non consigné" })[f.sexe] || "Inconnu"),
    ligneDef("Statut", f.vivant ? "Présumé vivant" : "Décédé"),
    ligneDef("Identifiant", f.id),
    ligneDef("N° de référence", f.refn),
    ligneDef("Confidentialité", f.resn ? (RESN_LABEL[f.resn] || f.resn) : ""),
    ligneDef("Lien avec la racine", f.relation_racine && f.racine_nom
      ? majuscule(f.relation_racine) + " de " + f.racine_nom : ""));
  if (assoc.length) {
    const l = h("div", { class: "def-ligne" }, h("span", { class: "def-cle" }, "Personnes liées"),
      h("span", { class: "def-val" }, assoc.join(" · ")));
    carte.append(l);
  }
  return carte;
}

function reperesDeVie(f, pid) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "Repères de vie"));
  const nais = f.naissance || {}, dec = f.deces || {};
  const repere = (ico, titre, corps) => corps ? h("div", { class: "repere" },
    h("span", { class: "repere-ico" }, ico),
    h("div", {}, h("div", { class: "repere-titre" }, titre),
      h("div", { class: "repere-corps" }, corps))) : null;
  const lieuxVie = [];
  const vus = new Set();
  const addL = (l) => { l = (l || "").trim(); if (l && !vus.has(l.toLowerCase())) { vus.add(l.toLowerCase()); lieuxVie.push(l); } };
  addL(nais.lieu); (f.residences || []).forEach((r) => addL(r.lieu));
  (f.evenements || []).forEach((e) => addL(e.lieu)); addL(dec.lieu);

  // TOUTES les unions ayant un·e conjoint·e (pas seulement la première) — sinon
  // une 2ᵉ union restait invisible dans la synthèse.
  const unionsRep = (f.unions || []).filter((u) => u.conjoint).flatMap((u) => {
    const dv = divorceDe(u);
    const pac = pacsDe(u), pacFin = pacsFinDe(u);
    const marie = u.mariage && (u.mariage.date || u.mariage.lieu);
    return [
      // PACS / union libre : affiché DÈS QU'IL existe — même si le couple s'est
      // marié ensuite (sinon « PACS puis mariage » perdait le PACS en synthèse).
      pac
        ? repere("🤝", "PACS / union libre", u.conjoint.nom
            + (pac.date ? " · depuis " + pac.date : "")
            + (pacFin && pacFin.date ? " → dissous " + pacFin.date : " · en cours"))
        : null,
      // Mariage → « Union » ; couple avec conjoint mais ni PACS ni mariage → « Union » simple.
      (marie || !pac)
        ? repere("💍", "Union", u.conjoint.nom
            + (marie ? " · " + [u.mariage.date, u.mariage.lieu].filter(Boolean).join(" à ") : ""))
        : null,
      dv && (dv.date || dv.lieu)
        ? repere("💔", "Divorce", "d'avec " + u.conjoint.nom + " · "
            + [dv.date, dv.lieu].filter(Boolean).join(" à ")) : null,
    ];
  });
  const reperes = [
    repere("✳️", "Naissance", [nais.date, nais.lieu].filter(Boolean).join(" à ") || null),
    ...unionsRep,
    repere("✝️", "Décès", ([dec.date, dec.lieu].filter(Boolean).join(" à ")
      + (dec.cause ? " · cause : " + dec.cause : "")).trim() || null),
    repere("🛠", "Profession", (f.professions || []).map((p) => p.valeur ? p.valeur + (p.date ? " (" + p.date + ")" : "") : "").filter(Boolean).join(", ") || null),
    lieuxVie.length ? h("div", { class: "repere" },
      h("span", { class: "repere-ico" }, "📍"),
      h("div", {}, h("div", { class: "repere-titre" }, "Lieux de vie"),
        h("div", { class: "repere-corps" },
          lieuxVie.map((l, i) => h("span", { class: "lien", style: "cursor:pointer",
            onclick: () => aller("lieux", { focus: l }) }, (i ? " · " : "") + l))))) : null,
  ].filter(Boolean);   // ne jamais append(null) : le DOM le convertirait en « null »
  if (!reperes.length)
    reperes.push(h("div", { class: "vide compacte" }, "Repères à compléter."));
  reperes.forEach((r) => carte.append(r));
  return carte;
}

// ── Onglet Famille : cellule + unions + lien racine ──────────────────────
function panneauFamille(f, pid, conjoints, enfants) {
  const box = h("div", { class: "fiche-sections" });
  box.append(celluleFamiliale(f));
  box.append(h("div", { class: "carte" },
    h("h2", {}, "Unions et enfants"),
    ...(f.unions.length ? f.unions.map((u) => blocUnion(f, pid, u))
      : [h("div", { class: "vide compacte" }, "Aucune union enregistrée.")]),
    // « ＋ enfant » au niveau du panneau : permet d'ajouter un enfant SANS
    // conjoint (parent seul / autre parent inconnu) — le blocUnion n'apparaît
    // sinon qu'avec une union existante.
    h("div", { class: "barre-actions", style: "margin-top:8px" },
      h("button", { class: "bouton secondaire petit", onclick: () => ajoutRelatif(pid, "conjoint", f.nom_complet) }, "＋ conjoint·e"),
      h("button", { class: "bouton secondaire petit", onclick: () => ajoutRelatif(pid, "enfant", f.nom_complet) }, "＋ enfant"))));
  if (f.relation_racine && f.racine_nom) {
    box.append(h("div", { class: "carte" },
      h("h2", {}, "Lien avec " + (f.racine_nom.split(" ")[0] || "la racine")),
      h("p", {}, majuscule(f.relation_racine) + " de " + f.racine_nom
        + (f.sosa ? " (Sosa n° " + f.sosa + ")" : "") + ".")));
  }
  return box;
}

function celluleFamiliale(f) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "Cellule familiale"));
  const parents = [...f.peres, ...f.meres];
  const fidParents = (f.famc || [])[0] || null;   // famille-parents à éditer
  const ligneParents = h("div", { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap" });

  // Un parent affiché + ses mini-actions (changer / retirer), ancrées sur la
  // famille-parents (fidParents). `role` = 'mari' (père) ou 'epouse' (mère).
  function blocParent(p, role, libelle) {
    const enveloppe = h("span", { style: "display:inline-flex;gap:4px;align-items:center" },
      pucePersonne(p));
    if (fidParents) {
      enveloppe.append(
        h("button", { class: "bouton secondaire petit", title: "Changer ce parent",
          onclick: async () => {
            const id = await choisirPersonne({ titre: "Changer " + libelle, exclureId: f.id });
            if (!id) return;
            try {
              await apiJson("/api/familles/" + fidParents + "/conjoint", "PUT", { role, id });
              toast("Parent modifié.");
              rechargerFamille(f.id);
            } catch (e) { toast(e.message || "Modification impossible."); }
          } }, "✎"),
        h("button", { class: "bouton secondaire petit", title: "Retirer ce parent",
          onclick: async () => {
            if (!await confirmer("Retirer « " + p.nom + " » comme " + libelle
              + " de " + f.nom_complet + " ? (la personne reste dans l'arbre)",
              { titre: "Retirer le parent", danger: true, valider: "Retirer" })) return;
            try {
              await apiJson("/api/familles/" + fidParents + "/conjoint", "PUT", { role, id: "" });
              toast("Parent retiré.");
              rechargerFamille(f.id);
            } catch (e) { toast(e.message || "Modification impossible."); }
          } }, "✕"));
    }
    return enveloppe;
  }

  if (parents.length) {
    let premier = true;
    const ajouter = (el) => {
      if (!premier) ligneParents.append(h("span", { style: "color:var(--gris-clair)" }, "×"));
      premier = false;
      ligneParents.append(el);
    };
    // pères (rôle « mari »), puis mères (rôle « epouse ») — on connaît ainsi le
    // créneau exact à remplacer, sans se fier à la liste fusionnée.
    f.peres.forEach((p) => ajouter(blocParent(p, "mari", "le père")));
    f.meres.forEach((p) => ajouter(blocParent(p, "epouse", "la mère")));
  } else {
    ligneParents.append(h("span", { style: "color:var(--gris-clair)" }, "Parents inconnus"));
  }
  // Ajout d'un parent manquant, directement là où on le cherche.
  if (!f.peres.length) ligneParents.append(h("button", { class: "bouton secondaire petit",
    onclick: () => ajoutRelatif(f.id, "pere", f.nom_complet) }, "＋ Père"));
  if (!f.meres.length) ligneParents.append(h("button", { class: "bouton secondaire petit",
    onclick: () => ajoutRelatif(f.id, "mere", f.nom_complet) }, "＋ Mère"));

  // Ligne « soi + fratrie » : la personne (mise en avant) et ses frères et sœurs
  // (enfants des mêmes parents), même génération, avec l'ajout au bon endroit.
  const ligneFratrie = h("div", { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap" },
    h("span", { class: "puce-pers", style: "background:var(--accent-pale);border-color:var(--accent);font-weight:600" },
      pastilleSexe(f.sexe), f.nom_complet + (f.periode ? "  " + f.periode : "")));
  (f.fratrie || []).forEach((s) => ligneFratrie.append(pucePersonne(s)));
  ligneFratrie.append(h("button", { class: "bouton secondaire petit",
    onclick: () => ajoutRelatif(f.id, "fratrie", f.nom_complet) }, "＋ Frère / Sœur"));

  carte.append(ligneParents, h("div", { class: "cellule-lien" }), ligneFratrie);
  return carte;
}

function pucePersonne(p) {
  return h("span", { class: "puce-pers", onclick: () => aller("personnes", { fiche: p.id }) },
    pastilleSexe(p.sexe), p.nom + (p.periode ? "  " + p.periode : ""));
}

function blocUnion(f, pid, u) {
  const bloc = h("div", { style: "padding:8px 0;border-bottom:1px solid var(--bord)" });
  const m = u.mariage || {};
  bloc.append(h("div", { class: "sur-titre" }, "Conjoint·e"));
  const ligneConjoint = h("div", { style: "margin:4px 0;display:flex;gap:6px;align-items:center;flex-wrap:wrap" });
  if (u.conjoint) {
    ligneConjoint.append(pucePersonne(u.conjoint));
    ligneConjoint.append(
      h("button", { class: "bouton secondaire petit", title: "Changer ce·tte conjoint·e",
        onclick: async () => {
          const id = await choisirPersonne({ titre: "Changer le conjoint·e", exclureId: pid });
          if (!id) return;
          try {
            await apiJson("/api/familles/" + u.famille + "/conjoint", "PUT",
              { role: u.role_conjoint, id });
            toast("Conjoint·e modifié·e.");
            rechargerFamille(pid);
          } catch (e) { toast(e.message || "Modification impossible."); }
        } }, "✎ Changer"),
      h("button", { class: "bouton secondaire petit", title: "Retirer ce·tte conjoint·e de l'union",
        onclick: async () => {
          if (!await confirmer("Retirer « " + u.conjoint.nom + " » de cette union ?"
            + " (la personne reste dans l'arbre)",
            { titre: "Retirer le conjoint·e", danger: true, valider: "Retirer" })) return;
          try {
            await apiJson("/api/familles/" + u.famille + "/conjoint", "PUT",
              { role: u.role_conjoint, id: "" });
            toast("Conjoint·e retiré·e.");
            rechargerFamille(pid);
          } catch (e) { toast(e.message || "Modification impossible."); }
        } }, "✕ Retirer"));
  } else {
    ligneConjoint.append(h("span", { style: "color:var(--gris-clair)" }, "conjoint·e inconnu·e"));
  }
  bloc.append(ligneConjoint);
  // Faits du couple, chacun sur sa ligne, dans l'ordre PACS → Mariage → Divorce.
  const ligneFait = (txt) => h("div", { style: "color:var(--gris);font-size:13px;margin:2px 0" }, txt);
  const pac = pacsDe(u);
  if (pac) {
    const fin = pacsFinDe(u);
    bloc.append(ligneFait("🤝 PACS / union libre"
      + ((pac.date || pac.lieu) ? " · " + [pac.date, pac.lieu].filter(Boolean).join(" à ") : "")
      + (fin && fin.date ? " → dissolution " + fin.date + " (terminée)" : " · en cours")));
  }
  if (m.date || m.lieu)
    bloc.append(ligneFait("💍 Mariage · " + [m.date, m.lieu].filter(Boolean).join(" à ")));
  const div = divorceDe(u);
  if (div) bloc.append(ligneFait("💔 Divorce"
    + ((div.date || div.lieu) ? " · " + [div.date, div.lieu].filter(Boolean).join(" à ") : "")));
  if (u.enfants.length) {
    bloc.append(h("div", { class: "sur-titre" }, "Enfants"));
    const e = h("div", { style: "display:flex;flex-wrap:wrap;gap:6px;margin-top:2px" });
    u.enfants.forEach((c) => {
      const enveloppe = h("span", { style: "display:inline-flex;gap:4px;align-items:center" },
        pucePersonne(c),
        h("button", { class: "bouton secondaire petit",
          title: "Corriger ses parents / le déplacer",
          onclick: () => menuEnfant(pid, c) }, "⋯"));
      e.append(enveloppe);
    });
    bloc.append(e);
  }
  bloc.append(h("div", { class: "barre-actions", style: "margin-top:6px" },
    h("button", { class: "bouton secondaire petit",
      onclick: () => ajoutRelatif(pid, "enfant", f.nom_complet, u.famille) }, "＋ enfant"),
    h("button", { class: "bouton secondaire petit",
      onclick: () => modifierUnion(pid, u, f.nom_complet) }, "✎ Modifier l'union")));
  return bloc;
}

// ── Onglet Sources & preuves ─────────────────────────────────────────────
async function panneauSources(f, pid) {
  const box = h("div", { class: "fiche-sections" });
  const docs = sectionDocuments(f);
  if (docs) box.append(docs);
  box.append(await sectionPreuves(pid));
  box.append(sectionPistes(f, pid));
  return box;
}

// ── Onglet Données GEDCOM : vue brute des champs stockés ─────────────────
function donneesGedcom(f) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "Données GEDCOM"),
    h("p", { class: "sous-titre" }, "Champs bruts tels qu'enregistrés (utile pour vérifier l'import/export)."));
  const cle = (k, v) => {
    if (v == null || v === "" || (Array.isArray(v) && !v.length)) return null;
    const txt = typeof v === "object" ? JSON.stringify(v, null, 0) : String(v);
    return h("div", { class: "def-ligne" }, h("span", { class: "def-cle" }, k),
      h("span", { class: "def-val", style: "font-family:ui-monospace,monospace;font-size:12.5px;word-break:break-word" }, txt));
  };
  ["id", "sexe", "prenoms", "nom", "nom_particule", "nom_prefixe", "nom_suffixe",
   "prenom_principal", "prenoms_secondaires",
   "surnom", "nom_marital", "noms_alternatifs", "naissance", "deces", "professions", "residences",
   "evenements", "tags", "pistes", "refn", "resn", "associations", "note"].forEach((k) => {
    const ligne = cle(k, f[k]);
    if (ligne) carte.append(ligne);   // ne pas ajouter les champs vides (évite « null »)
  });
  carte.append(h("div", { class: "barre-actions", style: "margin-top:12px" },
    h("button", { class: "bouton secondaire petit", title: "Copier la fiche GEDCOM de cette personne",
      onclick: async (e) => {
        try {
          const r = await apiGet("/api/individus/" + f.id + "/gedcom");
          await navigator.clipboard.writeText(r.gedcom || "");
          toast("GEDCOM de la personne copié dans le presse-papiers.");
        } catch (err) { toast("Copie impossible : " + (err.message || err)); }
      } }, "📋 Copier le GEDCOM")));
  return carte;
}

// Bandeau d'identité détaillée (surnom, nom marital, variantes) sous le titre.
function detailsIdentite(f) {
  const bouts = [];
  if ((f.prenom_principal || "").trim()) bouts.push(["Prénom usuel", f.prenom_principal.trim()]);
  if ((f.surnom || "").trim()) bouts.push(["Dit", "« " + f.surnom.trim() + " »"]);
  if ((f.nom_marital || "").trim()) bouts.push(["Nom marital", f.nom_marital.trim()]);
  if ((f.filiation || "").trim()) bouts.push(["Filiation", f.filiation.trim()]);
  const variantes = (f.noms_alternatifs || []).map((v) => {
    const nom = [v.prenoms, v.nom].filter(Boolean).join(" ").trim();
    const t = TYPE_NOM_LABEL[v.type];
    return nom ? nom + (t ? " (" + t + ")" : "") : "";
  }).filter(Boolean);
  if (variantes.length) bouts.push(["Variantes", variantes.join(" · ")]);
  if (!bouts.length) return null;
  return h("div", { class: "ident-details" },
    ...bouts.map(([k, v]) => h("span", { class: "ident-bout" },
      h("span", { class: "ident-k" }, k + " : "), v)));
}
