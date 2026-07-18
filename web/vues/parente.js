// Onglet Parenté — lien entre deux personnes (sang ou alliance), présenté comme
// un diagramme : ancêtre commun couronné en haut, branches descendantes.
import { h, vider } from "../noyau/dom.js";
import { aller, etat, majEspace } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";
import { champPersonne } from "../composants/champ.js";
import { pastilleSexe } from "../composants/badge.js";

export async function vueParente(vue, arg) {
  const g = arg || {};
  vue.append(h("h1", {}, "Lien de parenté"));
  vue.append(h("p", { class: "sous-titre" },
    "Choisissez deux personnes : Arboriane retrouve leur lien — ancêtre commun "
    + "(sang) ou, à défaut, alliance (mariage)."));
  await majEspace(apiGet);
  const liste = await apiGet("/api/individus").catch(() => []);
  if (liste.length < 2) {
    vue.append(h("div", { class: "vide" }, "Il faut au moins deux personnes."));
    return;
  }
  const nomDe = (id) => (liste.find((x) => x.id === id) || {}).nom || id;

  // Couple repris de l'historique (arg) si on revient ici : « ← Retour » depuis
  // une fiche redonne les DEUX mêmes personnes et le lien déjà calculé.
  let a = g.a || (etat.espace || {}).racine_id || liste[0].id;
  let b = g.b || liste.find((p) => p.id !== a)?.id || liste[1].id;
  const memoriser = () => { etat.arg = { a, b }; };
  memoriser();

  const pickA = champPersonne(liste, { initial: a, placeholder: "Première personne…",
    onChoix: (id) => { a = id || a; memoriser(); calc(); } });
  const pickB = champPersonne(liste, { initial: b, placeholder: "Seconde personne…",
    onChoix: (id) => { b = id || b; memoriser(); calc(); } });
  const btnSwap = h("button", { class: "par-swap", type: "button", title: "Inverser les deux personnes",
    onclick: () => { pickA.definir(b); pickB.definir(a); const t = a; a = b; b = t; memoriser(); calc(); } }, "⇄");

  vue.append(h("div", { class: "par-saisie" },
    h("div", { class: "par-champ" }, h("label", {}, "Personne 1"), pickA.element),
    btnSwap,
    h("div", { class: "par-champ" }, h("label", {}, "Personne 2"), pickB.element)));
  const res = h("div", { class: "par-resultat" });
  vue.append(res);

  // — une case personne cliquable —
  function chip(p, cls, avecSosa) {
    const el = h("div", { class: "par-chip" + (cls ? " " + cls : ""), title: "Ouvrir la fiche",
      onclick: () => aller("personnes", { fiche: p.id }) },
      pastilleSexe(p.sexe),
      h("span", { class: "par-chip-nom" }, p.nom),
      p.periode ? h("span", { class: "par-chip-per" }, p.periode) : null);
    if (avecSosa && p.sosa != null && p.sosa > 1)
      el.append(h("span", { class: "par-chip-sosa", title: "N° Sosa (par rapport à la personne du bas)" },
        "Sosa " + p.sosa));
    return el;
  }
  // — une colonne (branche) : de sous l'ancêtre jusqu'à la personne —
  function colonne(chaine, tete, distance) {
    const desc = chaine.slice(0, -1).reverse();   // exclut l'ancêtre (montré à part)
    const col = h("div", { class: "par-col" },
      h("div", { class: "par-col-tete" }, tete + " · " + distance
        + " génération" + (distance > 1 ? "s" : "")));
    desc.forEach((p, i) => {
      if (i) col.append(h("div", { class: "par-fleche" }, "↓"));
      col.append(chip(p, i === desc.length - 1 ? "bout" : "", true));
    });
    return col;
  }

  async function calc() {
    vider(res);
    if (a === b) {
      res.append(h("div", { class: "par-verdict" },
        h("span", { class: "par-ico" }, "🙂"),
        h("div", { class: "par-verdict-txt" }, "C'est la même personne.")));
      return;
    }
    const nomA = nomDe(a), nomB = nomDe(b);
    const r = await apiGet("/api/parente?a=" + a + "&b=" + b).catch(() => null);
    const lien = r && r.lien;

    if (!lien) {
      res.append(h("div", { class: "par-vide" },
        h("span", { class: "par-ico" }, "🌿"),
        h("div", {},
          h("div", {}, h("strong", {}, nomA), " et ", h("strong", {}, nomB),
            " n'ont pas d'ancêtre commun connu : ils sont sur des ",
            h("strong", {}, "branches différentes"), " de l'arbre."),
          h("div", { class: "par-precision", style: "margin-top:6px" },
            "C'est fréquent : deux personnes sont souvent reliées par une alliance "
            + "(mariage) plutôt que par le sang."))));
      return;
    }

    if (lien.alliance || lien.type === "alliance") {
      res.append(h("div", { class: "par-verdict par-alliance" },
        h("span", { class: "par-ico" }, "💍"),
        h("div", { class: "par-verdict-txt" },
          h("div", {}, h("strong", {}, nomB), " est ",
            h("strong", { class: "par-lien" }, lien.lien), " de ", h("strong", {}, nomA), "."),
          lien.explication ? h("div", { class: "par-precision" }, lien.explication) : null,
          h("div", { class: "par-precision" }, "Lien par alliance (mariage), non par le sang."))));
      ajouterImpression();
      return;
    }

    // — lien de sang : verdict + diagramme —
    res.append(h("div", { class: "par-verdict" },
      h("span", { class: "par-ico" }, "🔗"),
      h("div", { class: "par-verdict-txt" },
        h("div", {}, h("strong", {}, nomB), " est ",
          h("strong", { class: "par-lien" }, lien.lien), " de ", h("strong", {}, nomA), "."),
        lien.precision ? h("div", { class: "par-precision" }, lien.precision) : null)));
    ajouterImpression();

    const ancetre = lien.chaine_a[lien.chaine_a.length - 1];
    const direct = lien.distance_a === 0 || lien.distance_b === 0;
    const diag = h("div", { class: "par-diag" },
      h("div", { class: "par-anc" },
        h("div", { class: "par-anc-tag" }, direct ? "👑 Ancêtre direct" : "👑 Ancêtre commun"),
        chip(ancetre, "anc")));
    if (direct) {
      const versA = lien.distance_b === 0;   // B est l'ancêtre → on descend vers A
      diag.append(h("div", { class: "par-branches" },
        colonne(versA ? lien.chaine_a : lien.chaine_b, "Vers " + (versA ? nomA : nomB),
          versA ? lien.distance_a : lien.distance_b)));
    } else {
      diag.append(h("div", { class: "par-branches" },
        colonne(lien.chaine_a, "Vers " + nomA, lien.distance_a),
        colonne(lien.chaine_b, "Vers " + nomB, lien.distance_b)));
    }
    res.append(diag);
  }

  function ajouterImpression() {
    res.append(h("div", { class: "par-actions" },
      h("button", { class: "bouton secondaire petit", onclick: () => window.print() },
        "🖨 Imprimer ce lien")));
  }

  calc();
}
