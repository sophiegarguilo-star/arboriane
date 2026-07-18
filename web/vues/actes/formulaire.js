// Formulaire de source — création, modification, et mode « prouver un fait ».
//
// L'ordre des champs suit l'ordre où l'information arrive dans la tête : on sait
// d'abord QUEL acte on tient, puis QUI il concerne, puis QUAND et OÙ. Le TITRE
// vient en dernier, pré-rempli à partir de tout cela : on ne demande pas de
// nommer une chose avant de l'avoir décrite — c'est ainsi qu'on obtient des
// « acte naissance 2 » à la pelle.
//
// Titre et nom de fichier sont deux objets distincts : le titre décrit (il se
// lit dans la liste), le nom de fichier nomme (il se trie dans l'explorateur).
// La règle de nommage vit côté serveur (services/nomenclature.py).
import { h, vider } from "../../noyau/dom.js";
import { aller } from "../../noyau/etat.js";
import { apiGet, apiJson } from "../../noyau/api.js";
import { toast } from "../../composants/toast.js";
import { champSource } from "../../composants/champSource.js";
import { champLieu, chargerLieux } from "../../composants/champLieu.js";
import { STATUTS, STATUT_LABEL, AIDE_SOURCE, TYPES_ACTE } from "./commun.js";
import { blocPersonnes } from "./personnes.js";
import { blocScans } from "./scans.js";
import { detail } from "./detail.js";

// opts.retour = { label, action } : personnalise « Retour » (ex. revenir à une
// fiche). opts.preuve = { pid, fait, libelle, nom, proches, famille } : mode
// « prouver un fait » — le même formulaire, qui crée la source ET la relie au fait.
export async function formulaire(src, opts = {}) {
  const vue = document.getElementById("vue");
  vider(vue);
  const edit = !!src;
  const preuve = opts.preuve || null;
  const retourAction = opts.retour ? opts.retour.action
    : (edit ? () => detail(src.id) : () => aller("actes"));
  const retourLabel = opts.retour ? ("← " + opts.retour.label) : "← Retour";
  vue.append(h("button", { class: "bouton secondaire petit",
    onclick: () => { nettoyerAbandon(); retourAction(); } }, retourLabel));
  vue.append(h("h1", {}, edit ? "Modifier la source"
    : (preuve ? "Prouver : " + preuve.libelle : "Nouvelle source")));
  src = src || {};

  // Les scans déposés ici puis abandonnés (annulation / retour) sont effacés du
  // disque par le bloc « pièces jointes » — sauf si la source a été enregistrée.
  let enregistre = false;
  function nettoyerAbandon() {
    if (!enregistre) blocFichiers.nettoyerAbandon();
  }

  const champs = {};
  const lieux = await chargerLieux(apiGet);
  const personnes = await apiGet("/api/individus").catch(() => []);
  const carte = h("div", { class: "carte", style: "max-width:680px" });

  // ── 1. Type d'acte — la première chose qu'on sait ─────────────────────
  const typeConnu = !src.type || TYPES_ACTE.includes(src.type);
  const selType = h("select", { style: "width:100%" },
    h("option", { value: "", selected: !src.type ? "selected" : null }, "— (à préciser)"),
    ...TYPES_ACTE.map((t) => h("option", { value: t, selected: src.type === t ? "selected" : null }, t)),
    h("option", { value: "__autre__", selected: !typeConnu ? "selected" : null },
      "Autre (à préciser)…"));
  // Champ libre affiché quand « Autre… » est choisi : permet un type personnalisé
  // (ex. « Acte de baptême protestant », « Contrat de mariage »…).
  const inAutre = h("input", {
    style: "width:100%;margin-top:6px;" + (typeConnu ? "display:none" : ""),
    placeholder: "Votre type d'acte…", value: typeConnu ? "" : src.type });
  selType.addEventListener("change", () => {
    inAutre.style.display = selType.value === "__autre__" ? "" : "none";
    if (selType.value === "__autre__") inAutre.focus();
  });
  champs.type = selType;
  // Valeur réelle du type : le champ libre si « Autre… », sinon l'option choisie.
  const lireType = () => (selType.value === "__autre__" ? inAutre.value.trim() : selType.value);
  carte.append(h("div", { class: "champ" }, h("label", {}, "Type d'acte"), selType, inAutre));

  // ── 2. Personnes citées — l'indexation, au moment où l'on y pense ─────
  // En modification, on repart des personnes déjà citées : le formulaire les
  // réécrit en bloc à l'enregistrement, donc il doit les connaître.
  const blocGens = blocPersonnes(personnes, {
    presets: edit ? (src.personnes || []) : (preuve ? (preuve.proches || []) : []),
    libelle: preuve ? "Autres personnes concernées par cette source"
                    : "Personnes citées par cette source",
    aide: preuve && preuve.fait === "union"
      ? "Les deux conjoint·es sont couvert·es automatiquement — la preuve d'union "
        + "est portée par la famille. Ajoutez ici les autres personnes citées (témoins…)."
      : "Qui cet acte cite-t-il ? Rattachez-le à toutes les personnes concernées "
        + "(l'enfant et ses parents, tout un foyer au recensement, les témoins…).",
    onChange: () => rafraichir(),
  });
  carte.append(blocGens.element);

  // ── 3. Quand, où, et la référence aux archives ────────────────────────
  const champLieuSrc = champLieu(lieux, { valeur: src.lieu || "" });
  const depotsData = await apiGet("/api/depots").catch(() => ({ depots: [] }));
  const depots = depotsData.depots || [];
  let depotInit = "";
  if (src.depot_id && depots.some((d) => d.id === src.depot_id)) depotInit = src.depot_id;
  else if ((src.depot || "").trim()) {
    const m = depots.find((d) => (d.nom || "").toLowerCase() === src.depot.trim().toLowerCase());
    depotInit = m ? m.id : "__autre__";
  }
  const inpDepotLibre = h("input", {
    value: (depotInit === "__autre__" ? (src.depot || "") : ""),
    placeholder: "Nom du dépôt (ex. Archives départementales du Nord)", style: "width:100%;margin-top:6px" });
  const selDepot = h("select", { style: "width:100%" },
    h("option", { value: "", selected: depotInit === "" ? "selected" : null }, "— (aucun)"),
    ...depots.map((d) => h("option", { value: d.id,
      selected: depotInit === d.id ? "selected" : null }, d.nom || d.id)),
    h("option", { value: "__autre__", selected: depotInit === "__autre__" ? "selected" : null },
      "✏️ Autre / saisir un nom…"));
  function majDepotLibre() { inpDepotLibre.style.display = selDepot.value === "__autre__" ? "block" : "none"; }
  selDepot.addEventListener("change", majDepotLibre);
  majDepotLibre();

  [["date", "Date"], ["lieu", "Lieu"], ["depot", "Dépôt"], ["cote", "Cote"],
   ["page", "Page"], ["ark", "Lien vers l'acte en ligne (ARK / URL)"]].forEach(([cle, lib]) => {
    if (cle === "lieu") {
      carte.append(h("div", { class: "champ" }, h("label", {}, lib), champLieuSrc.element));
      return;
    }
    if (cle === "depot") {
      carte.append(h("div", { class: "champ" }, h("label", {}, lib), selDepot, inpDepotLibre));
      return;   // géré à part (entité depot_id + saisie libre)
    }
    const inp = h("input", { value: src[cle] || "", style: "width:100%",
      placeholder: AIDE_SOURCE[cle] || "" });
    champs[cle] = inp;
    carte.append(h("div", { class: "champ" }, h("label", {}, lib), inp));
  });

  const selFiab = h("select", {}, ...[["", "—"], ["haute", "haute"], ["moyenne", "moyenne"], ["basse", "basse"]]
    .map(([v, l]) => h("option", { value: v, selected: src.fiabilite === v ? "selected" : null }, l)));
  const selStatut = h("select", { title: "Où en est cette source dans votre recherche." },
    ...["", ...STATUTS].map((v) => h("option", { value: v,
      selected: src.statut === v ? "selected" : null }, v ? (STATUT_LABEL[v] || v) : "—")));
  champs.fiabilite = selFiab; champs.statut = selStatut;
  carte.append(h("div", { style: "display:flex;gap:12px" },
    h("div", { class: "champ" }, h("label", {}, "Fiabilité"), selFiab),
    h("div", { class: "champ" }, h("label", {}, "Statut"), selStatut)));

  // ── 4. Scans, et leur nom sur le disque ──────────────────────────────
  const blocFichiers = blocScans(src.fichiers || [], { onChange: () => rafraichir() });
  carte.append(blocFichiers.element);

  // Renommage : proposé, jamais imposé — ce sont les fichiers de l'utilisateur,
  // et certains dépôts imposent déjà leur propre convention (« 5Mi123_4_vue42 »).
  const chkRenommer = h("input", { type: "checkbox", checked: "checked" });
  const listeRenommage = h("div", { style: "font-size:12px;color:var(--gris);margin-top:6px" });
  const blocRenommage = h("div", { class: "champ", style: "display:none" },
    h("label", { style: "display:flex;gap:7px;align-items:center;font-weight:normal" },
      chkRenommer, "Renommer les scans selon la nomenclature Arboriane"),
    listeRenommage);
  chkRenommer.addEventListener("change", () => rendreRenommage());
  carte.append(blocRenommage);

  // ── 5. Titre — construit, en dernier ─────────────────────────────────
  let titreTouche = edit && !!(src.titre || "").trim();   // on n'écrase jamais un titre existant
  const inpTitre = h("input", { value: src.titre || "", style: "width:100%",
    placeholder: "Se remplit tout seul à partir du type, des personnes, de la date et du lieu" });
  champs.titre = inpTitre;
  const btnReprendre = h("button", { class: "bouton fantome petit", style: "display:none",
    onclick: () => { titreTouche = false; btnReprendre.style.display = "none"; rafraichir(); } },
    "↺ Reprendre la suggestion");
  inpTitre.addEventListener("input", () => {
    titreTouche = true;
    btnReprendre.style.display = "inline-block";
  });
  carte.append(h("div", { class: "champ" },
    h("div", { style: "display:flex;align-items:baseline;gap:8px;justify-content:space-between" },
      h("label", { style: "margin:0" }, "Titre"), btnReprendre),
    inpTitre,
    h("p", { style: "color:var(--gris-clair);font-size:12px;margin:4px 0 0" },
      "Le titre décrit la source dans vos listes. Le nom du fichier, lui, sert à "
      + "ranger le scan sur votre disque : ce sont deux choses différentes.")));

  const transSrc = h("textarea", { rows: 6, style: "width:100%",
    placeholder: "Transcription de l'acte…" }, src.transcription || "");
  carte.append(h("div", { class: "champ" }, h("label", {}, "Transcription"), transSrc));

  // ── Nomenclature : le serveur propose, l'écran affiche ───────────────
  let propositions = [];              // [{origine, propose}] pour les scans AJOUTÉS ici
  function personnesChoisies() {
    const ids = preuve ? [preuve.pid] : [];   // le sujet du fait est toujours cité
    blocGens.valeurs().forEach((p) => { if (!ids.includes(p.id)) ids.push(p.id); });
    return ids;
  }
  function rendreRenommage() {
    const neufs = blocFichiers.ajoutes();
    blocRenommage.style.display = neufs.length ? "block" : "none";
    vider(listeRenommage);
    if (!neufs.length) return;
    if (!chkRenommer.checked) {
      listeRenommage.append(h("div", {}, "Les scans garderont leur nom d'origine."));
      return;
    }
    propositions.forEach((p) => listeRenommage.append(
      h("div", {}, p.origine, " → ", h("strong", {}, p.propose))));
    if (edit && blocFichiers.fichiers().length > neufs.length) {
      listeRenommage.append(h("div", { style: "margin-top:4px;color:var(--gris-clair)" },
        "Les scans déjà enregistrés ne sont pas renommés : une source les cite déjà."));
    }
  }
  let minuterie = null;
  let demande = 0;              // deux appels peuvent se croiser : seul le dernier compte
  function rafraichir() {                       // appelée à chaque frappe : on temporise
    clearTimeout(minuterie);
    minuterie = setTimeout(demanderNomenclature, 250);
  }
  async function demanderNomenclature() {
    const mien = ++demande;
    let r;
    try {
      r = await apiJson("/api/nomenclature", "POST", {
        type: lireType(), personnes: personnesChoisies(),
        date: champs.date.value.trim(), lieu: champLieuSrc.valeur(),
        fichiers: blocFichiers.ajoutes() });
    } catch { return; }                          // suggestion de confort : jamais bloquante
    if (mien !== demande) return;                // une saisie plus récente a déjà répondu
    propositions = r.fichiers || [];
    if (!titreTouche) inpTitre.value = r.titre || "";
    rendreRenommage();
  }
  selType.addEventListener("change", rafraichir);
  champs.date.addEventListener("input", rafraichir);
  // Le champ Lieu remplit son input sans émettre d'événement quand on clique une
  // suggestion : on écoute donc aussi le clic (qui remonte du menu) et le blur.
  ["input", "click", "blur"].forEach((e) =>
    champLieuSrc.element.addEventListener(e, rafraichir, true));
  rafraichir();

  // Renomme les scans ajoutés ici, juste avant d'enregistrer la source : à ce
  // moment seulement le type, la date et les personnes sont connus.
  async function appliquerRenommage() {
    if (!chkRenommer.checked || !blocFichiers.ajoutes().length) return;
    clearTimeout(minuterie);        // sinon une frappe en attente périmerait cette demande
    await demanderNomenclature();
    for (const p of propositions) {
      if (p.propose === p.origine) continue;
      try {
        const r = await apiJson("/api/media/Sources/renommer", "POST",
          { de: p.origine, vers: p.propose });
        blocFichiers.renomme(p.origine, r.fichier);
      } catch { /* le scan garde son nom : ce n'est pas une raison de tout perdre */ }
    }
  }

  function lireCorps() {
    const corps = {};
    Object.entries(champs).forEach(([k, el]) => corps[k] = el.value.trim());
    corps.type = lireType();              // « Autre… » -> type personnalisé saisi
    corps.lieu = champLieuSrc.valeur();   // lieu avec autocomplétion
    // dépôt : entité choisie (depot_id + nom synchronisé) ou saisie libre
    const dv = selDepot.value;
    if (dv === "__autre__") { corps.depot = inpDepotLibre.value.trim(); corps.depot_id = ""; }
    else if (dv) { const d = depots.find((x) => x.id === dv); corps.depot = d ? (d.nom || "") : ""; corps.depot_id = dv; }
    else { corps.depot = ""; corps.depot_id = ""; }
    corps.fichiers = blocFichiers.fichiers();
    corps.transcription = transSrc.value.trim();
    // personnes citées : réécrites en bloc, donc jamais de doublon de rôle
    corps.personnes = blocGens.valeurs();
    return corps;
  }

  // ── Mode « prouver un fait » : source existante OU nouvelle ───────────
  if (preuve) {
    const sourcesExist = (await apiGet("/api/sources").catch(() => ({ sources: [] }))).sources || [];
    // Sélecteur de source CHERCHABLE (autocomplétion par titre) au lieu d'un menu
    // déroulant de toutes les sources — utilisable avec des milliers d'entrées.
    const pickSource = champSource(sourcesExist, {});
    const blocEx = h("div", { class: "carte", style: "max-width:680px;display:none" },
      h("div", { class: "champ" }, h("label", {}, "Source déjà créée"), pickSource.element));
    let mode = "nouvelle";
    const majMode = () => {
      carte.style.display = mode === "nouvelle" ? "block" : "none";
      blocEx.style.display = mode === "existante" ? "block" : "none";
    };
    const radio = (val, txt) => h("label", { style: "display:flex;gap:6px;align-items:center" },
      h("input", { type: "radio", name: "modesrc", checked: mode === val ? "checked" : null,
        disabled: (val === "existante" && !sourcesExist.length) ? "disabled" : null,
        onchange: () => { mode = val; majMode(); } }), txt);
    vue.append(h("div", { class: "barre-actions", style: "max-width:680px;gap:20px;margin-bottom:10px" },
      radio("nouvelle", "Nouvelle source"), radio("existante", "Relier une source existante")));
    vue.append(carte, blocEx);

    const selQ = h("select", {},
      h("option", { value: "3" }, "Prouvé par acte (fiable)"),
      h("option", { value: "2" }, "Déclaré"),
      h("option", { value: "1" }, "Estimé"));
    vue.append(h("div", { class: "carte", style: "max-width:680px" },
      h("div", { class: "champ", style: "max-width:300px" },
        h("label", {}, "Fiabilité de la preuve"), selQ)));

    vue.append(h("div", { class: "barre-actions", style: "max-width:680px" },
      h("button", { class: "bouton", onclick: async () => {
        try {
          let sid;
          if (mode === "existante") {
            const s0 = pickSource.valeur();
            if (!s0) { toast("Choisissez une source."); return; }
            sid = s0; nettoyerAbandon();      // scans éventuels non utilisés
          } else {
            await appliquerRenommage();
            const corps = lireCorps();
            if (!corps.titre) { toast("Donnez au moins un titre à la source."); return; }
            // le sujet du fait est toujours cité par la source qui le prouve
            if (!corps.personnes.some((p) => p.id === preuve.pid)) {
              corps.personnes.unshift({ id: preuve.pid, role: "sujet" });
            }
            const r = await apiJson("/api/sources", "POST", corps); sid = r.id; enregistre = true;
          }
          // prouver le fait pour la personne de départ (union ciblée si besoin)
          await apiJson("/api/individus/" + preuve.pid + "/citer", "POST",
            { fait: preuve.fait, source: sid, quay: +selQ.value, famille: preuve.famille || "" });
          if (mode === "existante") {
            // La source existe déjà et peut citer d'autres personnes : on ajoute
            // les nôtres sans réécrire les siennes.
            const tags = [{ id: preuve.pid, role: "sujet" }].concat(blocGens.valeurs());
            const vus = new Set();
            for (const t of tags) {
              if (vus.has(t.id)) continue;
              vus.add(t.id);
              await apiJson("/api/sources/" + sid + "/personne", "POST", t).catch(() => {});
            }
          }
          toast("Preuve ajoutée.");
          retourAction();
        } catch (e) { toast(e.message); }
      } }, "Enregistrer et lier au fait"),
      h("button", { class: "bouton secondaire",
        onclick: () => { nettoyerAbandon(); retourAction(); } }, "Annuler")));
    return;
  }

  // ── Mode normal (écran Actes / Sources) ──
  vue.append(carte);
  vue.append(h("div", { class: "barre-actions", style: "max-width:680px" },
    h("button", { class: "bouton", onclick: async () => {
      try {
        await appliquerRenommage();
        const corps = lireCorps();
        if (!corps.titre) { toast("Donnez au moins un titre."); return; }
        if (edit) {
          await apiJson("/api/sources/" + src.id, "PUT", corps);
          enregistre = true; toast("Source modifiée."); retourAction();
        } else {
          const r = await apiJson("/api/sources", "POST", corps);
          enregistre = true; toast("Source créée.");
          opts.retour ? retourAction() : detail(r.id);
        }
      } catch (e) { toast(e.message); }
    } }, "Enregistrer"),
    h("button", { class: "bouton secondaire",
      onclick: () => { nettoyerAbandon(); retourAction(); } }, "Annuler")));
}
