// Onglet « Qualité des sources » (Lot 5) — 6 vérifications orientées preuves :
// fichiers manquants, à transcrire, plan par dépôt, sexes absents (avec
// validation de la déduction), noms absents, export du compte-rendu de cohérence.
import { h } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";

export async function vueVerif(vue) {
  vue.append(h("h1", {}, "🔍 Qualité des sources"));
  const d = await apiGet("/api/verif").catch(() => null);
  if (!d) {
    vue.append(h("div", { class: "vide" }, h("span", { class: "grand" }, "🌱"),
      "Ouvrez un arbre pour lancer les vérifications."));
    return;
  }
  vue.append(h("p", { class: "sous-titre" },
    "Ce que votre arbre vous suggère de vérifier, transcrire et chercher ensuite."));
  const grille = h("div", { class: "grille-cartes large" });
  grille.append(
    carteFichiers(d.fichiers_manquants),
    carteTranscrire(d.a_transcrire),
    carteSexes(d.sexes_absents),
    carteDeces(d.deces_presumes),
    carteNoms(d.noms_absents),
    carteCoherence(d.coherence),
    carteDatesDouteuses(d.dates_douteuses),
    carteLieuxSansPays(d.lieux_sans_pays, d.pays_defaut),
    cartePlanDepot(d.plan_depots));      // en dernier : c'est la carte la plus haute
  vue.append(grille);
}

// Lieux sans pays (retour utilisateur Michel) : on propose d'ajouter le « pays
// par défaut » des Réglages à ceux qui n'en ont pas — utile après un import.
function carteLieuxSansPays(lst, paysDefaut) {
  lst = lst || [];
  const c = h("div", { class: "carte" }, tete(lst.length, "Lieux sans pays", true),
    h("p", { class: "sous-titre" },
      "Lieux qui n'indiquent pas de pays. Préciser le pays fiabilise le géocodage "
      + "(ex. « Neufchâteau » en Belgique plutôt que dans les Vosges)."));
  if (!lst.length) {
    c.append(h("p", { class: "vide compacte" }, "Tous vos lieux indiquent un pays. 🎉"));
    return c;
  }
  if ((paysDefaut || "").trim()) {
    const btn = h("button", { class: "bouton petit", onclick: async () => {
      btn.disabled = true;
      try {
        const r = await apiJson("/api/lieux/ajouter-pays", "POST", {});
        toast(r.modifies + " occurrence(s) précisée(s) avec « " + paysDefaut + " ».");
        aller("verif");
      } catch (e) { btn.disabled = false; toast("Impossible : " + e.message); }
    } }, "🌍 Ajouter « " + paysDefaut + " » à tous");
    c.append(h("div", { class: "barre-actions", style: "margin:2px 0 8px" }, btn));
  } else {
    c.append(h("p", { class: "sous-titre" },
      "Astuce : définissez un « Pays par défaut » dans ",
      h("span", { class: "lien", style: "cursor:pointer", onclick: () => aller("reglages") },
        "Réglages"), " pour l'ajouter en un clic."));
  }
  const box = h("div", { class: "liste-pers compacte liste-defilante" });
  lst.slice(0, 60).forEach((x) => box.append(
    h("div", { class: "ligne-pers", onclick: () => aller("lieux", { focus: x.nom }) },
      h("strong", {}, x.nom),
      h("span", { class: "meta" }, x.nb + " occurrence(s)"))));
  c.append(box);
  return c;
}

function carteDatesDouteuses(dd) {
  dd = dd || [];
  const c = h("div", { class: "carte" }, tete(dd.length, "Dates douteuses", true),
    h("p", { class: "sous-titre" },
      "Dates hors format reconnu — elles risquent d'être mal lues par d'autres logiciels."));
  if (!dd.length) {
    c.append(h("p", { class: "vide compacte" }, "Toutes les dates sont bien formées. 🎉"));
    return c;
  }
  const box = h("div", { class: "liste-pers compacte liste-defilante" });
  dd.slice(0, 60).forEach((x) => box.append(
    h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: x.id }) },
      h("strong", {}, x.nom),
      h("span", { class: "meta" }, x.contexte + " : « " + x.date + " » — " + x.raison))));
  c.append(box);
  return c;
}

function tete(n, titre, alerte) {
  return h("h2", {}, badge(String(n), n && alerte ? "attention" : "ok"), " " + titre);
}

function carteFichiers(fm) {
  const n = fm.nb_manquants;
  const c = h("div", { class: "carte" }, tete(n, "Fichiers manquants", true),
    h("p", { class: "sous-titre" },
      fm.presents + " / " + fm.total + " fichiers bien retrouvés sur le disque."));
  if (!n) { c.append(h("p", { class: "vide compacte" }, "Tous les scans sont là. 🎉")); return c; }
  const box = h("div", { class: "liste-pers compacte" });
  fm.manquants.slice(0, 50).forEach((m) => box.append(
    h("div", { class: "ligne-pers",
      onclick: () => aller(m.origine === "source" ? "actes" : "personnes",
        m.origine === "source" ? { source: m.id } : { fiche: m.id }) },
      h("strong", {}, "✕ " + m.fichier),
      h("span", { class: "meta" }, m.contexte))));
  c.append(box);
  return c;
}

function carteTranscrire(at) {
  const c = h("div", { class: "carte" }, tete(at.total, "À transcrire", true),
    h("p", { class: "sous-titre" }, "Sources avec un scan mais sans relevé saisi."));
  if (!at.total) { c.append(h("p", { class: "vide compacte" }, "Tout est transcrit. 🎉")); return c; }
  const box = h("div", { class: "liste-pers compacte" });
  at.sources.slice(0, 50).forEach((s) => box.append(
    h("div", { class: "ligne-pers", onclick: () => aller("actes", { source: s.id }) },
      h("strong", {}, s.titre || s.id),
      s.date ? h("span", { class: "meta" }, s.date) : null)));
  c.append(box);
  return c;
}

function cartePlanDepot(pd) {
  const c = h("div", { class: "carte" }, tete(pd.groupes.length, "Plan par dépôt", false),
    h("p", { class: "sous-titre" }, pd.total + " actes à rechercher, regroupés par lieu."));
  if (!pd.groupes.length) { c.append(h("p", { class: "vide compacte" }, "Aucun acte en attente. 🎉")); return c; }
  pd.groupes.slice(0, 20).forEach((g) => {
    const det = h("details", {}, h("summary", {},
      h("strong", {}, g.depot), " ", badge(g.nb + " acte" + (g.nb > 1 ? "s" : ""))));
    const box = h("div", { class: "liste-pers compacte" });
    g.pistes.forEach((p) => box.append(
      h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: p.personne }) },
        h("strong", {}, p.personne_nom), h("span", { class: "meta" }, p.quoi))));
    det.append(box); c.append(det);
  });
  return c;
}

function carteSexes(sa) {
  const c = h("div", { class: "carte" }, tete(sa.total, "Sexes absents", true),
    h("p", { class: "sous-titre" },
      sa.nb_deductibles + " déductibles du rôle familial (à valider)."));
  if (!sa.total) { c.append(h("p", { class: "vide compacte" }, "Tous les sexes sont renseignés. 🎉")); return c; }
  const box = h("div", { class: "liste-pers compacte" });
  const fini = h("p", { class: "vide compacte", style: "display:none" }, "Plus rien à valider. 🎉");
  let restant = sa.total;
  sa.personnes.slice(0, 60).forEach((p) => {
    const infos = h("div", {},
      h("strong", { style: "cursor:pointer",
        onclick: () => aller("personnes", { fiche: p.id }) }, p.nom),
      h("span", { class: "meta" }, p.raison
        ? "déduit : " + (p.sexe_propose === "M" ? "masculin" : "féminin") + " — " + p.raison
        : "à préciser"));
    const ligne = h("div", { class: "ligne-pers" }, infos);
    if (p.sexe_propose) {
      const btn = h("button", { class: "bouton secondaire petit" },
        p.sexe_propose === "M" ? "Valider ♂" : "Valider ♀");
      btn.onclick = async () => {
        btn.disabled = true;
        try {
          await apiJson("/api/verif/sexe", "POST", { id: p.id, sexe: p.sexe_propose });
          ligne.remove();
          restant -= 1;
          toast(p.nom + " : sexe " + (p.sexe_propose === "M" ? "masculin" : "féminin") + " posé.");
          if (restant <= 0) fini.style.display = "";
        } catch (e) {
          btn.disabled = false;
          toast("Impossible : " + e.message);
        }
      };
      ligne.append(btn);
    }
    box.append(ligne);
  });
  c.append(box, fini);
  return c;
}

function carteDeces(dp) {
  const c = h("div", { class: "carte" }, tete(dp.total, "Présumés vivants trop âgés", true),
    h("p", { class: "sous-titre" },
      "Sans date de décès mais trop âgé·e·s pour être en vie (âge minimal déduit ≥ "
      + dp.seuil + " ans, souvent faute de date de naissance). On pose « décédé·e, "
      + "sans date » — aucune date n'est inventée."));
  if (!dp.total) {
    c.append(h("p", { class: "vide compacte" }, "Aucun présumé vivant improbable. 🎉"));
    return c;
  }
  const box = h("div", { class: "liste-pers compacte liste-defilante" });
  const fini = h("p", { class: "vide compacte", style: "display:none" }, "Tout est corrigé. 🎉");
  const btnTout = h("button", { class: "bouton petit" }, "Tout corriger (" + dp.total + ")");
  let restant = dp.total;
  btnTout.onclick = async () => {
    btnTout.disabled = true;
    try {
      const r = await apiJson("/api/verif/deces", "POST", { tous: true });
      toast(r.corriges + " personne·s marquée·s décédée·s (sans date).");
      aller("verif");                    // recharge la vue
    } catch (e) { btnTout.disabled = false; toast("Impossible : " + e.message); }
  };
  dp.personnes.slice(0, 80).forEach((p) => {
    const ligne = h("div", { class: "ligne-pers" },
      h("div", {},
        h("strong", { style: "cursor:pointer",
          onclick: () => aller("personnes", { fiche: p.id }) }, p.nom),
        h("span", { class: "meta" }, "au moins " + p.age_min + " ans — " + p.indice)));
    const btn = h("button", { class: "bouton secondaire petit" }, "Décédé·e");
    btn.onclick = async () => {
      btn.disabled = true;
      try {
        await apiJson("/api/verif/deces", "POST", { id: p.id });
        ligne.remove(); restant -= 1;
        toast(p.nom + " : marqué·e décédé·e (sans date).");
        if (restant <= 0) { fini.style.display = ""; btnTout.style.display = "none"; }
      } catch (e) { btn.disabled = false; toast("Impossible : " + e.message); }
    };
    ligne.append(btn);
    box.append(ligne);
  });
  c.append(h("div", { class: "barre-actions" }, btnTout), box, fini);
  return c;
}

function carteNoms(na) {
  const libelle = { nom: "nom : ?", prenom: "prénom : ?", nom_et_prenom: "nom + prénom : ?" };
  const c = h("div", { class: "carte" }, tete(na.total, "Noms / prénoms absents", true),
    h("p", { class: "sous-titre" }, "Fiches à compléter (un « ? » plutôt qu'un vide invisible)."));
  if (!na.total) { c.append(h("p", { class: "vide compacte" }, "Toutes les fiches sont nommées. 🎉")); return c; }
  const box = h("div", { class: "liste-pers compacte" });
  na.personnes.slice(0, 60).forEach((p) => box.append(
    h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: p.id }) },
      h("strong", {}, p.nom),
      h("span", { class: "meta" }, libelle[p.manque] || "?"))));
  c.append(box);
  return c;
}

function carteCoherence(coh) {
  const c = h("div", { class: "carte" }, tete(coh.total, "Cohérence — export", true),
    h("p", { class: "sous-titre" }, coh.total
      ? "Anomalies détectées, exportables pour traiter hors ligne."
      : "Aucune anomalie. 🎉"));
  if (coh.total) {
    const box = h("div", { class: "liste-pers compacte" });
    coh.alertes.slice(0, 3).forEach((a) => box.append(
      h("div", { class: "ligne-pers",
        onclick: () => a.personne && aller("personnes", { fiche: a.personne }) },
        h("strong", {}, a.personne_nom || "—"), h("span", { class: "meta" }, a.message))));
    c.append(box);
  }
  c.append(h("div", { class: "barre-actions" },
    h("button", { class: "bouton secondaire petit",
      onclick: () => telecharger("coherence.csv", coherenceCsv(coh), "text/csv;charset=utf-8") },
      "⬇ Exporter (CSV)"),
    h("button", { class: "bouton secondaire petit",
      onclick: () => telecharger("coherence.txt", coherenceTxt(coh), "text/plain;charset=utf-8") },
      "⬇ Exporter (txt)")));
  return c;
}

// ── Export client (aucune donnée ne quitte la machine) ──────────────────
function coherenceCsv(coh) {
  const esc = (s) => '"' + String(s == null ? "" : s).replace(/"/g, '""') + '"';
  const lignes = [["Gravité", "Catégorie", "Personne", "Message"].map(esc).join(";")];
  (coh.alertes || []).forEach((a) =>
    lignes.push([a.gravite, a.categorie, a.personne_nom, a.message].map(esc).join(";")));
  return lignes.join("\r\n");
}

function coherenceTxt(coh) {
  const lignes = ["Compte-rendu de cohérence — " + coh.total + " anomalie(s)", ""];
  (coh.alertes || []).forEach((a) =>
    lignes.push("[" + a.gravite + "] " + a.categorie + " — "
      + (a.personne_nom || "") + " : " + a.message));
  return lignes.join("\r\n");
}

function telecharger(nom, contenu, type) {
  const blob = new Blob(["﻿" + contenu], { type });   // BOM : accents lisibles dans Excel
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: nom });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
