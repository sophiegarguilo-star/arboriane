// Bouton « ← Retour » UNIFIÉ pour tous les sous-écrans.
//
// Règle unique de navigation d'Arboriane : un retour revient à l'ÉCRAN PRÉCÉDENT
// (l'historique déjà tenu par web/noyau/etat.js), JAMAIS à une destination codée
// en dur. Ainsi, quel que soit le chemin d'arrivée (liste, fiche personne,
// recherche, Qualité des sources…), « ← Retour » ramène exactement là d'où l'on
// vient. Le repli (repliVue/repliArg) ne sert que si aucun écran n'est empilé
// (sous-écran ouvert en direct, ou tout premier écran au démarrage).
//
// À NE PAS mettre : sur les onglets du menu (toujours accessibles) ni sur les
// overlays (volet, modale, visionneuse — fermés par Échap / ✕).
import { h } from "../noyau/dom.js";
import { peutRevenir, retour, aller } from "../noyau/etat.js";

export function boutonRetour(repliVue, repliArg = null, libelle = "← Retour") {
  return h("button", {
    class: "bouton secondaire petit",
    onclick: () => (peutRevenir() ? retour() : aller(repliVue, repliArg)),
  }, libelle);
}
