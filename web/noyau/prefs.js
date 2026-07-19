// Préférences d'AFFICHAGE locales au navigateur (pas des données de l'arbre).
//
// Le « menu simplifié » (audit UX-01) masque les onglets d'analyse avancée
// (implexe, fusion assistée, référentiel des lieux…) pour ne pas noyer les
// débutants — réactivables d'un clic dans Réglages. C'est une préférence de
// POSTE (localStorage), pas de l'arbre : deux ordinateurs peuvent différer.
const CLE_MENU = "arbo_menu_simplifie";

export function menuSimplifie() {
  try { return localStorage.getItem(CLE_MENU) === "1"; } catch { return false; }
}

export function definirMenuSimplifie(actif) {
  try { localStorage.setItem(CLE_MENU, actif ? "1" : "0"); } catch { /* privé */ }
  // app.js écoute cet événement et reconstruit le menu aussitôt.
  window.dispatchEvent(new CustomEvent("arbo-menu-change"));
}
