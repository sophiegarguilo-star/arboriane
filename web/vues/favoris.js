// Onglet « Favoris & ensembles » (L13) — personnes épinglées, ensembles nommés
// réutilisables, et anniversaires du mois (réutilise l'éphéméride L8).
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge, pastilleSexe } from "../composants/badge.js";
import { toast } from "../composants/toast.js";
import { confirmer, demander } from "../composants/modale.js";
import { champPersonne } from "../composants/champ.js";

const MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
  "août", "septembre", "octobre", "novembre", "décembre"];

export async function vueFavoris(vue) {
  vue.append(h("h1", {}, "⭐ Favoris & ensembles"));
  const liste = await apiGet("/api/individus").catch(() => []);
  const zoneFav = h("div", {}), zoneEns = h("div", {}), zoneAnn = h("div", {});
  vue.append(h("h2", {}, "⭐ Personnes épinglées"), zoneFav,
    h("h2", { style: "margin-top:24px" }, "👥 Ensembles de personnes"), zoneEns,
    h("h2", { style: "margin-top:24px" }, "🎂 Anniversaires du mois"), zoneAnn);
  await charger(zoneFav, zoneEns, liste);
  await anniversaires(zoneAnn);
}

async function charger(zoneFav, zoneEns, liste) {
  let d;
  try { d = await apiGet("/api/favoris"); }
  catch (e) { zoneFav.append(h("div", { class: "vide" }, e.message)); return; }

  vider(zoneFav);
  if (!d.favoris.length) {
    zoneFav.append(h("div", { class: "vide" },
      "Aucun favori. Ouvrez une fiche et cliquez « ☆ Favori » pour l'épingler."));
  } else {
    const box = h("div", { class: "liste-pers" });
    d.favoris.forEach((p) => box.append(h("div", { class: "ligne-pers",
      onclick: () => aller("personnes", { fiche: p.id }) },
      pastilleSexe(p.sexe), h("span", { class: "nom" }, p.nom),
      h("span", { class: "meta" }, p.periode || ""),
      h("span", { class: "pousse" }),
      h("button", { class: "lien danger", onclick: async (e) => {
        e.stopPropagation();
        await apiJson("/api/favoris/basculer", "POST", { id: p.id }); aller("favoris");
      } }, "retirer"))));
    zoneFav.append(box);
  }

  vider(zoneEns);
  zoneEns.append(h("div", { class: "barre-actions", style: "margin-bottom:8px" },
    h("button", { class: "bouton secondaire petit", onclick: async () => {
      const nom = await demander("Nom du nouvel ensemble :",
        { titre: "Nouvel ensemble", placeholder: "ex. Ma branche paternelle", valider: "Créer" });
      if (nom == null) return;
      await apiJson("/api/ensembles", "POST", { nom }); aller("favoris");
    } }, "➕ Nouvel ensemble")));
  if (!d.ensembles.length) {
    zoneEns.append(h("div", { class: "vide" }, "Aucun ensemble pour l'instant."));
  } else {
    d.ensembles.forEach((e) => zoneEns.append(carteEnsemble(e, liste)));
  }
}

function carteEnsemble(e, liste) {
  const carte = h("div", { class: "carte compacte" });
  const corps = h("div", { style: "margin-top:8px;display:none" });
  let ouvert = false;

  async function basculerOuvert(force) {
    ouvert = force != null ? force : !ouvert;
    corps.style.display = ouvert ? "block" : "none";
    if (!ouvert) return;
    vider(corps);
    const m = await apiGet("/api/ensembles/" + e.id).catch(() => null);
    if (!m) { corps.append(h("div", { class: "vide" }, "—")); return; }
    const box = h("div", { class: "liste-pers" });
    if (!m.membres.length) box.append(h("div", { class: "vide" }, "Ensemble vide."));
    m.membres.forEach((p) => box.append(h("div", { class: "ligne-pers" },
      pastilleSexe(p.sexe),
      h("span", { class: "nom", style: "cursor:pointer",
        onclick: () => aller("personnes", { fiche: p.id }) }, p.nom),
      h("span", { class: "meta" }, p.periode || ""),
      h("span", { class: "pousse" }),
      h("button", { class: "lien danger", onclick: async () => {
        await apiJson("/api/ensembles/" + e.id + "/membre", "POST", { id: p.id });
        basculerOuvert(true);
      } }, "retirer"))));
    const pick = champPersonne(liste, { placeholder: "Ajouter une personne…" });
    corps.append(box, h("div", { class: "barre-actions", style: "margin-top:8px" },
      pick.element,
      h("button", { class: "bouton secondaire petit", onclick: async () => {
        const id = pick.valeur();
        if (!id) { toast("Choisissez une personne."); return; }
        await apiJson("/api/ensembles/" + e.id + "/membre", "POST", { id });
        basculerOuvert(true);
      } }, "➕ Ajouter")));
  }

  carte.append(h("div", { class: "barre-actions" },
    h("strong", {}, e.nom), badge(e.nb + " personne" + (e.nb > 1 ? "s" : "")),
    h("span", { class: "pousse" }),
    h("button", { class: "bouton secondaire petit", onclick: () => basculerOuvert() }, "Ouvrir"),
    h("button", { class: "lien", onclick: async () => {
      const n = await demander("Nouveau nom :", { titre: "Renommer", defaut: e.nom, valider: "Renommer" });
      if (n == null) return;
      await apiJson("/api/ensembles/" + e.id, "PUT", { nom: n }); aller("favoris");
    } }, "renommer"),
    h("button", { class: "lien danger", onclick: async () => {
      if (!await confirmer("Supprimer l'ensemble « " + e.nom + " » ? (les personnes ne sont pas touchées)",
        { titre: "Supprimer l'ensemble", valider: "Supprimer", danger: true })) return;
      await apiJson("/api/ensembles/" + e.id, "DELETE", {}); aller("favoris");
    } }, "supprimer")), corps);
  return carte;
}

async function anniversaires(zone) {
  vider(zone);
  const d = await apiGet("/api/ephemeride").catch(() => ({ personnes: [] }));
  const mois = new Date().getMonth() + 1;
  const duMois = (d.personnes || []).filter((p) => p.mois === mois);
  if (!duMois.length) {
    zone.append(h("div", { class: "vide" }, "Aucun anniversaire en " + MOIS[mois] + "."));
    return;
  }
  const box = h("div", { class: "liste-pers" });
  duMois.forEach((p) => box.append(h("div", { class: "ligne-pers",
    onclick: () => aller("personnes", { fiche: p.id }) },
    h("span", { class: "pers-num" }, String(p.jour)),
    h("span", { class: "nom" }, p.nom),
    h("span", { class: "meta" }, MOIS[p.mois] + (p.annee ? " " + p.annee : "")))));
  zone.append(box);
}
