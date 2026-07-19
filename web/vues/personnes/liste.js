// Personnes — vue liste (Ligne directe / Tout le monde / Par branche) :
// recherche, filtres, tri, index A-Z.
import { h, vider, actionnable } from "../../noyau/dom.js";
import { aller } from "../../noyau/etat.js";
import { apiGet } from "../../noyau/api.js";
import { normaliser } from "../../noyau/texte.js";
import { badge, pastilleSexe } from "../../composants/badge.js";
import { SEXES, TRIS_PAR_MODE, modeleAnnee } from "./commun.js";
import { ouvrirDoublons } from "./doublons.js";

const CAT_LIB = { directe: "Lignée directe", elargie: "Famille élargie", hors: "Hors famille" };

export async function vueListe(vue) {
  let liste;
  try { liste = await apiGet("/api/individus"); }
  catch {
    vue.append(h("h1", {}, "Personnes"), h("div", { class: "vide" },
      h("span", { class: "grand" }, "🌳"),
      h("div", {}, "Ouvrez d'abord un arbre pour voir ses personnes."),
      h("button", { class: "bouton", style: "margin-top:12px",
        onclick: () => aller("espace") }, "Aller à l'espace de travail")));
    return;
  }

  const ancetres = liste.filter((p) => p.sosa != null);
  const brMap = {};
  liste.forEach((p) => { if (p.branche) brMap[p.branche] = (brMap[p.branche] || 0) + 1; });
  const branches = Object.entries(brMap).sort((a, b) => b[1] - a[1]);

  let mode = ancetres.length ? "directe" : "tous";
  let tri = "sosa", sens = 1, compacte = false, filtresVisibles = false, brancheFiltre = "";
  let horsMode = "afficher";   // afficher | masquer | seules (personnes hors famille)
  const aCategories = liste.some((p) => p.categorie);

  vue.append(h("div", { style: "display:flex;align-items:center;gap:12px;flex-wrap:wrap" },
    h("h1", { style: "margin:0" }, "Personnes"),
    h("span", { style: "margin-left:auto" }),
    h("button", { class: "bouton", onclick: () => aller("personnes", { creer: true }) }, "➕ Nouvelle personne")));

  // onglets de vue
  const compteurTab = h("span", { style: "margin-left:auto;color:var(--gris)" });
  const tabs = h("div", { class: "pers-tabs" });
  const defTab = (id, lib) => {
    const b = h("button", { class: "pers-tab" + (mode === id ? " actif" : ""),
      onclick: () => { mode = id; tri = TRIS_PAR_MODE[id][0][0]; brancheFiltre = ""; majTout(); } }, lib);
    b.dataset.m = id; return b;
  };
  tabs.append(defTab("directe", "Ligne directe"), defTab("tous", "Tout le monde"),
    ancetres.length ? defTab("branche", "Par branche") : null, compteurTab);
  vue.append(tabs);

  // Légende des catégories de parenté (affichée en vue « Tout le monde »).
  const legende = h("div", { class: "cat-legende", style: "display:none" },
    h("span", { class: "cat-item" }, h("i", { class: "cat-pastille directe" }), "Lignée directe"),
    h("span", { class: "cat-item" }, h("i", { class: "cat-pastille elargie" }), "Famille élargie"),
    h("span", { class: "cat-item" }, h("i", { class: "cat-pastille hors" }), "Hors famille"));
  vue.append(legende);

  // tri + recherche + actions
  const zoneTri = h("div", { class: "pers-tri" });
  const recherche = h("input", { type: "search", placeholder: "Rechercher…", style: "width:220px" });
  const btnDensite = h("button", { class: "bouton secondaire petit" }, "≡ Compact");
  const btnFiltres = h("button", { class: "bouton secondaire petit" }, "⚙ Filtres");
  const barre = h("div", { class: "barre-actions", style: "margin:10px 0 6px" },
    h("span", { style: "color:var(--gris);font-size:13px" }, "Trier"), zoneTri,
    h("span", { style: "margin-left:auto" }), recherche, btnDensite, btnFiltres,
    h("button", { class: "bouton secondaire petit", onclick: ouvrirDoublons }, "⚠ Doublons"));
  vue.append(barre);

  // chips de branche (vue « Par branche »)
  const chipsBranche = h("div", { class: "branche-chips", style: "display:none" });
  vue.append(chipsBranche);

  // panneau de filtres
  const fSexe = h("select", {}, h("option", { value: "" }, "Tous sexes"),
    ...SEXES.map(([v, l]) => h("option", { value: v }, l)));
  const fAnMin = h("input", { type: "number", placeholder: "année min", style: "width:100px" });
  const fAnMax = h("input", { type: "number", placeholder: "année max", style: "width:100px" });
  const fIncomplet = h("input", { type: "checkbox" });
  const fHors = h("select", {},
    h("option", { value: "afficher" }, "Hors famille : afficher"),
    h("option", { value: "masquer" }, "Hors famille : masquer"),
    h("option", { value: "seules" }, "Hors famille : seules"));
  const panneau = h("div", { class: "carte", style: "display:none;padding:12px 16px" },
    h("div", { class: "barre-actions" }, fSexe, fAnMin, h("span", {}, "–"), fAnMax,
      aCategories ? fHors : null,
      h("label", { style: "display:flex;align-items:center;gap:5px" }, fIncomplet, "à compléter (sans source ou sans parent)")));
  vue.append(panneau);

  const conteneur = h("div", { class: "liste-pers" });
  const azIndex = h("div", { class: "az-index" });
  vue.append(h("div", { style: "display:flex;gap:8px;align-items:flex-start" }, conteneur, azIndex));

  const annee = (p) => modeleAnnee(p.naissance && p.naissance.date) || modeleAnnee(p.periode);
  const lettreDe = (p) => ((p.nom_famille || p.nom || "?").trim()[0] || "#").toUpperCase();

  function majTri() {
    vider(zoneTri);
    TRIS_PAR_MODE[mode].forEach(([id, lib]) => {
      const actif = tri === id;
      zoneTri.append(h("button", { class: "tri-chip" + (actif ? " actif" : ""),
        onclick: () => { if (tri === id) sens = -sens; else { tri = id; sens = 1; } rendre(); } },
        lib + (actif ? (sens > 0 ? " ↓" : " ↑") : "")));
    });
  }

  function majChips() {
    vider(chipsBranche);
    chipsBranche.style.display = mode === "branche" ? "flex" : "none";
    if (mode !== "branche") return;
    const chip = (val, lib, n) => h("button", {
      class: "chip-br" + (brancheFiltre === val ? " actif" : "") + (/Maternelle/.test(val) ? " mat" : val ? " pat" : ""),
      onclick: () => { brancheFiltre = val; majChips(); rendre(); } },
      lib + (n != null ? " " + n : ""));
    chipsBranche.append(chip("", "Toutes les branches", null));
    branches.forEach(([b, n]) => chipsBranche.append(chip(b, b, n)));
  }

  function rendre() {
    majTri();
    vider(conteneur);
    conteneur.className = "liste-pers" + (compacte ? " compacte" : "");
    const q = normaliser(recherche.value.trim());
    let base = mode === "directe" ? ancetres : liste;
    if (mode === "branche" && brancheFiltre) base = base.filter((p) => p.branche === brancheFiltre);
    let lst = base.filter((p) => {
      if (q && !normaliser(p.nom).includes(q)) return false;
      if (fSexe.value && p.sexe !== fSexe.value) return false;
      const an = annee(p);
      if (fAnMin.value && (!an || an < +fAnMin.value)) return false;
      if (fAnMax.value && (!an || an > +fAnMax.value)) return false;
      if (fIncomplet.checked && p.identifie && annee(p)) return false;
      // filtre « hors famille » (n'a de sens qu'en vue « Tout le monde »)
      if (mode === "tous" && p.categorie) {
        if (horsMode === "masquer" && p.categorie === "hors") return false;
        if (horsMode === "seules" && p.categorie !== "hors") return false;
      }
      return true;
    });
    lst.sort((a, b) => {
      let r = 0;
      if (tri === "sosa") r = (a.sosa || 1e9) - (b.sosa || 1e9);
      else if (tri === "prenom") r = (a.prenoms || "").localeCompare(b.prenoms || "", "fr");
      else if (tri === "naissance") r = (annee(a) || 9999) - (annee(b) || 9999);
      else r = (a.nom_famille || a.nom).localeCompare(b.nom_famille || b.nom, "fr");
      return r * sens;
    });
    const label = mode === "directe" ? "ancêtre" : "personne";
    compteurTab.textContent = lst.length + " " + label + (lst.length > 1 ? "s" : "");

    if (!lst.length) {
      conteneur.append(h("div", { class: "vide" },
        liste.length ? "Aucune personne ne correspond." : "Aucune personne pour l'instant."));
      azIndex.style.display = "none";
      return;
    }
    lst.forEach((p, i) => {
      const ligne = actionnable(h("div", { class: "ligne-pers", "data-lettre": lettreDe(p),
        onclick: () => aller("personnes", { fiche: p.id }) },
        (mode === "directe" && tri === "sosa") ? h("span", { class: "pers-num" }, String(p.sosa)) : null,
        (mode === "tous" && p.categorie)
          ? h("i", { class: "cat-pastille " + p.categorie, title: CAT_LIB[p.categorie] }) : null,
        pastilleSexe(p.sexe),
        h("span", { class: "nom" }, (p.prenoms ? p.prenoms + " " : ""), h("b", {}, p.nom_famille || p.nom)),
        !p.identifie ? badge("non identifiée") : null,
        h("span", { class: "meta" }, p.periode || ""),
        h("span", { style: "margin-left:auto" }),
        (mode !== "directe" && p.sosa != null) ? h("span", { class: "badge info" }, "Sosa " + p.sosa) : null,
        (!p.identifie || !annee(p)) ? h("span", { class: "pt-alerte", title: "à compléter" }, "•") : null));
      conteneur.append(ligne);
    });
    // index alphabétique (seulement en tri par nom)
    majAZ(tri === "nom" ? lst : null);
  }

  function majAZ(lst) {
    vider(azIndex);
    if (!lst) { azIndex.style.display = "none"; return; }
    azIndex.style.display = "flex";
    const presentes = new Set(lst.map(lettreDe));
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((L) => {
      const on = presentes.has(L);
      azIndex.append(actionnable(h("span", { class: "az-l" + (on ? "" : " absent"),
        onclick: on ? () => {
          const cible = conteneur.querySelector('[data-lettre="' + L + '"]');
          if (cible) cible.scrollIntoView({ behavior: "smooth", block: "start" });
        } : null }, L)));
    });
  }

  function majTout() {
    tabs.querySelectorAll(".pers-tab").forEach((b) => b.classList.toggle("actif", b.dataset.m === mode));
    legende.style.display = (mode === "tous" && aCategories) ? "flex" : "none";
    majChips(); rendre();
  }

  recherche.addEventListener("input", rendre);
  [fSexe, fAnMin, fAnMax].forEach((el) => el.addEventListener("input", rendre));
  fIncomplet.addEventListener("change", rendre);
  fHors.addEventListener("change", () => { horsMode = fHors.value; rendre(); });
  btnFiltres.addEventListener("click", () => {
    filtresVisibles = !filtresVisibles;
    panneau.style.display = filtresVisibles ? "block" : "none";
    btnFiltres.classList.toggle("actif-filtre", filtresVisibles);
  });
  btnDensite.addEventListener("click", () => {
    compacte = !compacte;
    btnDensite.textContent = compacte ? "≡ Confortable" : "≡ Compact";
    rendre();
  });
  majTout();
}
