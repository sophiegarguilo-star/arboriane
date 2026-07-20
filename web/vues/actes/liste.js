// Écran « Actes / Sources » — la liste et son tableau de bord.
// Deux sous-vues : « Documents & actes » (avec pièces) et « Toutes les sources ».
import { h, vider } from "../../noyau/dom.js";
import { aller } from "../../noyau/etat.js";
import { apiGet, apiJson } from "../../noyau/api.js";
import { badge } from "../../composants/badge.js";
import { toast } from "../../composants/toast.js";
import { ouvrirModale, fermerModale } from "../../composants/modale.js";
import { STATUTS, STATUT_LABEL, FIAB, exportCsv } from "./commun.js";
import { champPersonne } from "../../composants/champ.js";
import { detail } from "./detail.js";
import { formulaire } from "./formulaire.js";

// « Ranger les pièces » : renomme les scans selon la nomenclature triable
// (date de l'événement en tête), en gardant les citations intactes. Aperçu
// d'abord (cases à cocher), puis application côté serveur (renomme + recite +
// sauvegarde). Le TITRE affiché dans l'app ne change pas — seul le nom disque.
async function ouvrirRangement() {
  const { items } = await apiGet("/api/nomenclature/rangement").catch(() => ({ items: [] }));
  if (!items || !items.length) {
    toast("Toutes vos pièces sont déjà bien nommées 👍"); return;
  }
  const lignes = items.map((it) => {
    it._chk = h("input", { type: "checkbox", checked: "checked" });
    return h("label", { style: "display:flex;gap:8px;align-items:flex-start;padding:7px 0;border-bottom:1px solid var(--bord);font-size:13px" },
      it._chk,
      h("div", { style: "min-width:0" },
        it.titre ? h("div", { style: "color:var(--gris-clair);font-size:12px" }, it.titre) : null,
        h("div", { style: "word-break:break-all" },
          h("span", { style: "color:var(--gris)" }, it.de), " → ", h("strong", {}, it.vers))));
  });
  const contenu = h("div", {},
    h("p", { style: "margin-top:0;font-size:13px" },
      "Renomme les scans avec un nom triable (date de l'événement en tête). "
      + "Le titre dans l'application ne change pas, et le lien avec chaque source "
      + "est conservé. Une sauvegarde est faite avant."),
    h("div", { style: "max-height:50vh;overflow:auto" }, ...lignes),
    h("div", { class: "barre-actions", style: "margin-top:12px" },
      h("button", { class: "bouton", onclick: async (e) => {
        const choisis = items.filter((it) => it._chk.checked)
          .map((it) => ({ de: it.de, vers: it.vers }));
        if (!choisis.length) { toast("Aucune pièce cochée."); return; }
        e.target.disabled = true;
        try {
          const r = await apiJson("/api/nomenclature/rangement", "POST", { items: choisis });
          const n = r.renommes.length, ig = (r.ignores || []).length;
          toast(n + " pièce" + (n > 1 ? "s" : "") + " rangée" + (n > 1 ? "s" : "")
            + (ig ? " · " + ig + " ignorée" + (ig > 1 ? "s" : "") : ""));
          fermerModale(); aller("actes");
        } catch (err) { toast(err.message, { type: "erreur" }); e.target.disabled = false; }
      } }, "🗂️ Ranger les pièces cochées"),
      h("button", { class: "bouton secondaire", onclick: fermerModale }, "Annuler")));
  ouvrirModale(contenu, { titre: "Ranger les pièces (" + items.length + ")", largeur: 640 });
}

let sousVue = "documents";     // documents | toutes
let filtres = { q: "", type: "", statut: "", personne: "", depot: "", orphelins: false, tri: "date" };

export async function vueActes(vue, arg) {
  if (arg && arg.source) { detail(arg.source); return; }
  // Arrivée filtrée sur un dépôt (depuis l'onglet Dépôts) : on n'affiche que ses
  // sources. Sinon on repart sans filtre dépôt (pour ne pas le garder collé).
  filtres.depot = (arg && arg.depot) || "";
  if (filtres.depot) sousVue = "toutes";
  vue.append(h("h1", {}, "Actes / Sources"));
  vue.append(h("p", { class: "sous-titre" },
    "Vos preuves : chaque source (registre, acte, relevé) peut porter un scan, "
    + "une transcription, et prouver des faits sur vos personnes."));

  const data = await apiGet("/api/sources").catch(() => ({ sources: [], types: [] }));

  // tableau de bord — vue d'ensemble du fonds documentaire
  if (data.sources.length) {
    const avecScan = data.sources.filter((s) => s.nb_fichiers > 0).length;
    const sansScan = data.sources.length - avecScan;
    // « reliée » = tag personnes OU citation d'un fait (conscient des preuves).
    const nonReliees = data.sources.filter((s) => !s.reliee).length;
    const stat = (n, lib, alerte) => h("div", { class: "stat" },
      h("strong", { style: alerte && n ? "color:var(--alerte)" : "" }, String(n)),
      h("span", {}, lib));
    vue.append(h("div", { class: "stats", style: "margin-bottom:14px" },
      stat(data.sources.length, "sources"),
      stat(avecScan, "avec scan"),
      stat(sansScan, "sans scan", true),
      stat(nonReliees, "non reliées", true)));
  }

  // sous-onglets
  const onglets = h("div", { class: "barre-actions", style: "margin-bottom:14px" });
  const btn = (cle, lib) => h("button", {
    class: "bouton " + (sousVue === cle ? "" : "secondaire") + " petit",
    onclick: () => { sousVue = cle; aller("actes"); } }, lib);
  onglets.append(btn("documents", "🖼 Documents & actes"), btn("toutes", "📋 Toutes les sources"),
    h("span", { class: "pousse" }),
    h("button", { class: "bouton petit", onclick: () => formulaire(null) }, "➕ Nouvelle source"),
    h("button", { class: "bouton secondaire petit", onclick: ouvrirRangement,
      title: "Renommer les scans avec un nom de fichier triable (date en tête)" }, "🗂️ Ranger les pièces"),
    h("button", { class: "bouton secondaire petit", onclick: () => exportCsv(data.sources) }, "⬇ CSV"));
  vue.append(onglets);

  // filtres
  const barre = h("div", { class: "barre-actions", style: "margin-bottom:12px" });
  const rech = h("input", { type: "search", placeholder: "Rechercher…", value: filtres.q });
  const selType = h("select", {}, h("option", { value: "" }, "Tous les types"),
    ...data.types.map((t) => h("option", { value: t, selected: filtres.type === t ? "selected" : null }, t)));
  const selTri = h("select", {},
    ...[["date", "Trier par date"], ["type", "Par type"], ["titre", "Par titre"]].map(([v, l]) =>
      h("option", { value: v, selected: filtres.tri === v ? "selected" : null }, l)));
  const selStatut = h("select", {}, h("option", { value: "" }, "Tous les statuts"),
    ...STATUTS.map((v) => h("option", { value: v, selected: filtres.statut === v ? "selected" : null },
      STATUT_LABEL[v] || v)));
  const chkOrph = h("label", { style: "display:flex;align-items:center;gap:5px" },
    h("input", { type: "checkbox", checked: filtres.orphelins ? "checked" : null }), "⚠ sans scan");
  // filtre par PERSONNE : ne montrer que les actes/sources qui la citent
  const gens = await apiGet("/api/individus").catch(() => []);
  const champPers = champPersonne(gens, { placeholder: "Filtrer par personne…",
    initial: filtres.personne, onChoix: (pid) => { filtres.personne = pid || ""; rendre(); } });
  const effacerPers = h("button", { class: "lien", style: "font-size:12px",
    onclick: () => { filtres.personne = ""; const i = champPers.element.querySelector("input"); if (i) i.value = ""; rendre(); } }, "✕");
  barre.append(rech, selType, selStatut, selTri, chkOrph,
    h("div", { class: "rangee serre" }, champPers.element, effacerPers));
  vue.append(barre);

  // Bandeau « filtré sur un dépôt » (avec bouton pour l'enlever).
  if (filtres.depot) {
    vue.append(h("div", { class: "barre-actions", style: "margin-bottom:10px" },
      badge("🏛 Dépôt : " + filtres.depot, "info"),
      h("button", { class: "lien", style: "font-size:12px",
        onclick: () => { filtres.depot = ""; rendre(); } }, "✕ enlever le filtre")));
  }

  const zone = h("div", {});
  vue.append(zone);

  function rendre() {
    vider(zone);
    let lst = data.sources.slice();
    if (sousVue === "documents") lst = lst.filter((s) => s.nb_fichiers > 0 || filtres.orphelins);
    const q = filtres.q.trim().toLowerCase();
    if (q) lst = lst.filter((s) => (s.titre + s.lieu + s.cote).toLowerCase().includes(q));
    if (filtres.type) lst = lst.filter((s) => s.type === filtres.type);
    if (filtres.statut) lst = lst.filter((s) => s.statut === filtres.statut);
    if (filtres.personne) lst = lst.filter((s) => (s.personnes || []).includes(filtres.personne));
    if (filtres.depot) lst = lst.filter((s) => (s.depot || "") === filtres.depot);
    if (filtres.orphelins) lst = lst.filter((s) => s.orpheline);
    lst.sort((a, b) => filtres.tri === "titre" ? a.titre.localeCompare(b.titre)
      : filtres.tri === "type" ? (a.type || "").localeCompare(b.type || "")
      : (a.date || "").localeCompare(b.date || ""));

    if (!lst.length) {
      if (sousVue === "documents" && data.sources.length) {
        zone.append(h("div", { class: "vide" },
          h("span", { class: "grand" }, "🖼"),
          h("div", {}, "Aucune source n'a encore de scan rattaché."),
          h("button", { class: "bouton secondaire petit", style: "margin-top:10px",
            onclick: () => { sousVue = "toutes", aller("actes"); } },
            "Voir toutes les sources")));
      } else {
        zone.append(h("div", { class: "vide" }, "Aucune source ne correspond."));
      }
      return;
    }
    // Dans « Documents & actes », les sources SANS scan (dont les preuves créées
    // sans pièce jointe) sont masquées : on le signale, avec un raccourci.
    if (sousVue === "documents" && !filtres.orphelins) {
      const caches = data.sources.filter((s) => !s.nb_fichiers).length;
      if (caches) zone.append(h("div", { style: "margin-bottom:10px;font-size:13px;color:var(--gris)" },
        caches + " source(s) sans scan ne sont pas affichées ici — ",
        h("button", { class: "lien", onclick: () => { sousVue = "toutes"; aller("actes"); } },
          "voir « Toutes les sources »")));
    }
    const grille = h("div", { class: "grille-arbres" });
    lst.forEach((s) => grille.append(carteSource(s)));
    zone.append(grille);
  }

  rech.addEventListener("input", () => { filtres.q = rech.value; rendre(); });
  selType.addEventListener("change", () => { filtres.type = selType.value; rendre(); });
  selStatut.addEventListener("change", () => { filtres.statut = selStatut.value; rendre(); });
  selTri.addEventListener("change", () => { filtres.tri = selTri.value; rendre(); });
  chkOrph.querySelector("input").addEventListener("change", (e) => { filtres.orphelins = e.target.checked; rendre(); });
  rendre();
}

function carteSource(s) {
  return h("div", { class: "carte-arbre", onclick: () => detail(s.id), style: "cursor:pointer" },
    h("div", { class: "nom" }, s.titre),
    h("div", { class: "rangee serre" },
      s.type ? badge(s.type, "info") : null,
      s.fiabilite ? badge("fiabilité " + s.fiabilite, FIAB[s.fiabilite] || "") : null,
      s.statut ? badge(s.statut) : null,
      s.nb_fichiers ? badge("🖼 " + s.nb_fichiers) : badge("⚠ sans scan", "attention"),
      s.a_transcription ? badge("transcription", "ok") : null),
    h("div", { style: "color:var(--gris);font-size:13px" },
      [s.date, s.lieu, s.cote].filter(Boolean).join(" · ") || "—"),
    s.nb_personnes ? h("div", { style: "font-size:12px;color:var(--gris-clair)" },
      "👥 " + s.nb_personnes + " personne(s) citée(s)") : null);
}
