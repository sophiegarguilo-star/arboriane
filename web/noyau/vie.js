// Garde « serveur arrêté ».
//
// Arboriane est une page servie par un petit serveur local : si la fenêtre de
// lancement est fermée (ou l'ordinateur mis en veille, ou le serveur planté), la
// page reste affichée mais plus rien ne répond. Sans avertissement, l'utilisateur
// clique dans le vide et croit que le logiciel est cassé.
//
// On sonde donc /api/version (la plus légère des routes, déjà utilisée par la
// garde de version). Deux échecs d'affilée — un seul peut être un hoquet — et on
// affiche un bandeau rouge, permanent, avec un bouton « Réessayer ». Dès que le
// serveur répond de nouveau, le bandeau disparaît de lui-même.
import { bandeau, retirerBandeau, bandeauAffiche } from "../composants/bandeau.js";

const ID = "banniere-serveur-arrete";
const PERIODE_MS = 20000;      // sondage tranquille : c'est du 127.0.0.1
const ECHECS_AVANT_ALERTE = 2;

let echecs = 0;
let minuterie = null;

async function repond() {
  try {
    // Pas d'apiGet ici : on ne veut ni toast d'erreur ni traitement du corps,
    // juste savoir si quelqu'un décroche.
    const r = await fetch("/api/version", { cache: "no-store" });
    return r.ok;
  } catch {
    return false;               // serveur injoignable (fetch a échoué)
  }
}

function alerter() {
  bandeau(ID,
    "Arboriane est arrêté. Vos données sont intactes, mais cette page ne "
    + "répond plus : relancez Arboriane depuis le raccourci du Bureau, puis "
    + "réessayez.",
    [{ texte: "Réessayer", primaire: true, onclick: () => sonder() }],
    { ton: "alerte" });
}

async function sonder() {
  if (await repond()) {
    echecs = 0;
    retirerBandeau(ID);         // le serveur est revenu : on s'efface
    return true;
  }
  echecs += 1;
  if (echecs >= ECHECS_AVANT_ALERTE && !bandeauAffiche(ID)) alerter();
  return false;
}

export function initVieServeur() {
  if (minuterie !== null) return;                 // déjà armée
  minuterie = setInterval(sonder, PERIODE_MS);
  // Un retour sur l'onglet est le moment où l'utilisateur va agir : on vérifie
  // tout de suite plutôt que d'attendre le prochain battement.
  window.addEventListener("focus", sonder);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") sonder();
  });
}

// Exporté pour les bancs de test.
export const _interne = { sonder, ID };
