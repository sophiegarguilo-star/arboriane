// Mises à jour, côté client. Orchestré une fois au démarrage (voir app.js) :
//   1. « Quoi de neuf » LOCAL après une mise à jour (aucun réseau) ;
//   2. proposition unique d'activer la vérification EN LIGNE (opt-in) ;
//   3. si activée, bandeau discret quand une version plus récente existe.
//
// Rien ne part sur le réseau tant que l'utilisateur n'a pas dit « oui » : la
// vérification en ligne est déclenchée par le serveur local, et lui seul appelle
// GitHub — uniquement pour lire un numéro de version.
import { h } from "../noyau/dom.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { ouvrirModale, fermerModale } from "./modale.js";
import { bandeau } from "./bandeau.js";

// Petite modale à boutons qui se résout à la fermeture (bouton, Échap ou fond).
function modaleBoutons(contenu, boutons, { titre = "", largeur = 520 } = {}) {
  return new Promise((resolve) => {
    let cle = null;
    const fond = document.getElementById("modale-fond");
    const obs = new MutationObserver(() => {
      if (fond.classList.contains("cache")) { obs.disconnect(); resolve(cle); }
    });
    obs.observe(fond, { attributes: true, attributeFilter: ["class"] });
    const barre = h("div", { class: "barre-actions",
      style: "justify-content:flex-end;margin-top:18px;flex-wrap:wrap;gap:8px" });
    for (const b of boutons) {
      barre.append(h("button", {
        class: "bouton" + (b.secondaire ? " secondaire" : ""),
        onclick: () => { cle = b.cle; fermerModale(); },
      }, b.texte));
    }
    ouvrirModale(h("div", {}, contenu, barre), { titre, largeur });
  });
}

function contenuNouveautes(notes) {
  const bloc = h("div", {});
  for (const n of notes) {
    bloc.append(h("h3", { style: "margin:14px 0 6px;font-size:1rem" },
      "Version " + n.version + (n.date ? "  — " + n.date : "")));
    const ul = h("ul", { style: "margin:0 0 4px;padding-left:20px;line-height:1.5" });
    for (const p of (n.points || [])) ul.append(h("li", {}, p));
    bloc.append(ul);
  }
  return bloc;
}

function afficherBandeau(info) {
  // On télécharge DIRECTEMENT l'installeur (.exe) quand GitHub nous le donne ;
  // sinon on ouvre la page (repli). Avant, le bouton ouvrait la page et
  // l'utilisateur récupérait un fichier non exécutable.
  const lien = info.installeur || info.url;
  bandeau("banniere-maj", "Arboriane " + info.derniere + " est disponible.", [
    { texte: "Télécharger", primaire: true,
      onclick: () => window.open(lien, "_blank", "noopener") },
    { texte: "Plus tard", onclick: (retirer) => retirer() },
  ]);
}

// Consentement à la vérification en ligne : un bandeau plutôt qu'une modale, pour
// ne pas barrer l'écran d'accueil d'une nouvelle utilisatrice avant qu'elle ait
// lu la première ligne. Tant qu'elle ne répond pas, la question revient au
// prochain lancement — et rien ne part sur le réseau.
function bandeauConsentement(onOui) {
  const repondre = async (retirer, actif) => {
    retirer();
    try { await apiJson("/api/maj/preference", "POST", { actif }); } catch { /* */ }
    if (actif) onOui();
  };
  bandeau("banniere-maj-consent",
    "Prévenir quand une nouvelle version existe ? Aucune donnée n'est envoyée.", [
      { texte: "Oui, me prévenir", primaire: true, onclick: (r) => repondre(r, true) },
      { texte: "Non merci", onclick: (r) => repondre(r, false) },
    ]);
}

export async function initMaj() {
  let etat;
  try { etat = await apiGet("/api/maj/etat"); } catch { return; }

  // 1) « Quoi de neuf » local (uniquement s'il y a des nouveautés à montrer).
  if (etat.nouveautes && etat.nouveautes.length) {
    await modaleBoutons(contenuNouveautes(etat.nouveautes),
      [{ cle: "ok", texte: "Parfait" }], { titre: "Quoi de neuf dans Arboriane" });
    try { await apiJson("/api/maj/vu", "POST", {}); } catch { /* sans gravité */ }
  } else if (!etat.derniere_vue) {
    // Premier lancement : on mémorise la version pour montrer les nouveautés
    // à la PROCHAINE mise à jour, sans rien afficher maintenant.
    try { await apiJson("/api/maj/vu", "POST", {}); } catch { /* sans gravité */ }
  }

  // 3) Vérification en ligne si autorisée -> bandeau si une MAJ existe.
  const verifierEnLigne = async () => {
    try {
      const info = await apiGet("/api/maj/verifier");
      if (info && info.autorise && info.ok && info.disponible) afficherBandeau(info);
    } catch { /* hors ligne : on ne dérange pas */ }
  };

  // 2) Consentement (opt-in) : bandeau discret, jamais une modale bloquante.
  if (etat.premier_choix) bandeauConsentement(verifierEnLigne);
  else if (etat.verif_active) await verifierEnLigne();
}
