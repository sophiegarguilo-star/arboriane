// Onglet Arbre — éventail / ascendance / descendance en SVG, avec un panneau
// de personnalisation complet (persisté). Clic sur une case → fiche.
import { h, vider } from "../noyau/dom.js";
import { aller, etat, majEspace } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { champPersonne } from "../composants/champ.js";
import { toast } from "../composants/toast.js";
import { chargeur } from "../composants/chargeur.js";
import { dialogueExportArbre } from "../composants/impression.js";
import { imprimerMosaique } from "../composants/mosaique.js";
import { ouvrirVolet, fermerVolet } from "../composants/volet.js";
import { badge, pastilleSexe } from "../composants/badge.js";

const CLE = "arbo_arbre_opts";
const DEFAUTS = {
  mode: "ascendance", generations: 6, angle: 360, theme: "sexe",
  prenoms: "tous", gras: true, dates: true, lieux: false, police: "sans",
  taille: 100, sosa: false, implexe: false, vierge: false, profession: false, pastille: "monogramme",
  preuves: false, sens: "gd", trait_forme: "courbe",
  titre: "", trait_epaisseur: 0, trait_couleur: "",
  fond: "", fond_opacite: 60, vignette: false,
  cadre: "aucun", cadre_couleur: "", legende: true,
};

function lireOpts() {
  try { return { ...DEFAUTS, ...JSON.parse(localStorage.getItem(CLE) || "{}") }; }
  catch { return { ...DEFAUTS }; }
}
function ecrireOpts(o) { try { localStorage.setItem(CLE, JSON.stringify(o)); } catch { /* */ } }

export async function vueArbre(vue, arg) {
  vue.append(h("h1", {}, "Arbre"));
  const liste = await apiGet("/api/individus").catch(() => []);
  if (!liste.length) {
    vue.append(h("div", { class: "vide" }, h("span", { class: "grand" }, "🌳"), "Aucune personne dans l'arbre."));
    return;
  }
  const esp = etat.espace || {};
  const opts = lireOpts();
  if (opts.mode === "sablier") opts.mode = "ascendance";   // rendu sablier retiré
  let racine = (arg && arg.racine) || esp.racine_id || liste[0].id;
  // Garde l'arg d'historique à jour avec la racine COURANTE : ainsi « ← Retour »
  // depuis une fiche redonne l'arbre ré-enraciné sur la même personne (et non
  // l'arbre par défaut sur la racine de l'espace). Le zoom, lui, se réajuste.
  const memoRacine = () => { etat.arg = { ...(etat.arg || {}), racine }; };
  memoRacine();

  // Lot D : l'arrière-plan mémorisé DANS l'arbre (manifeste) prime sur le
  // réglage local du navigateur → on le retrouve d'un poste à l'autre.
  const metaEsp = await apiGet("/api/espace").catch(() => ({}));
  const fondArbre = metaEsp.arbre_fond || esp.arbre_fond;
  if (fondArbre && fondArbre.fond) {
    opts.fond = fondArbre.fond;
    if (fondArbre.fond_opacite) opts.fond_opacite = fondArbre.fond_opacite;
  }

  // hauteur bornée : la zone est un vrai cadre de défilement (sinon elle grandit
  // avec l'arbre et « Ajuster » ne peut pas calculer la place disponible).
  const zone = h("div", { class: "carte zone-arbre", style: "overflow:auto;padding:10px;height:74vh" });
  // index pour l'infobulle au survol (nom, dates, lieux)
  const infoParId = {};
  liste.forEach((p) => { infoParId[p.id] = p; });
  const infobulle = h("div", { class: "arbre-infobulle", style: "display:none" });
  vue.append(infobulle);
  function montrerInfobulle(e, id) {
    const p = infoParId[id];
    if (!p) return;
    vider(infobulle);
    const nl = (p.naissance || {}).lieu, dl = (p.deces || {}).lieu;
    // filter(Boolean) : append(null) insérerait un nœud texte « null » (d'où le
    // « nullnullnull » sur une carte sans dates ni lieux).
    [
      h("div", { style: "font-weight:600" }, p.nom || ""),
      p.periode ? h("div", { style: "color:var(--gris-clair);font-size:12px" }, p.periode) : null,
      nl ? h("div", { style: "font-size:12px" }, "✳️ " + nl) : null,
      dl ? h("div", { style: "font-size:12px" }, "✝️ " + dl) : null,
    ].filter(Boolean).forEach((el) => infobulle.append(el));
    infobulle.style.display = "block";
    infobulle.style.left = Math.min(e.clientX + 14, window.innerWidth - 230) + "px";
    infobulle.style.top = (e.clientY + 16) + "px";
  }
  let zoomArbre = 1;
  let premierRendu = true;   // au tout premier affichage, on cadre l'arbre à l'écran
  let aBouge = false;   // vrai si un glisser (pan) est en cours → n'ouvre pas la fiche
  const plies = new Set();   // numéros Sosa des branches repliées (relatifs à la racine courante)
  const lblZoom = h("span", { style: "font-size:12px;color:var(--gris);min-width:44px;text-align:center" }, "100%");

  function appliquerZoom(z) {
    zoomArbre = Math.max(0.2, Math.min(4, z));
    const svg = zone.querySelector("svg");
    if (svg && svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width) {
      const vb = svg.viewBox.baseVal;
      svg.style.width = (vb.width * zoomArbre) + "px";
      svg.style.height = (vb.height * zoomArbre) + "px";
      svg.style.maxWidth = "none";
      // flex:none empêche le conteneur flex de COMPRIMER l'arbre quand il est
      // plus grand que la zone ; margin:auto le centre quand il est plus petit,
      // et retombe à 0 (coin haut-gauche, entièrement défilable) quand il est
      // plus grand — sans jamais rogner le début comme un justify-center.
      svg.style.flex = "none";
      svg.style.margin = "auto";
    }
    lblZoom.textContent = Math.round(zoomArbre * 100) + "%";
  }
  function ajuster() {
    const svg = zone.querySelector("svg");
    if (!svg || !svg.viewBox || !svg.viewBox.baseVal.width) return;
    const vb = svg.viewBox.baseVal;
    // ajuste à l'écran : on tient dans la largeur ET la hauteur du cadre visible
    const dispoW = Math.max(200, zone.clientWidth - 24);
    const dispoH = Math.max(200, zone.clientHeight - 24);
    appliquerZoom(Math.min(dispoW / vb.width, dispoH / vb.height));
    // recentre horizontalement une fois ajusté
    requestAnimationFrame(() => { zone.scrollLeft = (zone.scrollWidth - zone.clientWidth) / 2; zone.scrollTop = 0; });
  }

  // centre la vue sur une personne (par défaut la racine)
  function centrerSur(id) {
    const el = id && zone.querySelector('[data-id="' + id + '"]');
    if (!el) { ajuster(); return; }
    const er = el.getBoundingClientRect(), zr = zone.getBoundingClientRect();
    const cx = (er.left + er.width / 2) - zr.left + zone.scrollLeft;
    const cy = (er.top + er.height / 2) - zr.top + zone.scrollTop;
    zone.scrollLeft = cx - zone.clientWidth / 2;
    zone.scrollTop = cy - zone.clientHeight / 2;
  }

  // re-enracine l'arbre sur une personne (navigation de proche en proche)
  function recentrer(id) {
    racine = id; plies.clear();   // les Sosa changent de sens → on repart déplié
    memoRacine();
    if (pick && pick.definir) pick.definir(id);
    majEtoile(); dessiner(); ouvrirMiniFiche(id);
  }

  const NIV = { acte: "ok", declare: "info", estime: "attention",
                non_qualifie: "attention", manquant: "attention" };

  // volet mini-fiche au clic sur une case, sans quitter l'arbre
  async function ouvrirMiniFiche(id, sosaArbre) {
    const [f, pv] = await Promise.all([
      apiGet("/api/individus/" + id).catch(() => null),
      apiGet("/api/individus/" + id + "/preuves").catch(() => null),
    ]);
    if (!f) { aller("personnes", { fiche: id }); return; }
    const conjoints = f.unions.map((u) => u.conjoint).filter(Boolean);
    const enfants = f.unions.flatMap((u) => u.enfants);
    const puce = (p) => p ? h("span", { class: "puce-pers", onclick: () => recentrer(p.id) },
      pastilleSexe(p.sexe), p.nom + (p.periode ? " · " + p.periode : "")) : null;
    const groupe = (titre, arr) => arr.length
      ? h("div", { class: "rel-groupe" }, h("h3", {}, titre), ...arr.map(puce)) : null;
    const ligneInfo = (lib, val) => val ? h("div", { class: "def-ligne" },
      h("span", { class: "def-cle" }, lib), h("span", { class: "def-val" }, val)) : null;
    const nais = f.naissance || {}, dec = f.deces || {};

    ouvrirVolet(h("div", {},
      h("div", { style: "color:var(--gris)" },
        (f.periode || "dates inconnues") + (f.age != null ? " · " + f.age + " ans" : "")),
      h("div", { style: "display:flex;gap:5px;flex-wrap:wrap;margin:6px 0" },
        f.sosa ? badge("Sosa " + f.sosa, "ok") : null,
        badge(f.vivant ? "Présumé vivant" : "Décédé", f.vivant ? "attention" : "")),
      pv && pv.faits ? h("div", { style: "display:flex;gap:5px;flex-wrap:wrap;margin:6px 0" },
        ...pv.faits.map((ft) => badge(ft.libelle + " · " + (ft.niveau_texte || ft.niveau),
          NIV[ft.niveau] || ""))) : null,
      ligneInfo("Naissance", [nais.date, nais.lieu].filter(Boolean).join(" à ")),
      ligneInfo("Décès", [dec.date, dec.lieu].filter(Boolean).join(" à ")),
      ligneInfo("Profession", (f.professions || []).map((p) => p.valeur).filter(Boolean).join(", ")),
      h("p", { class: "sous-titre", style: "margin:10px 0 2px" },
        "Cliquez un proche pour recentrer l'arbre sur lui."),
      groupe("Parents", [...f.peres, ...f.meres]),
      groupe("Frères et sœurs", f.fratrie),
      groupe("Conjoint·e·s", conjoints),
      groupe("Enfants", enfants),
      // plier / déplier la branche d'ascendance (si la personne a des parents)
      (sosaArbre != null && sosaArbre >= 1 && (f.peres.length || f.meres.length))
        ? h("div", { style: "margin-top:10px" },
            plies.has(sosaArbre)
              ? h("button", { class: "bouton secondaire petit",
                  onclick: () => { plies.delete(sosaArbre); dessiner(); fermerVolet(); } },
                  "➕ Déplier cette branche")
              : h("button", { class: "bouton secondaire petit",
                  onclick: () => { plies.add(sosaArbre); dessiner(); fermerVolet(); } },
                  "➖ Plier cette branche"))
        : null,
      h("div", { class: "barre-actions", style: "margin-top:14px" },
        h("button", { class: "bouton petit",
          onclick: () => { fermerVolet(); aller("personnes", { fiche: id }); } }, "Ouvrir la fiche complète →"),
        h("button", { class: "bouton secondaire petit", onclick: () => recentrer(id) }, "🎯 Recentrer ici"))),
      { titre: f.nom_complet });
  }

  async function dessiner() {
    vider(zone); zone.append(chargeur("Dessin de l'arbre…"));
    // le service descendance attend sens = vertical|horizontal ; on traduit gd/bh
    const effectifs = { ...opts };
    if (opts.mode === "descendance") effectifs.sens = opts.sens === "bh" ? "horizontal" : "vertical";
    const params = new URLSearchParams({ racine, ...Object.fromEntries(
      Object.entries(effectifs).map(([k, v]) => [k, String(v)])) });
    if (plies.size) params.set("plies", [...plies].join(","));
    try {
      const r = await apiGet("/api/arbre?" + params.toString());
      vider(zone);
      const boite = h("div", { html: r.svg, style: "display:flex;min-width:100%;min-height:100%" });
      boite.querySelectorAll("[data-id]").forEach((el) => {
        const id = el.getAttribute("data-id");
        const so = el.getAttribute("data-sosa");
        el.style.cursor = "pointer";
        el.addEventListener("click", () => { if (!aBouge) ouvrirMiniFiche(id, so ? +so : null); });
        el.addEventListener("mousemove", (e) => montrerInfobulle(e, id));
        el.addEventListener("mouseleave", () => { infobulle.style.display = "none"; });
      });
      zone.append(boite);
      if (premierRendu) {   // 1ʳᵉ ouverture : on cadre l'arbre à l'écran
        premierRendu = false;
        requestAnimationFrame(() => ajuster());
      } else {
        appliquerZoom(zoomArbre);   // sinon on conserve le zoom courant
      }
    } catch (e) { vider(zone); zone.append(h("div", { class: "vide" }, e.message)); }
  }

  function maj(cle, val) {
    opts[cle] = val; ecrireOpts(opts); dessiner();
    // l'arrière-plan est aussi mémorisé dans l'arbre (Lot D)
    if (cle === "fond" || cle === "fond_opacite") {
      apiJson("/api/espaces/fond-arbre", "POST",
        { fond: opts.fond, fond_opacite: opts.fond_opacite }).catch(() => { /* */ });
    }
  }

  async function reinitialiserApparence() {
    try { localStorage.removeItem(CLE); } catch { /* */ }
    try {
      await apiJson("/api/espaces/fond-arbre", "POST", { fond: "", fond_opacite: 60 });
    } catch { /* */ }
    // repart sur la vue par défaut : Sosa 1 (racine de l'arbre) en ascendance,
    // recadré à l'écran (on ne passe pas de racine → vueArbre reprend le Sosa 1).
    vider(vue); await vueArbre(vue, {});
    toast("Vue réinitialisée : Sosa 1, ascendance.");
  }

  // ── Barre principale ──
  // « Personne de départ » : celle autour de qui l'arbre est construit.
  const pick = champPersonne(liste, { initial: racine, placeholder: "Choisir la personne de départ…",
    onChoix: (id) => { if (id) { racine = id; plies.clear(); memoRacine(); dessiner(); majEtoile(); } } });
  const selMode = select(["eventail", "ascendance", "descendance", "tableau"],
    ["Éventail", "Ascendance", "Descendance", "Tableau par génération"], opts.mode,
    (v) => { plies.clear(); maj("mode", v); majOptionsMode(); });
  const selMosaique = select(["A4", "A3", "A0"], ["A4", "A3", "A0"], "A4", () => {});
  selMosaique.title = "Format des feuilles de la mosaïque (A0 = affiche unique)";
  selMosaique.style.marginLeft = "6px";

  // Étoile « personne de référence de l'arbre » (persistée dans l'espace)
  const etoile = h("span", { title: "Personne de référence de l'arbre" });
  function estRacineEspace() { return racine === (etat.espace || {}).racine_id; }
  function majEtoile() { etoile.textContent = estRacineEspace() ? "⭐" : ""; }
  const btnRacine = h("button", { class: "bouton secondaire petit", style: "height:40px",
    title: "Faire de cette personne le point de départ par défaut de votre arbre",
    onclick: async () => {
      try {
        await apiJson("/api/espaces/racine", "POST", { id: racine });
        await majEspace(apiGet);
        toast("Personne de l'arbre définie.");
        majEtoile();
      } catch (e) { toast(e.message); }
    } }, "⭐ Définir comme personne de l'arbre");

  let panneauVisible = false;
  const panneau = h("div", { class: "pev", style: "display:none" });
  const btnPers = h("button", { class: "bouton secondaire petit", style: "height:40px", onclick: () => {
    panneauVisible = !panneauVisible;
    panneau.style.display = panneauVisible ? "grid" : "none";
    btnPers.textContent = panneauVisible ? "🎨 Masquer" : "🎨 Personnaliser";
  } }, "🎨 Personnaliser");

  vue.append(h("div", { class: "barre-actions", style: "margin-bottom:12px" },
    h("div", {}, h("label", {}, "Personne de départ ", etoile), pick.element),
    h("div", {}, h("label", {}, "Vue"), selMode),
    h("div", { style: "align-self:flex-end" }, btnRacine),
    h("div", { style: "align-self:flex-end" }, btnPers),
    h("div", { style: "align-self:flex-end" },
      h("div", { class: "zoom-barre" },
        h("button", { class: "bouton secondaire petit", title: "Zoom arrière",
          onclick: () => appliquerZoom(zoomArbre / 1.2) }, "−"),
        lblZoom,
        h("button", { class: "bouton secondaire petit", title: "Zoom avant",
          onclick: () => appliquerZoom(zoomArbre * 1.2) }, "+"),
        h("button", { class: "bouton secondaire petit", title: "Voir tout l'arbre (ajuster à l'écran)",
          onclick: ajuster }, "⛶ Tout voir"),
        h("button", { class: "bouton secondaire petit", title: "Centrer sur la personne de départ",
          onclick: () => centrerSur(racine) }, "🎯 Centrer"),
        h("button", { class: "bouton secondaire petit",
          title: "Réinitialiser : revenir à la vue par défaut (Sosa 1, ascendance)",
          onclick: reinitialiserApparence }, "🔄"))),
    h("div", { style: "align-self:flex-end" },
      h("button", { class: "bouton secondaire petit",
        onclick: () => dialogueExportArbre(zone.querySelector("svg"), "arbre_" + racine) },
        "🖨 Imprimer / Exporter"),
      selMosaique,
      h("button", { class: "bouton secondaire petit", style: "margin-left:6px",
        title: "Imprimer un grand arbre en mosaïque (feuilles à assembler ; A0 = affiche unique)",
        onclick: () => imprimerMosaique(zone.querySelector("svg"), { format: selMosaique.value }) }, "🧩 Mosaïque")),
    h("div", { style: "align-self:flex-end" },
      h("button", { class: "bouton secondaire petit", onclick: () => aller("personnes", { fiche: racine }) }, "Fiche"))));

  // ── Panneau de personnalisation ──
  bloc(panneau, "Profondeur", plage(2, 12, opts.generations, (v) => maj("generations", v)));
  const blocAngle = bloc(panneau, "Angle (éventail)", select(["360", "270", "180"], ["360°", "270°", "180°"],
    String(opts.angle), (v) => maj("angle", +v)));
  bloc(panneau, "Couleurs", select(["sexe", "branche", "generation", "aucune"],
    ["Par sexe", "Par branche", "Par génération", "Aucune"], opts.theme, (v) => maj("theme", v)));
  bloc(panneau, "Prénoms", select(["tous", "premier", "initiale", "nom"],
    ["Tous", "Premier", "Initiale", "Nom seul"], opts.prenoms, (v) => maj("prenoms", v)));
  bloc(panneau, "Pastille", select(["monogramme", "photo", "aucune"],
    ["Monogramme", "Photo", "Aucune"], opts.pastille, (v) => maj("pastille", v)));
  bloc(panneau, "Police", select(["sans", "serif"], ["Moderne", "Classique"],
    opts.police, (v) => maj("police", v)));
  // Taille du texte : utile surtout en éventail (en cases, le texte se cale
  // automatiquement à la cellule).
  const blocTaille = bloc(panneau, "Taille du texte", plage(70, 140, opts.taille, (v) => maj("taille", v), "%"));
  // Titre imprimé au-dessus de l'arbre (validé à la sortie du champ)
  const inpTitre = h("input", { type: "text", value: opts.titre || "",
    placeholder: "titre imprimé au-dessus (facultatif)", style: "width:100%" });
  inpTitre.addEventListener("change", () => maj("titre", inpTitre.value.trim()));
  bloc(panneau, "Titre de l'arbre", inpTitre);

  const blocDispo = bloc(panneau, "Disposition", select(["gd", "bh"],
    ["Standard", "Alternée (asc. bas→haut / desc. horizontale)"],
    opts.sens, (v) => maj("sens", v)));
  const blocConn = bloc(panneau, "Connecteurs", select(["courbe", "coude"], ["Courbes", "Coudés"],
    opts.trait_forme, (v) => maj("trait_forme", v)));
  const blocEp = bloc(panneau, "Épaisseur des traits", select(["0", "1", "2", "3"],
    ["Auto", "Fine", "Moyenne", "Épaisse"], String(opts.trait_epaisseur), (v) => maj("trait_epaisseur", +v)));
  const inpCoul = h("input", { type: "color", value: opts.trait_couleur || "#c3ccd4",
    class: "champ-couleur" });
  inpCoul.addEventListener("change", () => maj("trait_couleur", inpCoul.value));
  const blocCoul = bloc(panneau, "Couleur des traits",
    h("div", { style: "display:flex;gap:6px;align-items:center" }, inpCoul,
      h("button", { class: "bouton secondaire petit", onclick: () => maj("trait_couleur", "") }, "auto")));

  // Affiche seulement les options utiles au mode courant.
  function majOptionsMode() {
    blocAngle.style.display = opts.mode === "eventail" ? "" : "none";
    blocTaille.style.display = opts.mode === "eventail" ? "" : "none";
    const asc = opts.mode === "ascendance" || opts.mode === "descendance";
    [blocDispo, blocConn, blocEp, blocCoul].forEach((b) => { b.style.display = asc ? "" : "none"; });
  }
  majOptionsMode();
  bloc(panneau, "", interrupteur("Afficher les dates", opts.dates, (v) => maj("dates", v)));
  bloc(panneau, "", interrupteur("Afficher les lieux", opts.lieux, (v) => maj("lieux", v)));
  bloc(panneau, "", interrupteur("Nom de famille en gras", opts.gras, (v) => maj("gras", v)));
  bloc(panneau, "", interrupteur("N° Sosa", opts.sosa, (v) => maj("sosa", v)));
  bloc(panneau, "", interrupteur("Grouper l'implexe (ancêtres répétés grisés)",
    opts.implexe, (v) => maj("implexe", v)));
  bloc(panneau, "", interrupteur("Arbre à vide (cartes vierges à imprimer)",
    opts.vierge, (v) => maj("vierge", v)));
  bloc(panneau, "", interrupteur("Profession", opts.profession, (v) => maj("profession", v)));
  bloc(panneau, "", interrupteur("Preuves colorées", opts.preuves, (v) => maj("preuves", v)));
  bloc(panneau, "", interrupteur("Légende des preuves", opts.legende, (v) => maj("legende", v)));

  // Arrière-plan : aucun / texture générée / couleur unie / image personnelle.
  const estImg = (opts.fond || "").startsWith("img:");
  const estCoul = /^#/.test(opts.fond || "");
  const inpFond = h("input", { type: "color", value: estCoul ? opts.fond : "#f4e6d2",
    class: "champ-couleur" });
  inpFond.addEventListener("change", () => maj("fond", inpFond.value));
  const wrapFondCoul = h("div",
    { style: "display:flex;gap:6px;align-items:center;margin-top:6px" }, inpFond);
  wrapFondCoul.style.display = estCoul ? "" : "none";
  // upload d'une image personnelle (stockée dans Fonds/ de l'arbre)
  const inpImg = h("input", { type: "file", accept: "image/*", style: "display:none" });
  inpImg.addEventListener("change", async () => {
    const f = inpImg.files && inpImg.files[0];
    if (!f) return;
    try {
      const data = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(f);
      });
      const rep = await apiJson("/api/media/Fonds", "POST", { nom: f.name, data });
      maj("fond", "img:" + rep.fichier);
      toast("Image de fond ajoutée.");
    } catch { toast("Import de l'image impossible."); }
  });
  const wrapOpac = h("div", { style: "margin-top:8px" },
    h("div", { style: "font-size:12px;color:var(--gris-clair);margin-bottom:2px" },
      "Opacité de l'image"),
    plage(15, 100, opts.fond_opacite, (v) => maj("fond_opacite", v), "%"));
  wrapOpac.style.display = estImg ? "" : "none";
  const selFond = select(
    ["", "parchemin", "vieux-papier", "toile", "sepia", "couleur", "image"],
    ["Aucun", "Parchemin", "Vieux papier", "Toile de lin", "Sépia", "Couleur unie…", "Image personnelle…"],
    estImg ? "image" : (estCoul ? "couleur" : (opts.fond || "")), (v) => {
      wrapFondCoul.style.display = v === "couleur" ? "" : "none";
      wrapOpac.style.display = v === "image" ? "" : "none";
      if (v === "couleur") maj("fond", inpFond.value);
      else if (v === "image") inpImg.click();   // maj après le téléversement
      else maj("fond", v);
    });
  bloc(panneau, "Arrière-plan", h("div", {}, selFond, wrapFondCoul, wrapOpac, inpImg));
  bloc(panneau, "Cadre décoratif", select(["aucun", "simple", "double", "coins", "passe-partout"],
    ["Aucun", "Filet simple", "Double filet", "Coins d'angle", "Passe-partout (tableau)"],
    opts.cadre, (v) => maj("cadre", v)));
  bloc(panneau, "", interrupteur("Vignette (bords assombris)", opts.vignette, (v) => maj("vignette", v)));
  const inpCadreCoul = h("input", { type: "color", value: opts.cadre_couleur || "#b79b6a",
    class: "champ-couleur" });
  inpCadreCoul.addEventListener("change", () => maj("cadre_couleur", inpCadreCoul.value));
  bloc(panneau, "Couleur du cadre", h("div", { style: "display:flex;gap:6px;align-items:center" },
    inpCadreCoul, h("button", { class: "bouton secondaire petit", onclick: () => maj("cadre_couleur", "") }, "auto")));
  bloc(panneau, "", h("button", { class: "bouton fantome petit",
    title: "Revenir à la vue par défaut (Sosa 1, ascendance) et aux réglages d'origine",
    onclick: reinitialiserApparence }, "🔄 Réinitialiser la vue"));

  vue.append(panneau);
  majEtoile();

  // zoom à la molette (molette seule), centré sur le curseur
  zone.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = zone.getBoundingClientRect();
    const px = e.clientX - r.left + zone.scrollLeft;   // point sous le curseur (coords contenu)
    const py = e.clientY - r.top + zone.scrollTop;
    const avant = zoomArbre;
    appliquerZoom(zoomArbre * (e.deltaY < 0 ? 1.12 : 0.9));
    const k = zoomArbre / avant;
    zone.scrollLeft = px * k - (e.clientX - r.left);   // garde le point fixe
    zone.scrollTop = py * k - (e.clientY - r.top);
  }, { passive: false });

  // déplacement au glisser (pan) — comme dans les logiciels d'arbre
  zone.style.cursor = "grab";
  let panOn = false, sx = 0, sy = 0, sl0 = 0, st0 = 0;
  zone.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    panOn = true; aBouge = false;
    sx = e.clientX; sy = e.clientY; sl0 = zone.scrollLeft; st0 = zone.scrollTop;
    zone.style.cursor = "grabbing";
  });
  zone.addEventListener("pointermove", (e) => {
    if (!panOn) return;
    const dx = e.clientX - sx, dy = e.clientY - sy;
    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) aBouge = true;
    zone.scrollLeft = sl0 - dx; zone.scrollTop = st0 - dy;
  });
  const finPan = () => { panOn = false; zone.style.cursor = "grab"; };
  zone.addEventListener("pointerup", finPan);
  zone.addEventListener("pointerleave", finPan);

  vue.append(zone);
  dessiner();
}

// ── petits helpers d'UI ──
function bloc(parent, label, control) {
  const el = h("div", { class: "pev-bloc" },
    label ? h("label", {}, label) : null, control);
  parent.append(el);
  return el;
}
function select(vals, libs, courant, onChange) {
  const s = h("select", {}, ...vals.map((v, i) =>
    h("option", { value: v, selected: v === courant ? "selected" : null }, libs[i])));
  s.addEventListener("change", () => onChange(s.value));
  return s;
}
function plage(min, max, courant, onChange, suffixe = "") {
  const val = h("span", { style: "font-size:12px;color:var(--gris)" }, courant + suffixe);
  const r = h("input", { type: "range", min, max, value: courant, style: "width:120px" });
  r.addEventListener("input", () => { val.textContent = r.value + suffixe; });
  r.addEventListener("change", () => onChange(+r.value));
  return h("div", { style: "display:flex;align-items:center;gap:8px" }, r, val);
}
function interrupteur(label, coche, onChange) {
  const c = h("input", { type: "checkbox", checked: coche ? "checked" : null });
  c.addEventListener("change", () => onChange(c.checked));
  return h("label", { style: "display:flex;align-items:center;gap:7px;cursor:pointer" }, c, label);
}

