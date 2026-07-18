// Garde de version : détecte un backend d'une AUTRE version (mise à jour en
// cours, vieux serveur laissé ouvert) et propose de recharger.
//
// Complément des en-têtes de revalidation (ETag) côté serveur : ceux-ci
// empêchent un vieux JS d'être resservi AU rechargement ; ce garde-ci PRÉVIENT
// l'utilisateur qu'un rechargement est devenu utile (onglet resté ouvert
// pendant qu'on a mis à jour le serveur). Non intrusif : jamais de rechargement
// automatique en pleine saisie — juste un bandeau discret.
import { apiGet } from "./api.js";
import { bandeau } from "../composants/bandeau.js";

let buildInitial = null;

async function lireBuild() {
  try {
    const d = await apiGet("/api/version");
    return d && d.build ? String(d.build) : null;
  } catch {
    return null;                       // serveur injoignable : ne pas déranger
  }
}

function afficherBanniere() {
  bandeau("banniere-version", "Arboriane a été mis à jour.",
    [{ texte: "Recharger", primaire: true, onclick: () => location.reload() }]);
}

async function verifier() {
  const build = await lireBuild();
  if (build == null) return;
  if (buildInitial == null) { buildInitial = build; return; }   // 1er appel
  if (build !== buildInitial) afficherBanniere();
}

export async function initGardeVersion() {
  await verifier();                    // mémorise le build servi au chargement
  window.addEventListener("focus", verifier);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") verifier();
  });
}
