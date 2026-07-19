// Personnes — formulaire de création / édition (identité principale + détaillée,
// faits de vie, recherche & confidentialité, note biographique).
//
// Écran UNIFIÉ : le même formulaire sert à « Nouvelle personne » ET à l'ajout
// d'un proche depuis une fiche. Un bloc « Lien de parenté » en tête permet, à la
// création, de rattacher la personne (père, mère, conjoint·e, enfant, frère/sœur)
// — pré-rempli quand on vient d'un bouton de fiche, « à déterminer » sinon — et
// de CRÉER une nouvelle personne complète ou de RELIER quelqu'un déjà dans l'arbre.
import { h, vider } from "../../noyau/dom.js";
import { aller, peutRevenir, retour as retourHistorique, gardeSaisie } from "../../noyau/etat.js";
import { apiGet, apiJson } from "../../noyau/api.js";
import { toast } from "../../composants/toast.js";
import { champDate } from "../../composants/champDate.js";
import { champLieu, chargerLieux } from "../../composants/champLieu.js";
import { champPersonne } from "../../composants/champ.js";
import { listeRepetable } from "../../composants/listeRepetable.js";
import { boutonMicro } from "../../composants/micro.js";
import { SEXES, TYPES_NOM, RESN, EVT_GROUPES, tagEvt, ligneChamp, blocAvance } from "./commun.js";

const LIBELLE_TITRE = {
  pere: "Ajouter le père", mere: "Ajouter la mère",
  conjoint: "Ajouter un·e conjoint·e", enfant: "Ajouter un enfant",
  fratrie: "Ajouter un frère / une sœur",
};

const OPTIONS_LIEN = [
  ["", "— à déterminer / personne isolée —"],
  ["pere", "le père de"],
  ["mere", "la mère de"],
  ["conjoint", "le·la conjoint·e de"],
  ["enfant", "un enfant de"],
  ["fratrie", "un frère ou une sœur de"],
];

export async function vueFormulaire(vue, { editer, lien } = {}) {
  let ind = { sexe: "U", naissance: {}, deces: {} };
  if (editer) {
    try { ind = await apiGet("/api/individus/" + editer); } catch { /* neuf */ }
  }
  const lieux = await chargerLieux(apiGet);
  // Liste des personnes (pour les autocomplétions ancre + « relier ») — seulement
  // en création.
  const liste = editer ? [] : await apiGet("/api/individus").catch(() => []);

  // Retour à l'écran précédent (historique). Repli : en édition → la fiche
  // éditée ; en création depuis une fiche → la fiche ancre ; sinon la liste.
  // Le bouton est TOUJOURS affiché (avant, il manquait en mode édition → « Annuler »
  // renvoyait à la liste au lieu de la fiche).
  const repliArg = editer ? { fiche: editer }
    : ((lien && lien.ancre) ? { fiche: lien.ancre } : null);
  const retour = () => (peutRevenir() ? retourHistorique() : aller("personnes", repliArg));
  vue.append(h("button", { class: "bouton secondaire petit", onclick: retour }, "← Retour"));

  // Garde « modifications non enregistrées » (UX-02) : toute saisie arme le
  // garde du routeur ; un enregistrement réussi le désarme (gardeSaisie(null)).
  let saisieModifiee = false;
  vue.addEventListener("input", () => { saisieModifiee = true; });
  vue.addEventListener("change", () => { saisieModifiee = true; });
  gardeSaisie(() => saisieModifiee);
  const titre = editer ? "Modifier une personne"
    : (LIBELLE_TITRE[lien && lien.type] || "Nouvelle personne");
  vue.append(h("h1", {}, titre));

  // ── Identité principale ────────────────────────────────────────────────
  const fNom = h("input", { value: ind.nom || "", style: "width:100%" });
  const fPrenoms = h("input", { value: ind.prenoms || "", style: "width:100%" });
  const fSexe = h("select", {}, ...SEXES.map(([v, l]) =>
    h("option", { value: v, selected: ind.sexe === v ? "selected" : null }, l)));

  // Statut de vie : auto / vivant / décédé (pilote la clé `vivant`)
  const statutInit = ind.vivant === true ? "vivant" : (ind.vivant === false ? "decede" : "auto");
  const fStatut = h("select", { title: "« Déduit automatiquement » : Arboriane considère la "
    + "personne décédée si un décès est connu ou si sa naissance est très ancienne "
    + "(plus d'environ 110 ans), sinon vivante. Forcez « Vivant·e » ou « Décédé·e » au besoin." },
    h("option", { value: "auto", selected: statutInit === "auto" ? "selected" : null }, "Déduit automatiquement"),
    h("option", { value: "vivant", selected: statutInit === "vivant" ? "selected" : null }, "Vivant·e"),
    h("option", { value: "decede", selected: statutInit === "decede" ? "selected" : null }, "Décédé·e"));

  // Dates & lieux (composants GEDCOM)
  const dNais = champDate((ind.naissance || {}).date || "");
  const lNais = champLieu(lieux, { valeur: (ind.naissance || {}).lieu || "" });
  const dDec = champDate((ind.deces || {}).date || "");
  const lDec = champLieu(lieux, { valeur: (ind.deces || {}).lieu || "" });

  const fCause = h("input", { value: (ind.deces || {}).cause || "",
    placeholder: "cause du décès (facultatif)", style: "width:100%" });
  // Heure du fait (facultative) : texte libre pour tolérer « 14:30 » comme
  // « trois heures du matin » (fréquent dans les actes anciens).
  const fHeureNais = h("input", { value: (ind.naissance || {}).heure || "",
    placeholder: "heure (facultatif, ex. 14:30)", style: "width:100%" });
  const fHeureDec = h("input", { value: (ind.deces || {}).heure || "",
    placeholder: "heure (facultatif, ex. 4:00)", style: "width:100%" });
  const blocDeces = h("div", {},
    ligneChamp("Décès — date", dDec.element),
    ligneChamp("Décès — heure", fHeureDec),
    ligneChamp("Décès — lieu", lDec.element),
    ligneChamp("Décès — cause", fCause));
  function majDeces() {
    // on masque le décès seulement si la personne est explicitement vivante
    blocDeces.style.display = fStatut.value === "vivant" ? "none" : "block";
  }
  fStatut.addEventListener("change", majDeces); majDeces();

  const principal = h("div", { class: "carte" },
    h("h2", { style: "margin-top:0" }, "Identité principale"),
    ligneChamp("Nom de famille", fNom),
    ligneChamp("Prénom(s)", fPrenoms),
    h("div", { style: "display:flex;gap:12px;flex-wrap:wrap" },
      ligneChamp("Sexe", fSexe),
      h("div", { class: "champ", style: "flex:1;min-width:180px" }, h("label", {}, "Statut de vie"), fStatut)),
    ligneChamp("Naissance — date", dNais.element),
    ligneChamp("Naissance — heure", fHeureNais),
    ligneChamp("Naissance — lieu", lNais.element),
    blocDeces);

  // ── P1 · Identité détaillée ────────────────────────────────────────────
  const fPrefixe = h("input", { value: ind.nom_prefixe || "", placeholder: "Dr, Me, Rév., Cpt…", style: "width:100%" });
  const fSuffixe = h("input", { value: ind.nom_suffixe || "", placeholder: "Jr, III, aîné, cadet…", style: "width:100%" });
  const fParticule = h("input", { value: ind.nom_particule || "", placeholder: "de, du, van…", style: "width:100%" });
  const fUsuel = h("input", { value: ind.prenom_principal || "", placeholder: "prénom d'usage", style: "width:100%" });
  const fSecondaires = h("input", { value: ind.prenoms_secondaires || "", placeholder: "autres prénoms", style: "width:100%" });
  const fSurnom = h("input", { value: ind.surnom || "", placeholder: "« dit … »", style: "width:100%" });
  const fMarital = h("input", { value: ind.nom_marital || "", placeholder: "nom d'épouse / d'époux", style: "width:100%" });

  const variantes = listeRepetable({
    ajouterLabel: "+ Ajouter une variante",
    valeurs: ind.noms_alternatifs || [],
    creerLigne(v) {
      const p = h("input", { value: v.prenoms || "", placeholder: "prénoms", style: "width:100%" });
      const n = h("input", { value: v.nom || "", placeholder: "nom", style: "width:100%" });
      const t = h("select", {}, ...TYPES_NOM.map(([val, lib]) =>
        h("option", { value: val, selected: (v.type || "aka") === val ? "selected" : null }, lib)));
      return {
        element: h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;align-items:center" },
          h("div", { style: "flex:1;min-width:120px" }, p), h("div", { style: "flex:1;min-width:120px" }, n),
          h("div", { style: "width:150px" }, t)),
        lire() {
          const pr = p.value.trim(), no = n.value.trim();
          if (!pr && !no) return null;
          return { prenoms: pr, nom: no, type: t.value };
        },
      };
    },
  });

  const blocIdentite = blocAvance("Identité détaillée — particule, préfixe, prénom usuel, surnom, variantes",
    h("div", { style: "display:flex;gap:12px;flex-wrap:wrap" },
      h("div", { class: "champ", style: "flex:1;min-width:150px" }, h("label", {}, "Préfixe (titre)"), fPrefixe),
      h("div", { class: "champ", style: "flex:1;min-width:150px" }, h("label", {}, "Suffixe (Jr, III…)"), fSuffixe)),
    ligneChamp("Particule du nom", fParticule),
    ligneChamp("Prénom usuel", fUsuel),
    ligneChamp("Prénoms secondaires", fSecondaires),
    ligneChamp("Surnom (« dit »)", fSurnom),
    ligneChamp("Nom marital", fMarital),
    ligneChamp("Variantes / autres noms", variantes.element));

  // ── P3 · Faits de vie ──────────────────────────────────────────────────
  const professions = listeRepetable({
    ajouterLabel: "+ Ajouter une profession",
    valeurs: ind.professions || [],
    creerLigne(v) {
      const inp = h("input", { value: v.valeur || "", placeholder: "ex. cultivateur", style: "width:100%" });
      return { element: inp, lire: () => inp.value.trim() ? { valeur: inp.value.trim() } : null };
    },
  });

  const residences = listeRepetable({
    ajouterLabel: "+ Ajouter une résidence",
    valeurs: ind.residences || [],
    creerLigne(v) {
      const d = champDate(v.date || "");
      const l = champLieu(lieux, { valeur: v.lieu || "" });
      return {
        element: h("div", {},
          h("div", { style: "margin-bottom:6px" }, d.element), l.element),
        lire() {
          const date = d.valeur(), lieu = l.valeur();
          if (!date && !lieu) return null;
          const r = { date, lieu };
          if (v.type) r.type = v.type;   // on préserve un éventuel type importé
          return r;
        },
      };
    },
  });

  const evenements = listeRepetable({
    ajouterLabel: "+ Ajouter un événement / fait",
    valeurs: ind.evenements || [],
    creerLigne(v) {
      const tagCourant = tagEvt(v);
      const sel = h("select", { style: "width:100%" },
        h("option", { value: "" }, "— type —"),
        ...EVT_GROUPES.map(([grp, opts]) =>
          h("optgroup", { label: grp }, ...opts.map(([tag, lib]) =>
            h("option", { value: tag, selected: tagCourant === tag ? "selected" : null }, lib)))));
      const val = h("input", { value: v.valeur || "", placeholder: "valeur / précision (facultatif)", style: "width:100%" });
      const d = champDate(v.date || "");
      const l = champLieu(lieux, { valeur: v.lieu || "" });
      return {
        element: h("div", {},
          h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px" },
            h("div", { style: "width:200px" }, sel), h("div", { style: "flex:1;min-width:160px" }, val)),
          h("div", { style: "margin-bottom:6px" }, d.element), l.element),
        lire() {
          if (!sel.value) return null;
          // « EVEN::<intitulé> » (faits militaires) -> type EVEN + precision, pour
          // un export GEDCOM standard « 1 EVEN … / 2 TYPE <intitulé> ».
          if (sel.value.startsWith("EVEN::")) {
            return { type: "EVEN", precision: sel.value.slice(6),
                     date: d.valeur(), lieu: l.valeur(), valeur: val.value.trim() };
          }
          const e = { type: sel.value, date: d.valeur(), lieu: l.valeur(), valeur: val.value.trim() };
          if (v.precision) e.precision = v.precision;   // conserve une précision existante (ex. PACS)
          return e;
        },
      };
    },
  });

  const blocFaits = blocAvance("Faits de vie — événements, professions, résidences",
    ligneChamp("Événements & attributs", evenements.element),
    ligneChamp("Professions", professions.element),
    ligneChamp("Résidences", residences.element));

  // ── P4 · Recherche & confidentialité ───────────────────────────────────
  const fTags = h("input", { value: (ind.tags || []).join(", "),
    placeholder: "mots-clés séparés par des virgules", style: "width:100%" });
  const fRefn = h("input", { value: ind.refn || "", placeholder: "référence perso / n° de dossier", style: "width:100%" });
  const fResn = h("select", { title: "Qui voit cette personne lors d'un partage : "
    + "Public (visible) · Confidentiel / Privé (masquée dans un export public) · "
    + "Verrouillé (fiche protégée contre les modifications de masse)." },
    ...RESN.map(([val, lib]) =>
      h("option", { value: val, selected: (ind.resn || "") === val ? "selected" : null }, lib)));

  const pistes = listeRepetable({
    ajouterLabel: "+ Ajouter une piste",
    valeurs: (ind.pistes || []).map((p) => (typeof p === "string" ? { texte: p } : p)),
    creerLigne(v) {
      const inp = h("input", { value: v.texte || v.libelle || "", placeholder: "acte à retrouver, hypothèse…", style: "width:100%" });
      return { element: inp, lire: () => inp.value.trim() ? { texte: inp.value.trim() } : null };
    },
  });

  const blocRecherche = blocAvance("Recherche & confidentialité — tags, pistes, référence, accès",
    ligneChamp("Tags", fTags),
    ligneChamp("Pistes de recherche", pistes.element),
    h("div", { style: "display:flex;gap:12px;flex-wrap:wrap" },
      h("div", { class: "champ", style: "flex:1;min-width:180px" }, h("label", {}, "Référence personnelle"), fRefn),
      h("div", { class: "champ", style: "min-width:180px" }, h("label", {}, "Confidentialité"), fResn)));

  // ── Note ───────────────────────────────────────────────────────────────
  const fNote = h("textarea", { rows: 4, style: "width:100%",
    placeholder: "Note biographique (facultatif)" }, ind.note || "");
  const microNote = boutonMicro(fNote);   // null si dictée non supportée
  const blocNote = h("div", { class: "carte" },
    h("h2", { style: "margin-top:0" }, "Note biographique"), ligneChamp("Note", fNote),
    microNote ? h("div", { class: "barre-actions" }, microNote) : null);

  // Sections de création regroupées : masquables en mode « relier ».
  const zoneCreer = h("div", {}, principal, blocIdentite, blocFaits, blocRecherche, blocNote);

  function collecter() {
    // on préserve les citations (preuves) et données existantes des faits
    // vitaux : on ne remplace que date / lieu / cause.
    const nais = { ...(ind.naissance || {}), date: dNais.valeur(), lieu: lNais.valeur(),
                   heure: fHeureNais.value.trim() };
    const dec = { ...(ind.deces || {}), date: dDec.valeur(), lieu: lDec.valeur(),
                  cause: fCause.value.trim(), heure: fHeureDec.value.trim() };
    const champs = {
      nom: fNom.value.trim(), prenoms: fPrenoms.value.trim(), sexe: fSexe.value,
      naissance: nais,
      deces: dec,
      nom_particule: fParticule.value.trim(),
      nom_prefixe: fPrefixe.value.trim(),
      nom_suffixe: fSuffixe.value.trim(),
      prenom_principal: fUsuel.value.trim(),
      prenoms_secondaires: fSecondaires.value.trim(),
      surnom: fSurnom.value.trim(),
      nom_marital: fMarital.value.trim(),
      noms_alternatifs: variantes.valeur(),
      professions: professions.valeur(),
      residences: residences.valeur(),
      evenements: evenements.valeur(),
      tags: fTags.value.split(",").map((t) => t.trim()).filter(Boolean),
      pistes: pistes.valeur(),
      refn: fRefn.value.trim(),
      resn: fResn.value,
      note: fNote.value.trim(),
      vivant: fStatut.value === "vivant" ? true : (fStatut.value === "decede" ? false : null),
    };
    return champs;
  }

  // ── Bloc « Lien de parenté » (création uniquement) ──────────────────────
  const ancreFixe = !!(lien && lien.ancre);
  const selLien = h("select", { style: "min-width:200px" },
    ...OPTIONS_LIEN.map(([v, l]) =>
      h("option", { value: v, selected: (lien && lien.type) === v ? "selected" : null }, l)));
  const ancrePicker = champPersonne(liste, {
    placeholder: "Choisir la personne…",
    initial: ancreFixe ? lien.ancre : "",
    onChoix: () => { majLien(); },
  });
  const relierPicker = champPersonne(liste, { placeholder: "Rechercher la personne à relier…" });
  const zoneAncre = h("span", { style: "display:inline-flex;align-items:center;gap:8px;flex-wrap:wrap" });
  const zoneUnion = h("div", { style: "margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap" });
  let selUnion = null;
  let modeRelier = false;

  const btnCreer = h("button", { class: "bouton petit", onclick: () => { modeRelier = false; majLien(); } },
    "Créer une nouvelle personne");
  const btnRelier = h("button", { class: "bouton secondaire petit", onclick: () => { modeRelier = true; majLien(); } },
    "Relier une personne existante");
  const zoneMode = h("div", { style: "display:none;margin-top:12px" },
    h("div", { style: "display:flex;gap:8px;flex-wrap:wrap" }, btnCreer, btnRelier));

  const zoneRelier = h("div", { style: "display:none" },
    h("div", { class: "carte" },
      h("h2", { style: "margin-top:0" }, "Relier une personne déjà dans l'arbre"),
      ligneChamp("Personne", relierPicker.element)));

  selLien.addEventListener("change", () => majLien());

  // Arbre encore vide (toute première personne) : aucun lien possible, on masque
  // le bloc plutôt que d'afficher un sélecteur sans personne à relier.
  const carteLien = (editer || !liste.length) ? null : h("div", { class: "carte" },
    h("h2", { style: "margin-top:0" }, "Lien de parenté"),
    h("div", { style: "display:flex;flex-wrap:wrap;align-items:center;gap:10px" },
      h("span", { style: "color:var(--gris)" }, "Cette personne est"), selLien, zoneAncre),
    zoneUnion, zoneMode,
    h("p", { style: "margin:10px 0 0;color:var(--gris-clair);font-size:13px" },
      ancreFixe ? "Pré-rempli d'après le bouton d'où tu viens — tu peux changer le lien."
        : "Laisse « à déterminer » pour une personne isolée, ou choisis un lien et la personne concernée."));

  const unionsCache = {};
  async function unionsDe(pid) {
    if (!pid) return [];
    if (!unionsCache[pid]) {
      const f = await apiGet("/api/individus/" + pid).catch(() => null);
      unionsCache[pid] = (f && f.unions) || [];
    }
    return unionsCache[pid];
  }

  async function majLien() {
    const type = selLien.value;
    const ancre = ancreFixe ? lien.ancre : ancrePicker.valeur();
    // Ancre : figée (puce) si on vient d'une fiche, sinon autocomplétion.
    vider(zoneAncre);
    if (type) {
      zoneAncre.append(h("span", { style: "color:var(--gris)" }, "de"));
      if (ancreFixe) zoneAncre.append(h("span", { class: "puce-pers" }, lien.ancreNom || "cette personne"));
      else zoneAncre.append(ancrePicker.element);
    }
    // Sous-choix d'union pour un enfant (réutilise le ciblage d'union).
    vider(zoneUnion); selUnion = null;
    if (type === "enfant" && ancre) {
      const unions = await unionsDe(ancre);
      if (unions.length) {
        selUnion = h("select", { style: "min-width:230px" },
          ...unions.map((u) => h("option", { value: u.famille },
            u.conjoint ? "Avec " + u.conjoint.nom : "Conjoint·e inconnu·e")),
          h("option", { value: "__nouvelle__" }, "— Nouvelle union (autre parent inconnu) —"));
        if (lien && lien.famille) selUnion.value = lien.famille;
        else { const c = unions.find((u) => u.conjoint); if (c) selUnion.value = c.famille; }
        zoneUnion.append(h("span", { style: "color:var(--gris)" }, "dans l'union"), selUnion);
      }
    }
    // Mode créer / relier (seulement s'il y a un lien à établir).
    const aLien = !!type;
    zoneMode.style.display = aLien ? "block" : "none";
    if (!aLien) modeRelier = false;
    btnCreer.className = modeRelier ? "bouton secondaire petit" : "bouton petit";
    btnRelier.className = modeRelier ? "bouton petit" : "bouton secondaire petit";
    zoneCreer.style.display = modeRelier ? "none" : "block";
    zoneRelier.style.display = modeRelier ? "block" : "none";
    btnPrimaire.textContent = !aLien ? "Enregistrer"
      : (modeRelier ? "Relier à la fiche" : "Créer et relier");
  }

  // ── Enregistrement ──────────────────────────────────────────────────────
  let enCours = false;

  async function enregistrerSimple(nonIdentifiee) {
    if (enCours) return;
    enCours = true;
    const champs = collecter();
    try {
      if (editer) {
        await apiJson("/api/individus/" + editer, "PUT", champs);
        gardeSaisie(null);
        toast("Modifications enregistrées.");
        aller("personnes", { fiche: editer });
      } else {
        const r = await apiJson("/api/individus", "POST", { ...champs, non_identifiee: !!nonIdentifiee });
        gardeSaisie(null);
        toast("Personne créée.");
        aller("personnes", { fiche: r.id });
      }
    } catch (e) {
      toast(e.message, { type: "erreur", duree: 6000 });
      enCours = false;
    }
  }

  async function enregistrerLie(nonIdentifiee) {
    const type = selLien.value;
    const ancre = ancreFixe ? lien.ancre : ancrePicker.valeur();
    if (!type) return enregistrerSimple(nonIdentifiee);   // personne isolée
    if (!ancre) { toast("Choisissez d'abord la personne concernée par le lien."); return; }

    let url, extra = {};
    if (type === "pere" || type === "mere") { url = "/api/individus/" + ancre + "/parent"; extra.role = type; }
    else if (type === "conjoint") url = "/api/individus/" + ancre + "/conjoint";
    else if (type === "fratrie") url = "/api/individus/" + ancre + "/frere_soeur";
    else {   // enfant
      const cible = selUnion ? selUnion.value : "";
      if (cible && cible !== "__nouvelle__") url = "/api/familles/" + cible + "/enfant";
      else { url = "/api/individus/" + ancre + "/enfant"; if (cible === "__nouvelle__") extra.nouvelle = true; }
    }

    let corps;
    if (modeRelier) {
      const id = relierPicker.valeur();
      if (!id) { toast("Choisissez la personne existante à relier."); return; }
      corps = { id, ...extra };
    } else {
      corps = { champs: collecter(), non_identifiee: !!nonIdentifiee, ...extra };
    }

    if (enCours) return;
    enCours = true;
    try {
      const r = await apiJson(url, "POST", corps);
      gardeSaisie(null);
      toast("Personne reliée.");
      aller("personnes", { fiche: (r && r.id) || ancre });
    } catch (e) {
      toast(e.message, { type: "erreur", duree: 6000 });
      enCours = false;
    }
  }

  const soumettre = () => (editer ? enregistrerSimple(false) : enregistrerLie(false));
  const btnPrimaire = h("button", { class: "bouton", onclick: soumettre },
    editer ? "Enregistrer" : "Enregistrer");

  // ── Assemblage ──────────────────────────────────────────────────────────
  const formulaire = h("div", { class: "form-perso" });
  if (carteLien) formulaire.append(carteLien);
  formulaire.append(zoneCreer, zoneRelier);
  formulaire.append(h("div", { class: "form-actions" },
    btnPrimaire,
    h("button", { class: "bouton secondaire", onclick: retour }, "Annuler")));
  if (!editer) {
    formulaire.append(h("p", { style: "margin-top:10px" },
      h("button", { class: "lien", onclick: () => enregistrerLie(true) },
        "Créer une personne non identifiée"),
      h("span", { style: "color:var(--gris-clair);font-size:13px" },
        "  — pour un témoin illisible, un conjoint inconnu…")));
  }
  vue.append(formulaire);

  if (!editer) majLien();   // état initial du bloc de lien (async : se complète seul)
}
