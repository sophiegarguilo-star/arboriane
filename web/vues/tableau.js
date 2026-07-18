// Tableau de bord — le PREMIER écran. Trois états selon l'arbre ouvert.
import { h } from "../noyau/dom.js";
import { aller, majEspace } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { lireOctetsB64 } from "../noyau/octets.js";
import { toast } from "../composants/toast.js";
import { demander } from "../composants/modale.js";
import { bilanImport } from "../composants/bilanImport.js";
import { confirmerVerrou } from "./espace.js";
import { lireRecents } from "../noyau/recents.js";

function grandBouton(emoji, titre, desc, onclick) {
  return h("button", { class: "carte", onclick,
    style: "text-align:left;cursor:pointer;border:1px solid var(--bord);width:100%" },
    h("div", { style: "font-size:26px;margin-bottom:6px" }, emoji),
    h("h2", {}, titre),
    h("div", { class: "sous-titre", style: "margin:4px 0 0" }, desc));
}

async function ouvrirDemo() {
  await apiJson("/api/espaces/demo", "POST", {});
  await majEspace(apiGet);
  toast("Arbre de démonstration ouvert.");
  aller("accueil");
}

// « Je pars de zéro » : nommer et créer un arbre vide, puis l'ouvrir.
async function creerArbreVide() {
  const nom = await demander("Comment s'appelle votre arbre ?",
    { titre: "Créer un arbre", placeholder: "ex. Famille Martin", valider: "Créer" });
  if (!nom) return;
  try {
    await apiJson("/api/espaces/creer", "POST", { nom });
    await majEspace(apiGet);
    toast("Arbre « " + nom + " » créé.");
    aller("accueil");
  } catch (e) { toast(e.message); }
}

// « J'ai déjà un arbre » : importer un GEDCOM QUI CRÉE un nouvel arbre.
// Le fichier devient un nouveau dossier — cohérent avec « un arbre = un dossier ».
function importerNouvelArbre() {
  const input = h("input", { type: "file", accept: ".ged,.gedcom,text/plain",
    style: "display:none" });
  input.addEventListener("change", async () => {
    const fichier = input.files[0];
    if (!fichier) return;
    // Octets BRUTS (jamais fichier.text() qui décoderait en UTF-8 et casserait
    // les accents d'un GEDCOM ANSI/ANSEL/IBMPC) : le serveur détecte l'encodage.
    const octets_b64 = await lireOctetsB64(fichier);
    const nom = fichier.name.replace(/\.(ged|gedcom)$/i, "") || "Arbre importé";
    try {
      await apiJson("/api/espaces/creer", "POST", { nom });   // nouvel arbre vide
      await majEspace(apiGet);
      const r = await apiJson("/api/import/gedcom/appliquer", "POST", { octets_b64 });
      await majEspace(apiGet);
      const bilan = bilanImport(r);
      toast("Arbre « " + nom + " » — " + bilan.texte,
            bilan.alerte ? { duree: 12000 } : undefined);
      aller("accueil");
    } catch (e) { toast(e.message, { duree: 6000 }); }
  });
  document.body.append(input);
  input.click();
}

// ── État 1 : aucun arbre ouvert ─────────────────────────────────────────
async function accueilVierge(vue) {
  vue.append(h("h1", {}, "Bienvenue dans Arboriane"));
  vue.append(h("p", { class: "sous-titre" },
    "Un atelier local pour transformer vos documents en preuves, vos preuves "
    + "en faits, et vos faits en histoire familiale. Tout reste sur votre "
    + "ordinateur — rien n'est publié, rien n'est envoyé en ligne."));
  const grille = h("div", { class: "grille-cartes" });
  grille.append(
    grandBouton("📥", "J'ai déjà un arbre", "Importer un fichier GEDCOM "
      + "(Geneanet, Heredis, MyHeritage…) : il devient votre nouvel arbre.",
      importerNouvelArbre),
    grandBouton("✏️", "Je pars de zéro", "Créer un arbre vide et saisir votre "
      + "première personne.", creerArbreVide),
    grandBouton("🌱", "Juste découvrir", "Ouvrir l'arbre de démonstration pour "
      + "explorer sans risque.", ouvrirDemo));
  vue.append(grille);

  // ── Reprendre un arbre (seulement si des arbres existent, hors démo) ──
  const espaces = await apiGet("/api/espaces").then((r) => r.espaces).catch(() => []);
  const arbres = espaces.filter((e) => !e.demo);
  if (arbres.length) {
    vue.append(h("h2", { class: "accueil-titsec" }, "Reprendre un arbre"));
    const g = h("div", { style:
      "display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:8px" });
    arbres.forEach((a) => g.append(h("div", { class: "arb-reprise" },
      h("div", { class: "arb-av" }, "🌳"),
      h("div", { style: "min-width:0;flex:1" },
        h("div", { class: "arb-nom" }, a.nom),
        h("div", { class: "arb-meta" }, a.personnes + " personnes")),
      h("button", { class: "bouton petit", onclick: () => reprendre(a.chemin) }, "Ouvrir"))));
    vue.append(g);
  }

  // ── Bandeau « Ce qui fait Arboriane » ──
  vue.append(h("div", { class: "accueil-valeurs" },
    valeur("🔒", "100 % sur votre ordinateur", "Aucune donnée envoyée, aucun compte, aucune publicité."),
    valeur("📄", "Les sources au cœur", "Chaque fait peut être prouvé par un acte, pas seulement affirmé."),
    valeur("🌱", "À votre rythme", "Rien n'est publié sans vous ; l'assistant IA est facultatif.")));

  // ── Un mot vers l'aide ──
  vue.append(h("p", { style: "color:var(--gris);font-size:14px" },
    "Nouvelle en généalogie ? ",
    h("button", { class: "lien", style: "font-weight:600",
      onclick: () => aller("apropos") }, "Ouvrez l'Aide & tutoriels →")));
}

function valeur(emoji, titre, desc) {
  return h("div", { class: "accueil-val" },
    h("span", { class: "accueil-val-e" }, emoji),
    h("div", {}, h("div", { class: "accueil-val-t" }, titre),
      h("div", { class: "accueil-val-d" }, desc)));
}

async function reprendre(chemin) {
  try {
    let r = await apiJson("/api/espaces/ouvrir", "POST", { chemin });
    if (r && r.ok === false && r.verrou) {
      if (!await confirmerVerrou(r.verrou)) return;
      r = await apiJson("/api/espaces/ouvrir", "POST", { chemin, forcer: true });
    }
    await majEspace(apiGet);
    toast("Arbre « " + r.nom + " » ouvert.");
    aller("accueil");
  } catch (e) { toast(e.message); }
}

// ── État 2 : arbre ouvert mais vide ─────────────────────────────────────
function accueilVide(vue, esp) {
  vue.append(h("h1", {}, "Votre arbre est prêt"));
  vue.append(h("p", { class: "sous-titre" },
    "« " + esp.nom + " » ne contient encore personne. Par où commencer ?"));
  const grille = h("div", { class: "grille-cartes" });
  grille.append(
    grandBouton("👤", "Créer la première personne", "Vous, un parent, un aïeul… "
      + "puis reliez la famille.", () => aller("personnes", { creer: true })),
    grandBouton("📥", "Importer un GEDCOM", "Vous avez déjà un fichier d'un autre "
      + "logiciel.", () => aller("donnees")));
  vue.append(grille);
}

// ── État 3 : arbre rempli ───────────────────────────────────────────────
async function accueilRempli(vue, esp) {
  vue.append(h("h1", {}, esp.nom));
  vue.append(h("p", { class: "sous-titre" },
    [esp.personnes + " personnes", esp.familles + " familles", esp.sources + " source(s)"].join("  ·  ")));

  // données de synthèse (en parallèle ; chacune tolère un échec)
  const [stats, coh, sante, ref] = await Promise.all([
    apiGet("/api/statistiques").catch(() => null),
    apiGet("/api/coherence").catch(() => null),
    apiGet("/api/sante").catch(() => null),
    esp.racine_id ? apiGet("/api/individus/" + esp.racine_id).catch(() => null) : Promise.resolve(null),
  ]);
  const anomalies = coh ? coh.total : 0;

  // ── Bandeau « point de départ » (personne de référence de l'arbre) ──
  if (ref) {
    vue.append(h("div", { class: "tb-hero" },
      portraitHero(ref),
      h("div", { style: "flex:1;min-width:0" },
        h("div", { class: "tb-hero-tag" }, "⭐ Point de départ de l'arbre"),
        h("div", { class: "tb-hero-nom" }, ref.nom_complet),
        h("div", { class: "tb-hero-meta" },
          (ref.periode || "dates inconnues") + (ref.age != null ? " · " + ref.age + " ans" : ""))),
      h("div", { style: "display:flex;gap:8px;flex-wrap:wrap" },
        h("button", { class: "bouton secondaire petit",
          onclick: () => aller("personnes", { fiche: ref.id }) }, "Sa fiche"),
        h("button", { class: "bouton petit",
          onclick: () => aller("arbre", { racine: ref.id }) }, "🌳 Son arbre"))));
  }

  // ── 4 cartes KPI (dont Anomalies, cliquable) ──
  vue.append(h("div", { class: "kpis" },
    kpi("👥", "var(--sauge-pale)", esp.personnes, "Personnes", () => aller("personnes")),
    kpi("👪", "var(--sauge-pale)", esp.familles, "Familles"),
    kpi("📄", "var(--accent-pale)", esp.sources, "Sources", () => aller("actes")),
    kpi(anomalies ? "⚠️" : "✅", anomalies ? "var(--accent-pale)" : "var(--sauge-pale)",
      anomalies, anomalies > 1 ? "Anomalies" : "Anomalie", () => aller("coherence"))));

  // ── 3 cartes de synthèse ──
  vue.append(h("div", { class: "tb-row3" },
    carteRepartition(stats, sante),
    carteRecents(),
    carteSante(sante, anomalies)));

  // ── Parcours métier : guider par les vrais gestes ──
  const parcours = [
    ["👤", "J'ajoute une personne", () => aller("personnes", { creer: true })],
    ["📄", "Je prouve un fait", () => aller("actes")],
    ["🔍", "Je suis une piste", () => aller("recherche")],
    ["🌳", "J'explore mon arbre", () => aller("arbre")],
    ["🌍", "Je prépare une publication", () => aller("donnees")],
    ["💾", "Je sauvegarde mon travail", sauvegarder],
  ];
  vue.append(h("h2", { class: "h2-parcours",
    style: "font-family:var(--serif);color:var(--vert);margin:4px 0 12px" },
    "Que voulez-vous faire ?"));
  const grilleP = h("div", { class: "parcours" });
  parcours.forEach(([emoji, titre, action]) => grilleP.append(
    h("button", { class: "geste", onclick: action },
      h("span", { class: "geste-e" }, emoji),
      h("span", { class: "geste-t" }, titre))));
  vue.append(grilleP);
}

function portraitHero(ref) {
  const princ = (ref.medias || []).find((m) => m.principale) || (ref.medias || [])[0];
  if (princ) return h("div", { class: "tb-hero-portrait",
    style: "background-image:url('/media/Photos/" + encodeURIComponent(princ.fichier) + "');"
      + "background-size:cover;background-position:" + (princ.cadrage || "center") });
  return h("div", { class: "tb-hero-portrait" }, (ref.nom_complet.trim()[0] || "?").toUpperCase());
}

function kpi(emoji, fond, n, label, onclick) {
  return h("div", { class: "kpi" + (onclick ? " cliquable" : ""), onclick: onclick || null },
    h("div", { class: "kpi-ico", style: "background:" + fond }, emoji),
    h("div", {}, h("strong", {}, String(n)), h("span", {}, label)));
}

function barre(pct, couleur) {
  return h("div", { class: "tb-barre" },
    h("i", { style: "width:" + Math.max(0, Math.min(100, pct)) + "%;background:" + couleur }));
}

function carteRepartition(stats, sante) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "📊 Répartition"));
  if (!stats) { carte.append(h("p", { class: "sous-titre" }, "—")); return carte; }
  const tot = stats.personnes || 1;
  const pct = (n) => Math.round(n * 100 / tot);
  // via h() (qui ignore les enfants null) pour ne jamais insérer « null »
  carte.append(h("div", {},
    h("div", { class: "tb-lg" }, h("span", {}, "Hommes"), h("b", {}, String(stats.sexes.M))),
    barre(pct(stats.sexes.M), "var(--homme)"),
    h("div", { class: "tb-lg" }, h("span", {}, "Femmes"), h("b", {}, String(stats.sexes.F))),
    barre(pct(stats.sexes.F), "var(--femme)"),
    stats.sexes.autre ? h("div", { class: "tb-lg" }, h("span", {}, "Indéterminés"),
      h("b", {}, String(stats.sexes.autre))) : null,
    h("div", { style: "height:6px" }),
    ligneJauge("Naissance connue", stats.avec_naissance + " / " + tot, pct(stats.avec_naissance), "var(--vert-clair)"),
    ligneJauge("Décès connu", stats.avec_deces + " / " + tot, pct(stats.avec_deces), "var(--vert-clair)"),
    sante ? ligneJauge("Faits prouvés par acte", sante.pct_prouves + " %", sante.pct_prouves, "var(--accent)") : null));
  return carte;
}

function ligneJauge(label, valeur, pct, couleur) {
  return h("div", {},
    h("div", { class: "tb-mini" }, h("span", {}, label), h("span", {}, valeur)),
    barre(pct, couleur));
}

function carteRecents() {
  const carte = h("div", { class: "carte" }, h("h2", {}, "🕘 Récemment consultées"));
  const recents = lireRecents();
  if (!recents.length) {
    carte.append(h("div", { class: "vide compacte" },
      "Ouvrez une fiche : elle apparaîtra ici pour un accès rapide."));
    return carte;
  }
  const box = h("div", { class: "liste-pers compacte" });
  recents.slice(0, 6).forEach((p) => box.append(h("div", {
    class: "ligne-pers", onclick: () => aller("personnes", { fiche: p.id }) },
    h("span", { class: "nom" }, p.nom),
    h("span", { class: "meta" }, p.periode || "—"))));
  carte.append(box);
  return carte;
}

function carteSante(sante, anomalies) {
  const carte = h("div", { class: "carte" }, h("h2", {}, "🩺 Santé de l'arbre"));
  carte.append(h("p", { style: "margin:0 0 12px" },
    anomalies
      ? h("span", { class: "badge attention" }, anomalies + " anomalie(s) à voir")
      : h("span", { class: "badge ok" }, "Aucune anomalie 🎉")));
  if (sante) {
    carte.append(
      ligneJauge("Faits prouvés par acte", sante.pct_prouves + " %", sante.pct_prouves, "var(--accent)"),
      ligneJauge("Personnes sans source",
        String(sante.nb_personnes_sans_source),
        Math.round(sante.nb_personnes_sans_source * 100 / (sante.nb_personnes || 1)), "var(--alerte)"));
  }
  carte.append(h("p", { style: "margin:10px 0 0;font-size:13px;color:var(--accent);cursor:pointer",
    onclick: () => aller("sante") }, "Voir la santé complète →"));
  return carte;
}

async function sauvegarder() {
  try {
    const r = await apiJson("/api/espaces/sauvegarde", "POST", {});
    toast("Sauvegarde créée : " + r.fichier);
  } catch (e) { toast(e.message); }
}

export async function vueTableau(vue) {
  const esp = await majEspace(apiGet);
  if (!esp || !esp.ouvert) return accueilVierge(vue);
  if (!esp.personnes) return accueilVide(vue, esp);
  return accueilRempli(vue, esp);
}
