// Personnes récemment consultées, mémorisées par arbre (localStorage).
import { etat } from "./etat.js";

function _cle() {
  const chemin = (etat.espace && etat.espace.chemin) || "defaut";
  return "arbo_recents_" + chemin;
}

export function lireRecents() {
  try { return JSON.parse(localStorage.getItem(_cle()) || "[]"); }
  catch { return []; }
}

export function noterRecent(personne) {
  if (!personne || !personne.id) return;
  const item = { id: personne.id, nom: personne.nom || personne.nom_complet || "",
                 periode: personne.periode || "" };
  let liste = lireRecents().filter((r) => r.id !== item.id);
  liste.unshift(item);
  liste = liste.slice(0, 12);
  try { localStorage.setItem(_cle(), JSON.stringify(liste)); } catch { /* quota */ }
}

export function retirerRecent(id) {
  try {
    localStorage.setItem(_cle(), JSON.stringify(lireRecents().filter((r) => r.id !== id)));
  } catch { /* rien */ }
}
