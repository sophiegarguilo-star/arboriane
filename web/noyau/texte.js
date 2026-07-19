// Normalisation de texte pour la RECHERCHE (audit PARC-01/UX-05).
//
// « Génealogie », « genealogie » et « généalogie » doivent se retrouver :
// on abaisse la casse ET on retire les diacritiques (é→e, ç→c, ï→i…) via la
// décomposition Unicode NFD. À appliquer AUX DEUX CÔTÉS de la comparaison
// (texte cherché ET texte saisi), partout où l'on filtre du texte libre.
export function normaliser(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
}
