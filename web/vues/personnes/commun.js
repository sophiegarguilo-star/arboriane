// Personnes — constantes et petits utilitaires partagés par les sous-modules
// (liste, fiche, formulaire, impression, sections…). Aucune logique de vue ici.
import { h } from "../../noyau/dom.js";

export const SEXES = [["F", "Féminin"], ["M", "Masculin"], ["U", "Inconnu"],
               ["N", "Non consigné"], ["X", "Intersexe"]];

// Types de variante de nom (NAME_TYPE GEDCOM).
export const TYPES_NOM = [["aka", "Alias / dit"], ["maiden", "Nom de jeune fille"],
                   ["married", "Nom d'épouse"], ["immigrant", "Nom d'immigration"],
                   ["religious", "Nom religieux"], ["", "Autre"]];

// Niveaux de confidentialité (RESN GEDCOM).
export const RESN = [["", "Public"], ["confidential", "Confidentiel"],
              ["privacy", "Privé"], ["locked", "Verrouillé"]];

// Types d'événement / d'attribut, en optgroups (tag GEDCOM → libellé).
// Événements & faits d'une personne, rangés par MOMENT DE VIE. Chaque code est
// un tag GEDCOM 5.5.1 standard (interopérable) — sauf les faits militaires, en
// « EVEN::<intitulé> » = EVEN + precision (voir plus bas).
export const EVT_GROUPES = [
  ["Enfance & religion", [
    ["CHR", "Baptême (nourrisson)"], ["BAPM", "Baptême (adulte)"],
    ["FCOM", "Communion"], ["CONF", "Confirmation"],
    ["BARM", "Bar Mitzvah"], ["BASM", "Bat Mitzvah"],
    ["ORDN", "Ordination"], ["RELI", "Religion"],
  ]],
  ["Vie civile", [
    ["CENS", "Recensement"], ["GRAD", "Diplôme"], ["EDUC", "Éducation"],
    ["RETI", "Retraite"], ["EMIG", "Émigration"], ["IMMI", "Immigration"],
    ["NATU", "Naturalisation"], ["NATI", "Nationalité"],
    ["ADOP", "Adoption"], ["TITL", "Titre"], ["DSCR", "Signalement"],
  ]],
  ["Décès & sépulture", [
    ["BURI", "Inhumation"], ["CREM", "Crémation"],
    ["WILL", "Testament"], ["PROB", "Succession"],
  ]],
  // Carrière militaire. Format GEDCOM STANDARD : « 1 EVEN <détail> / 2 TYPE
  // <intitulé> », lu par tous les logiciels — type interne « EVEN::<intitulé> ».
  ["Militaire", [
    ["EVEN::Fait militaire", "Fait militaire"],
    ["EVEN::Affectation / unité", "Affectation / unité"],
    ["EVEN::Décoration / médaille", "Décoration / médaille"],
    ["EVEN::Prisonnier de guerre", "Prisonnier de guerre"],
    ["EVEN::Blessure de guerre", "Blessure de guerre"],
    ["EVEN::Campagne / bataille", "Campagne / bataille"],
  ]],
  ["Autre", [
    ["EVEN", "Autre événement"], ["FACT", "Autre fait"],
  ]],
];

// tag GEDCOM → libellé lisible (pour l'affichage de la chronologie)
export const EVT_LABEL = { OCCU: "Profession", RESI: "Résidence" };
EVT_GROUPES.forEach(([, opts]) => opts.forEach(([tag, lib]) => { EVT_LABEL[tag] = lib; }));
// Compat : faits militaires créés en 1.8.2 (tags maison _MIL*) — libellé lisible
// même s'ils ne sont plus proposés à la saisie.
Object.assign(EVT_LABEL, {
  _MILT: "Fait militaire", _MILAFF: "Affectation / unité", _MILDEC: "Décoration / médaille",
  _MILPOW: "Prisonnier de guerre", _MILWND: "Blessure de guerre", _MILCMP: "Campagne / bataille",
});

// Intitulé d'affichage d'un événement : la précision (« Affectation », « PACS »…)
// prime sur le tag générique EVEN.
export function libelleEvt(e) {
  if (e.type === "EVEN" && e.precision) return e.precision;
  return EVT_LABEL[e.type] || e.type || "Fait";
}

// Type interne « normalisé » pour re-sélectionner la bonne option du formulaire
// (un fait militaire standard = EVEN + precision).
export function tagEvt(e) {
  if (e.type === "EVEN" && e.precision && EVT_LABEL["EVEN::" + e.precision]) {
    return "EVEN::" + e.precision;
  }
  return e.type;
}
export const TYPE_NOM_LABEL = Object.fromEntries(TYPES_NOM);
export const RESN_LABEL = Object.fromEntries(RESN);

// Liste — 3 vues : Ligne directe / Tout le monde / Par branche.
export const TRIS_PAR_MODE = {
  directe: [["sosa", "Sosa"], ["nom", "Nom"], ["naissance", "Naissance"]],
  tous: [["nom", "Nom"], ["prenom", "Prénom"], ["naissance", "Naissance"]],
  branche: [["nom", "Nom"], ["prenom", "Prénom"], ["naissance", "Naissance"]],
};

// ── Petits utilitaires ───────────────────────────────────────────────────
// extrait une année d'une chaîne (date ou période « 1850-1912 »)
export function modeleAnnee(s) {
  if (!s) return null;
  const m = String(s).match(/\d{3,4}/g);
  if (!m) return null;
  const plausibles = m.map(Number).filter((n) => n >= 1000 && n <= 2200);
  return plausibles.length ? plausibles[plausibles.length - 1] : null;
}

export function initiale(nom) { return (nom.trim()[0] || "?").toUpperCase(); }

export function majuscule(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }

// branche paternelle / maternelle d'après le n° Sosa (2e bit de poids fort)
export function brancheDeSosa(sosa) {
  if (!sosa || sosa < 2) return null;
  const bits = sosa.toString(2);
  return bits[1] === "0" ? "Branche paternelle" : "Branche maternelle";
}

export function ligneDef(cle, valeur) {
  if (valeur == null || valeur === "") return null;
  return h("div", { class: "def-ligne" },
    h("span", { class: "def-cle" }, cle),
    h("span", { class: "def-val" }, valeur));
}

export function lireBase64(fichier) {
  return new Promise((res) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.readAsDataURL(fichier);
  });
}

// ligneChamp vit désormais dans composants/ (A11Y-05) — ré-export compatible.
export { ligneChamp } from "../../composants/ligneChamp.js";

// bloc repliable (details) pour la saisie avancée
export function blocAvance(titre, ...corps) {
  return h("details", { class: "bloc-avance" },
    h("summary", {}, titre),
    h("div", { class: "bloc-corps" }, ...corps));
}
