// Onglet Réglages — assistant IA (clé masquée), géocodage, confidentialité.
import { h, vider } from "../noyau/dom.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";

const FOURNISSEURS = [["anthropic", "Anthropic (Claude)"], ["openai", "OpenAI (GPT)"],
                      ["gemini", "Google (Gemini)"]];

export async function vueReglages(vue) {
  vue.append(h("h1", {}, "Réglages"));
  const r = await apiGet("/api/reglages").catch(() => ({}));

  // Assistant IA
  const zoneCle = h("div", {});
  const selF = h("select", {}, ...FOURNISSEURS.map(([v, l]) =>
    h("option", { value: v, selected: r.ia_fournisseur === v ? "selected" : null }, l)));
  const inpModele = h("input", { value: r.ia_modele || "", placeholder: "modèle (facultatif — défaut choisi automatiquement)", style: "width:100%" });
  const inpCle = h("input", { type: "password", placeholder: "Collez votre clé API", style: "width:100%" });

  function etatCle() {
    vider(zoneCle);
    if (r.cle_definie) {
      zoneCle.append(h("p", {}, badge("Clé enregistrée " + (r.cle_apercu || ""), "ok"),
        h("button", { class: "lien", style: "margin-left:10px", onclick: async () => {
          try {
            await apiJson("/api/reglages", "PUT", { effacer_cle: true });
            toast("Clé effacée."); r.cle_definie = false; etatCle();
          } catch (e) { toast(e.message); }
        } }, "effacer la clé")));
    } else {
      zoneCle.append(h("p", { class: "sous-titre" }, "Aucune clé enregistrée — l'assistant est inactif."));
    }
  }

  const carteIA = h("div", { class: "carte" },
    h("h2", {}, "🤖 Assistant IA (facultatif)"),
    h("p", { class: "sous-titre" },
      "L'assistant ne fonctionne qu'avec votre propre clé API. Sans clé, "
      + "Arboriane marche parfaitement — rien n'est envoyé en ligne. La clé est "
      + "stockée sur votre ordinateur, jamais affichée en clair, jamais dans un arbre."),
    h("p", { class: "sous-titre", style: "color:var(--rouge,#a33)" },
      "⚠ Important : quand VOUS utilisez l'assistant (biographie, question…), les "
      + "informations concernées — noms, dates, lieux, filiations, y compris de "
      + "personnes éventuellement vivantes — sont envoyées au fournisseur choisi "
      + "(Anthropic, OpenAI ou Google). C'est la seule fonction qui transmet des "
      + "données de vos arbres, et uniquement sur votre action."),
    zoneCle,
    h("div", { class: "champ" }, h("label", {}, "Fournisseur"), selF),
    h("div", { class: "champ" }, h("label", {}, "Modèle"), inpModele),
    h("div", { class: "champ" }, h("label", {}, "Clé API"), inpCle),
    h("div", { class: "barre-actions" },
      h("button", { class: "bouton", onclick: async () => {
        const corps = { ia_fournisseur: selF.value, ia_modele: inpModele.value.trim() };
        if (inpCle.value.trim()) corps.ia_cle = inpCle.value.trim();
        try {
          const res = await apiJson("/api/reglages", "PUT", corps);
          Object.assign(r, res); inpCle.value = "";
          toast("Réglages enregistrés."); etatCle();
        } catch (e) { toast(e.message); }
      } }, "Enregistrer")));
  etatCle();
  vue.append(carteIA);

  // Géocodage
  const chk = h("input", { type: "checkbox", checked: r.geocodage_ok ? "checked" : null });
  chk.addEventListener("change", async () => {
    try {
      await apiJson("/api/reglages", "PUT", { geocodage_ok: chk.checked });
      toast(chk.checked ? "Géocodage activé." : "Géocodage désactivé.");
    } catch (e) { chk.checked = !chk.checked; toast(e.message); }
  });
  // Pays par défaut : ajouté à la recherche d'un lieu sans pays (ex. « Neufchâteau »
  // → « Neufchâteau, Belgique »), pour éviter les confusions au géocodage.
  const champPays = h("input", { type: "text", placeholder: "ex. Belgique, France, Suisse…",
    value: r.pays_defaut || "", style: "width:240px" });
  let paysTimer = null;
  const sauverPays = () => { clearTimeout(paysTimer); paysTimer = setTimeout(async () => {
    try { await apiJson("/api/reglages", "PUT", { pays_defaut: champPays.value.trim() });
      toast("Pays par défaut enregistré."); } catch (e) { toast(e.message); }
  }, 600); };
  champPays.addEventListener("input", sauverPays);
  vue.append(h("div", { class: "carte" },
    h("h2", {}, "🗺 Géocodage des lieux"),
    h("p", { class: "sous-titre" },
      "Désactivé par défaut. S'il est activé, Arboriane peut placer vos lieux "
      + "sur la carte en envoyant UNIQUEMENT le nom des lieux à OpenStreetMap "
      + "(jamais vos personnes ni vos données)."),
    h("label", { style: "display:flex;align-items:center;gap:8px" }, chk,
      "Autoriser le géocodage via OpenStreetMap"),
    h("div", { class: "champ", style: "margin-top:12px" },
      h("label", {}, "Pays par défaut (facultatif)"), champPays,
      h("p", { class: "sous-titre", style: "margin-top:4px" },
        "Ajouté à la recherche d'un lieu qui n'indique pas de pays. "
        + "Utile si votre arbre est surtout dans un pays."))));

  // Navigateur d'ouverture (retour utilisateur : Arboriane force Edge)
  const selNav = h("select", {},
    h("option", { value: "" }, "Automatique (Edge, Chrome ou Firefox)"),
    h("option", { value: "edge" }, "Microsoft Edge"),
    h("option", { value: "chrome" }, "Google Chrome"),
    h("option", { value: "firefox" }, "Mozilla Firefox"),
    h("option", { value: "defaut" }, "Navigateur par défaut du système"));
  selNav.value = r.navigateur || "";
  selNav.addEventListener("change", async () => {
    try { await apiJson("/api/reglages", "PUT", { navigateur: selNav.value });
      toast("Navigateur enregistré (effet au prochain lancement)."); }
    catch (e) { toast(e.message); }
  });
  vue.append(h("div", { class: "carte" },
    h("h2", {}, "🌐 Navigateur d'ouverture"),
    h("p", { class: "sous-titre" },
      "Choisissez le navigateur dans lequel Arboriane s'ouvre. "
      + "« Automatique » évite Internet Explorer (qui ne fonctionne pas). "
      + "La modification s'applique au prochain démarrage."),
    h("div", { class: "champ" }, h("label", {}, "Ouvrir Arboriane dans"), selNav)));

  // Mises à jour
  const etatMaj = await apiGet("/api/maj/etat").catch(() => ({}));
  const chkMaj = h("input", { type: "checkbox", checked: etatMaj.verif_active ? "checked" : null });
  chkMaj.addEventListener("change", async () => {
    try {
      await apiJson("/api/maj/preference", "POST", { actif: chkMaj.checked });
      toast(chkMaj.checked ? "Vérification des mises à jour activée."
                           : "Vérification des mises à jour désactivée.");
    } catch (e) { chkMaj.checked = !chkMaj.checked; toast(e.message); }
  });
  vue.append(h("div", { class: "carte" },
    h("h2", {}, "🔔 Mises à jour"),
    h("p", { class: "sous-titre" },
      "Version installée : " + (etatMaj.version || "?") + ". Si activée, Arboriane "
      + "vérifie à l'ouverture si une version plus récente existe, en lisant "
      + "UNIQUEMENT le numéro de version publié (aucune de vos données n'est envoyée)."),
    h("label", { style: "display:flex;align-items:center;gap:8px" }, chkMaj,
      "Vérifier les mises à jour au démarrage")));

  // Confidentialité
  vue.append(h("div", { class: "carte" },
    h("h2", {}, "🔒 Confidentialité"),
    h("p", {}, "Arboriane est 100 % local : aucune donnée n'est collectée, "
      + "aucune télémétrie, rien n'est publié sans votre geste. Vos arbres "
      + "vivent dans leurs dossiers ; vos réglages (dont la clé) restent sur "
      + "cette machine."),
    h("p", { class: "sous-titre" },
      "Seules exceptions, toujours à votre initiative : le géocodage des lieux "
      + "et l'assistant IA (si vous les activez), la vérification des mises à jour "
      + "(si vous l'acceptez), et l'affichage du fond de carte OpenStreetMap quand "
      + "vous ouvrez l'onglet Lieux / Carte.")));
}
