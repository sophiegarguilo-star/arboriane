// Point d'entrée du front. Construit la navigation, enregistre les vues et
// démarre le routeur. Chargé en module ES par index.html.
import { h, vider } from "./noyau/dom.js";
import { VUES, etat, aller, retour, peutRevenir, surNavigation, majEspace, restaurerVue } from "./noyau/etat.js";
import { apiGet } from "./noyau/api.js";
import { initGardeVersion } from "./noyau/version.js";
import { initVieServeur } from "./noyau/vie.js";
import { initMaj } from "./composants/maj.js";
import { initModale, fermerModale, modaleOuverte } from "./composants/modale.js";
import { initVolet, fermerVolet, voletOuvert } from "./composants/volet.js";
import { fermerVisionneuse, visionneuseOuverte } from "./composants/visionneuse.js";
import { vueTableau } from "./vues/tableau.js";
import { vuePersonnes } from "./vues/personnes.js";
import { vueEspace } from "./vues/espace.js";
import { vueArbre } from "./vues/arbre.js";
import { vueSosa } from "./vues/sosa.js";
import { vueParente } from "./vues/parente.js";
import { vueCoherence } from "./vues/coherence.js";
import { vueStats } from "./vues/stats.js";
import { vueDonnees } from "./vues/donnees.js";
import { vueLieux } from "./vues/lieux.js";
import { vueActes } from "./vues/actes.js";
import { vueSante } from "./vues/sante.js";
import { vueVerif } from "./vues/verif.js";
import { vueImplexe } from "./vues/implexe.js";
import { vueListes } from "./vues/listes.js";
import { vueFusion } from "./vues/fusionAssistee.js";
import { vueContemporains } from "./vues/contemporains.js";
import { vueFavoris } from "./vues/favoris.js";
import { vueDepots } from "./vues/depots.js";
import { vueLieuxRef } from "./vues/lieuxRef.js";
import { vueCarnet } from "./vues/carnet.js";
import { vueLivres } from "./vues/livres.js";
import { vueExplorateur } from "./vues/explorateur.js";
import { vueRecherche } from "./vues/recherche.js";
import { vueAssistant } from "./vues/assistant.js";
import { vueReglages } from "./vues/reglages.js";
import { vueAide } from "./vues/aide.js";

// ── Structure de la navigation (groupes du cahier des charges) ──────────
const NAV = [
  ["Explorer", [
    ["accueil", "🏠", "Tableau de bord"],
    ["personnes", "👥", "Personnes"],
    ["favoris", "⭐", "Favoris & ensembles"],
    ["arbre", "🌳", "Arbre"],
    ["sosa", "🧭", "Sosa"],
    ["parente", "🔗", "Parenté"],
    ["lieux", "🗺️", "Lieux / Carte"],
    ["lieux-ref", "🏘️", "Référentiel des lieux"],
  ]],
  ["Rechercher", [
    ["recherche", "🎯", "Plan de recherche"],
    ["actes", "📄", "Actes / Sources"],
    ["depots", "🏛️", "Dépôts"],
    ["carnet", "📔", "Carnet de bord"],
  ]],
  ["Analyser", [
    ["stats", "📊", "Statistiques"],
    ["coherence", "⚠️", "Cohérence"],
    ["sante", "🩺", "Santé de l'arbre"],
    ["verif", "🔍", "Qualité des sources"],
    ["implexe", "🧬", "Implexe"],
    ["listes", "📋", "Listes & index"],
    ["fusion", "🔀", "Fusion assistée"],
    ["contemporains", "🕰", "Chronologie"],
  ]],
  ["Composer", [
    ["livres", "📖", "Livres"],
  ]],
  ["Outils", [
    ["espace", "🗂️", "Espace de travail"],
    ["explorateur", "📂", "Explorateur"],
    ["donnees", "⇅", "Sauvegarde et export"],
    ["assistant", "🤖", "Assistant"],
    ["reglages", "⚙️", "Réglages"],
    ["apropos", "❓", "Aide & tutoriels"],
  ]],
];

// ── Enregistrement des vues ─────────────────────────────────────────────
VUES.accueil = vueTableau;
VUES.personnes = vuePersonnes;
VUES.espace = vueEspace;
VUES.arbre = vueArbre;
VUES.sosa = vueSosa;
VUES.parente = vueParente;
VUES.coherence = vueCoherence;
VUES.stats = vueStats;
VUES.donnees = vueDonnees;
VUES.lieux = vueLieux;
VUES.actes = vueActes;
VUES.sante = vueSante;
VUES.verif = vueVerif;
VUES.implexe = vueImplexe;
VUES.listes = vueListes;
VUES.fusion = vueFusion;
VUES.contemporains = vueContemporains;
VUES.favoris = vueFavoris;
VUES.depots = vueDepots;
VUES["lieux-ref"] = vueLieuxRef;
VUES.carnet = vueCarnet;
VUES.livres = vueLivres;
VUES.explorateur = vueExplorateur;
VUES.recherche = vueRecherche;
VUES.assistant = vueAssistant;
VUES.reglages = vueReglages;
VUES.apropos = vueAide;
// Tous les onglets sont désormais actifs — plus d'espace réservé.

// ── Construction du menu ────────────────────────────────────────────────
function construireMenu() {
  const liste = document.getElementById("menu-liste");
  vider(liste);
  for (const [groupe, entrees] of NAV) {
    liste.append(h("div", { class: "menu-groupe" }, groupe));
    for (const [nom, emoji, libelle] of entrees) {
      liste.append(h("button", {
        class: "onglet" + (etat.vue === nom ? " actif" : ""),
        "data-vue": nom, onclick: () => aller(nom),
      }, h("span", { class: "oic" }, emoji), libelle));
    }
  }
}

surNavigation((nom) => {
  document.querySelectorAll(".onglet").forEach((b) =>
    b.classList.toggle("actif", b.getAttribute("data-vue") === nom));
});

function majIndicateur() {
  const el = document.getElementById("indic-arbre");
  const esp = etat.espace;
  if (esp && esp.ouvert) {
    el.textContent = "🌳 " + esp.nom;
    el.classList.add("actif");
  } else {
    el.textContent = "Aucun arbre ouvert";
    el.classList.remove("actif");
  }
}
surNavigation(majIndicateur);

// ── Recherche globale (menu) — personnes, lieux, sources ────────────────
function initRechercheGlobale() {
  const input = document.getElementById("recherche-globale");
  if (!input) return;
  const menu = h("div", { class: "champ-menu", style: "position:absolute;z-index:45;width:280px;max-height:60vh;overflow:auto" });
  input.parentElement.style.position = "relative";
  input.parentElement.append(menu);
  let cache = null, t = null;

  async function charger() {
    const [ind, lieux, srcs] = await Promise.all([
      apiGet("/api/individus").catch(() => []),
      apiGet("/api/lieux").catch(() => ({ lieux: [] })),
      apiGet("/api/sources").catch(() => ({ sources: [] })),
    ]);
    return { ind, lieux: (lieux.lieux || []), srcs: (srcs.sources || []) };
  }

  function choisir(fn) {
    input.value = ""; menu.classList.remove("on"); fn();
  }
  function groupe(titre) {
    menu.append(h("div", { style: "padding:4px 10px;font-size:11px;text-transform:uppercase;"
      + "letter-spacing:.04em;color:var(--gris-clair);background:var(--ivoire)" }, titre));
  }
  function option(texte, meta, fn) {
    menu.append(h("div", { class: "champ-option",
      onmousedown: (e) => { e.preventDefault(); choisir(fn); } },
      texte, meta ? h("span", { style: "color:var(--gris-clair);font-size:12px" }, "  · " + meta) : null));
  }

  async function chercher() {
    const q = input.value.trim().toLowerCase();
    if (q.length < 2) { menu.classList.remove("on"); return; }
    if (!cache) cache = await charger();
    const pers = cache.ind.filter((p) => (p.nom || "").toLowerCase().includes(q)).slice(0, 8);
    const lieux = cache.lieux.filter((l) => (l.nom || "").toLowerCase().includes(q)).slice(0, 5);
    const srcs = cache.srcs.filter((s) => (s.titre || "").toLowerCase().includes(q)).slice(0, 5);
    vider(menu);
    if (!pers.length && !lieux.length && !srcs.length) { menu.classList.remove("on"); return; }
    if (pers.length) {
      groupe("Personnes");
      pers.forEach((p) => option(p.nom, p.periode, () => aller("personnes", { fiche: p.id })));
    }
    if (lieux.length) {
      groupe("Lieux");
      lieux.forEach((l) => option("📍 " + l.nom, l.nb_personnes + " pers.", () => aller("lieux", { focus: l.nom })));
    }
    if (srcs.length) {
      groupe("Sources");
      srcs.forEach((s) => option("📄 " + s.titre, s.type, () => aller("actes", { source: s.id })));
    }
    menu.classList.add("on");
  }
  input.addEventListener("input", () => { clearTimeout(t); t = setTimeout(chercher, 180); });
  input.addEventListener("focus", () => { cache = null; });   // recharge si l'arbre a changé
  input.addEventListener("blur", () => setTimeout(() => menu.classList.remove("on"), 150));
  surNavigation(() => { cache = null; });
}

// ── Raccourcis clavier ──────────────────────────────────────────────────
function initClavier() {
  document.addEventListener("keydown", (e) => {
    const dansChamp = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
    if (e.key === "Escape") {
      if (visionneuseOuverte()) { fermerVisionneuse(); return; }
      if (modaleOuverte()) { fermerModale(); return; }
      if (voletOuvert()) { fermerVolet(); return; }
    }
    if (e.key === "/" && !dansChamp) {
      e.preventDefault();
      document.getElementById("recherche-globale")?.focus();
    }
    // Alt+← : retour
    if (e.key === "ArrowLeft" && e.altKey && peutRevenir()) { e.preventDefault(); retour(); }
  });
}

// ── Démarrage ───────────────────────────────────────────────────────────
async function afficherVersion() {
  const el = document.getElementById("marque-version");
  if (!el) return;
  try {
    const d = await apiGet("/api/version");
    if (d && d.version) el.textContent = "v" + d.version;
  } catch (e) { /* la version est cosmétique : jamais bloquant */ }
}

(async function demarrer() {
  construireMenu();
  afficherVersion();
  initModale(); initVolet(); initRechercheGlobale(); initClavier();
  await majEspace(apiGet);
  majIndicateur();
  if (!restaurerVue()) aller("accueil");
  initGardeVersion();                       // surveille les changements de version
  initVieServeur();                         // prévient si le serveur local s'arrête
  initMaj();                                // « quoi de neuf » + vérif MAJ (opt-in)
})();
