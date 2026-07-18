// Onglet Assistant IA — facultatif. Ne modifie jamais l'arbre.
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { champPersonne } from "../composants/champ.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";

const MISSIONS = [
  ["biographie", "Brouillon de biographie", "Rédige une courte biographie d'une personne."],
  ["recherches", "Prochaines recherches", "Priorise les pistes de tout l'arbre."],
  ["coherence", "Contrôle de cohérence", "Explique les anomalies détectées."],
  ["documenter", "Personnes à documenter", "Suggère des sources à chercher."],
];

export async function vueAssistant(vue) {
  vue.append(h("h1", {}, "🤖 Assistant IA"));
  const r = await apiGet("/api/reglages").catch(() => ({}));

  if (!r.cle_definie) {
    vue.append(h("div", { class: "carte" },
      h("p", {}, "L'assistant a besoin d'une clé API (Anthropic, OpenAI, Gemini) — "
        + "entièrement facultatif."),
      h("p", { class: "sous-titre" },
        "Sans clé, aucune donnée ne quitte votre ordinateur. Même avec une clé, "
        + "l'assistant n'envoie que les informations de la mission choisie — jamais "
        + "vos images, jamais l'arbre entier — et uniquement quand vous lancez une mission. "
        + "Il ne modifie jamais votre arbre : il produit un brouillon à vérifier."),
      h("button", { class: "bouton", onclick: () => aller("reglages") }, "Aller dans Réglages")));
    return;
  }

  vue.append(h("p", { class: "sous-titre" },
    "Choisissez une mission. Le résultat est un brouillon à vérifier ; vous "
    + "pouvez l'enregistrer dans votre carnet. L'IA ne modifie jamais l'arbre."));

  const liste = await apiGet("/api/individus").catch(() => []);
  const pick = champPersonne(liste, { placeholder: "Personne (pour la biographie)…" });
  const selM = h("select", {}, ...MISSIONS.map(([v, l]) => h("option", { value: v }, l)));
  const zone = h("div", {});

  vue.append(h("div", { class: "carte" },
    h("div", { style: "display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end" },
      h("div", {}, h("label", {}, "Mission"), selM),
      h("div", {}, h("label", {}, "Personne"), pick.element),
      h("button", { class: "bouton", onclick: lancer }, "Lancer la mission"))));
  vue.append(zone);

  async function lancer() {
    vider(zone);
    zone.append(h("div", { class: "carte" }, h("p", { style: "color:var(--gris)" }, "L'assistant réfléchit…")));
    const corps = { type: selM.value };
    if (selM.value === "biographie") corps.cible = pick.valeur();
    try {
      const r2 = await apiJson("/api/assistant/mission", "POST", corps);
      afficher(r2.texte, r2.avertissement);
    } catch (e) { vider(zone); zone.append(h("div", { class: "carte" }, h("p", {}, "⚠ " + e.message))); }
  }

  function afficher(texte, avert) {
    vider(zone);
    zone.append(h("div", { class: "carte" },
      h("div", { style: "margin-bottom:8px" }, badge(avert || "Brouillon IA — à vérifier", "attention")),
      h("p", { style: "white-space:pre-wrap" }, texte),
      h("div", { class: "barre-actions", style: "margin-top:10px" },
        h("button", { class: "bouton secondaire petit", onclick: () => {
          navigator.clipboard?.writeText(texte); toast("Copié.");
        } }, "📋 Copier"),
        h("button", { class: "bouton secondaire petit", onclick: async () => {
          try {
            await apiJson("/api/carnet", "POST",
              { type: "ia", titre: "Brouillon IA", texte });
            toast("Enregistré dans le carnet.");
          } catch (e) { toast(e.message); }
        } }, "📔 Enregistrer au carnet"))));
  }
}
