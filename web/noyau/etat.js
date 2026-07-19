// État applicatif + routeur avec historique.
//
// Les vues s'enregistrent dans VUES (nom → fonction async(conteneur, arg)).
// `aller(nom, arg)` rend la vue ; l'historique permet `retour()`. La dernière
// vue est mémorisée pour reprendre au même endroit après un rechargement.

import { vider, associerLabels } from "./dom.js";
import { toast } from "../composants/toast.js";
import { confirmer } from "../composants/modale.js";

// ── Garde « modifications non enregistrées » (audit UX-02) ────────────────
// Un formulaire ARME gardeSaisie(fn) où fn() dit s'il reste une saisie non
// enregistrée ; toute navigation demande alors confirmation avant de quitter.
// Le garde est désarmé dès qu'on quitte (une seule vue à la fois) et par le
// formulaire lui-même après un enregistrement réussi : gardeSaisie(null).
let _estSale = null;
export function gardeSaisie(fn) { _estSale = fn; }

export const VUES = {};
export const etat = { vue: "accueil", arg: null, espace: null };

// Onglets accessibles SANS arbre ouvert. Tous les autres exigent un arbre :
// sans arbre, on renvoie vers l'accueil (qui guide la création/ouverture) au
// lieu de laisser chaque vue afficher un état vide cryptique (« Impossible. »,
// « Il faut au moins deux personnes. »…).
const VUES_LIBRES = new Set(["accueil", "espace", "apropos", "reglages"]);

const _historique = [];          // [{nom, arg}] — max 60
const _abonnes = [];
export function surNavigation(fn) { _abonnes.push(fn); }

export function peutRevenir() { return _historique.length > 1; }

const CLE_VUE = "arbo_derniere_vue";

function _memoriser() {
  try {
    localStorage.setItem(CLE_VUE, JSON.stringify(
      { nom: etat.vue, arg: (typeof etat.arg === "object" ? etat.arg : etat.arg) }));
  } catch { /* quota / mode privé */ }
}

// Un formulaire de saisie (création/édition) ne doit jamais être une cible de
// « Retour » : on ne le mémorise pas dans l'historique.
function _estFormulaire(arg) {
  return !!(arg && (arg.editer || arg.creer));
}

let _navSeq = 0;                        // jeton de navigation (anti-empilement)

export async function aller(nom, arg = null, sansHistorique = false) {
  const cible = document.getElementById("vue");
  const rendu = VUES[nom];
  if (!rendu) { console.warn("Vue inconnue :", nom); return; }
  // Saisie non enregistrée ? On demande avant de jeter le travail (UX-02).
  if (_estSale) {
    let sale = false;
    try { sale = !!_estSale(); } catch { sale = false; }
    if (sale && !(await confirmer(
      "Quitter sans enregistrer ? Vos modifications seront perdues.",
      { titre: "Modifications non enregistrées", valider: "Quitter", danger: true }))) return;
    _estSale = null;                     // on quitte : le garde est consommé
  }
  // Garde-fou : un onglet qui exige un arbre, sans arbre ouvert → retour guidé
  // à l'accueil. On ne bloque que si l'on SAIT qu'aucun arbre n'est ouvert
  // (etat.espace renseigné et ouvert === false) ; en cas d'inconnu, on laisse
  // la vue se rendre normalement.
  if (!VUES_LIBRES.has(nom) && etat.espace && etat.espace.ouvert === false) {
    toast("Ouvrez ou créez d'abord un arbre.");
    if (nom !== "accueil") return aller("accueil", null, sansHistorique);
    return;
  }
  const memeVue = etat.vue === nom && JSON.stringify(etat.arg) === JSON.stringify(arg);
  if (!sansHistorique && !memeVue && !_estFormulaire(etat.arg)) {
    _historique.push({ nom: etat.vue, arg: etat.arg });
    if (_historique.length > 60) _historique.shift();
  }
  etat.vue = nom; etat.arg = arg;
  _memoriser();
  const seq = ++_navSeq;
  _abonnes.forEach((fn) => { try { fn(nom, arg); } catch (e) { console.error(e); } });
  // On construit la vue dans un conteneur DÉTACHÉ : un rendu asynchrone plus lent
  // ne peut donc plus « coller » son contenu sur un écran déjà remplacé.
  const conteneur = document.createElement("div");
  try {
    await rendu(conteneur, arg);
  } catch (e) {
    console.error("Erreur de rendu", nom, e);
    conteneur.textContent = "";
    const d = document.createElement("div");
    d.className = "vide"; d.textContent = "Une erreur est survenue dans cette vue.";
    conteneur.append(d);
  }
  if (seq !== _navSeq) return;          // une navigation plus récente a pris la main
  vider(cible);
  while (conteneur.firstChild) cible.append(conteneur.firstChild);
  associerLabels(cible);          // labels ↔ champs (A11Y-05), sur toute vue rendue
  window.scrollTo(0, 0);
}

export function retour() {
  const prec = _historique.pop();
  if (prec) aller(prec.nom, prec.arg, true);
}

export function restaurerVue() {
  try {
    const v = JSON.parse(localStorage.getItem(CLE_VUE) || "null");
    if (v && VUES[v.nom]) { aller(v.nom, v.arg, true); return true; }
  } catch { /* rien */ }
  return false;
}

export async function majEspace(apiGet) {
  try { etat.espace = await apiGet("/api/espace"); }
  catch { etat.espace = { ouvert: false }; }
  return etat.espace;
}
