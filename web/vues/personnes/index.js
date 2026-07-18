// Personnes — aiguillage entre liste, fiche et formulaire. Point d'entrée du
// dossier (la vue Personnes a été découpée en modules : liste, fiche,
// fiche_sections, formulaire, impression, doublons, commun).
import { vueListe } from "./liste.js";
import { vueFiche } from "./fiche.js";
import { vueFormulaire } from "./formulaire.js";
export { ouvrirDoublons } from "./doublons.js";

export async function vuePersonnes(vue, arg) {
  if (arg && arg.fiche) return vueFiche(vue, arg.fiche, arg.onglet);
  if (arg && arg.editer) return vueFormulaire(vue, { editer: arg.editer });
  if (arg && arg.creer) return vueFormulaire(vue, { lien: arg.lien });
  return vueListe(vue);
}
