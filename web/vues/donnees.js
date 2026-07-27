// Onglet Sauvegarde et export — organisé par intention.
import { h, vider } from "../noyau/dom.js";
import { aller, majEspace } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { lireOctetsB64 } from "../noyau/octets.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";
import { champPersonne } from "../composants/champ.js";
import { confirmer } from "../composants/modale.js";
import { bilanImport, messageScans } from "../composants/bilanImport.js";

function telechargerTexte(nom, texte, type = "text/plain") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([texte], { type }));
  a.download = nom;
  a.click();
}

export async function vueDonnees(vue) {
  vue.append(h("h1", {}, "Sauvegarde et export"));
  vue.append(h("p", { class: "sous-titre" },
    "À quoi ce fichier va-t-il servir ? Choisissez selon votre intention."));

  const esp = await majEspace(apiGet);
  if (!esp || !esp.ouvert) {
    vue.append(h("div", { class: "carte" },
      h("p", {}, "Ouvrez d'abord un arbre."),
      h("button", { class: "bouton", onclick: () => aller("espace") }, "Espace de travail")));
    return;
  }

  // 1) Sauvegarde complète .zip
  vue.append(h("div", { class: "carte" },
    h("h2", {}, "💾 Sauvegarde complète (.zip)"),
    h("p", { class: "sous-titre" },
      "Tout l'arbre (données, sources, photos, carnet) dans une archive "
      + "réimportable dans Arboriane. C'est votre filet de sécurité."),
    h("button", { class: "bouton", onclick: async () => {
      try {
        const r = await apiJson("/api/espaces/sauvegarde", "POST", {});
        toast("Sauvegarde créée : " + r.fichier);
      } catch (e) { toast(e.message); }
    } }, "Créer une sauvegarde complète")));

  // 2) Export GEDCOM (avec profil d'optimisation par site)
  {
    const selProfil = h("select", {},
      h("option", { value: "generique" }, "Générique (archivage complet)"),
      h("option", { value: "geneanet" }, "Geneanet"),
      h("option", { value: "myheritage" }, "MyHeritage"),
      h("option", { value: "ancestry" }, "Ancestry"),
      h("option", { value: "filae" }, "Filae"));
    const caseTrans = h("input", { type: "checkbox", checked: true });
    vue.append(h("div", { class: "carte" },
      h("h2", {}, "📤 Exporter en GEDCOM (.ged)"),
      h("p", { class: "sous-titre" },
        "Le format d'échange standard, lisible par Geneanet, Heredis, "
        + "MyHeritage, Gramps… Les originaux ne sont jamais modifiés."),
      h("div", { style: "display:flex;gap:16px;flex-wrap:wrap;align-items:flex-end;margin-bottom:12px" },
        h("div", {}, h("label", {}, "Optimiser pour"), selProfil),
        h("label", { style: "display:flex;gap:6px;align-items:center;cursor:pointer" },
          caseTrans, h("span", {}, "Inclure la transcription complète"))),
      h("p", { class: "sous-titre", style: "font-style:italic" },
        "ℹ Les photos et scans ne sont pas transportés par le GEDCOM : "
        + "à réimporter à la main sur le site de destination."),
      h("button", { class: "bouton secondaire", onclick: async () => {
        try {
          const p = selProfil.value;
          const tc = caseTrans.checked ? "1" : "0";
          const url = "/api/export/gedcom?profil=" + encodeURIComponent(p)
            + "&transcription=" + tc;
          const r = await apiGet(url);
          const suff = (p && p !== "generique") ? ("_" + p) : "";
          telechargerTexte((esp.nom || "arbre") + suff + ".ged", r.texte);
          toast("GEDCOM exporté (aussi enregistré dans Exports/).");
        } catch (e) { toast(e.message); }
      } }, "Télécharger le GEDCOM")));
  }

  // 2a-bis) Export d'un rameau (ascendance / descendance d'une personne)
  {
    const liste = await apiGet("/api/individus").catch(() => []);
    const pick = champPersonne(liste, { initial: esp.racine_id,
      placeholder: "Personne de départ…" });
    const selSens = h("select", {},
      h("option", { value: "ascendance" }, "Ses ancêtres (ascendance)"),
      h("option", { value: "descendance" }, "Ses descendants (descendance)"));
    vue.append(h("div", { class: "carte" },
      h("h2", {}, "🌿 Exporter un rameau (.ged)"),
      h("p", { class: "sous-titre" },
        "Une seule branche : les ancêtres OU les descendants d'une personne, "
        + "avec leurs sources. Pratique pour partager une lignée précise."),
      h("div", { style: "display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end" },
        h("div", {}, h("label", {}, "Personne"), pick.element),
        h("div", {}, h("label", {}, "Sens"), selSens),
        h("button", { class: "bouton secondaire", onclick: async () => {
          if (!pick.valeur()) { toast("Choisissez une personne."); return; }
          try {
            const r = await apiJson("/api/export/rameau", "POST",
              { personne: pick.valeur(), sens: selSens.value });
            telechargerTexte(r.fichier || "rameau.ged", r.texte);
            toast("Rameau exporté (aussi dans Exports/).");
          } catch (e) { toast(e.message); }
        } }, "Exporter le rameau"))));
  }

  // 2b) GEDZIP (GEDCOM + images)
  vue.append(h("div", { class: "carte" },
    h("h2", {}, "🗜 GEDZIP (.gdz) — GEDCOM + images"),
    h("p", { class: "sous-titre" },
      "Le GEDCOM accompagné de vos scans et photos, dans une seule archive. "
      + "Vos originaux ne sont jamais modifiés."),
    h("button", { class: "bouton secondaire", onclick: async () => {
      try {
        const r = await apiJson("/api/export/gedzip", "POST", {});
        toast("GEDZIP créé : " + r.fichier);
      } catch (e) { toast(e.message); }
    } }, "Créer un GEDZIP")));

  // 2c) Publication en ligne (vivants masqués)
  const zonePub = h("div", {});
  vue.append(h("div", { class: "carte" },
    h("h2", {}, "🌍 Préparer une publication (vivants masqués)"),
    h("p", { class: "sous-titre" },
      "Pour partager votre arbre en ligne sans exposer les personnes vivantes. "
      + "Arboriane masque les présumés vivants et vous montre d'abord qui sera masqué. "
      + "Rien n'est publié automatiquement : vous obtenez un fichier à diffuser vous-même."),
    h("div", { class: "barre-actions" },
      h("button", { class: "bouton secondaire", onclick: async () => {
        const a = await apiJson("/api/publication/apercu", "POST", {});
        vider(zonePub);
        zonePub.append(h("p", {}, badge(a.total + " personne(s) seront masquées", "attention")));
        if (a.masques.length) {
          const box = h("div", { class: "liste-pers compacte", style: "max-height:200px;overflow:auto" });
          a.masques.forEach((m) => box.append(h("div", { class: "ligne-pers" },
            h("span", {}, m.nom), h("span", { class: "meta" }, m.annee ? "né(e) " + m.annee : ""))));
          zonePub.append(box);
        }
      } }, "👁 Aperçu des personnes masquées"),
      h("button", { class: "bouton", onclick: async () => {
        try {
          const r = await apiJson("/api/publication/gedcom", "POST", {});
          toast("GEDCOM public créé : " + r.fichier);
        } catch (e) { toast(e.message); }
      } }, "Exporter le GEDCOM public")),
    zonePub));

  // 3) Import GEDCOM (avec comparaison avant application)
  const zoneImport = h("div", {});
  const input = h("input", { type: "file", accept: ".ged,.gedcom,text/plain",
    style: "display:none" });
  input.addEventListener("change", async () => {
    const fichier = input.files[0];
    if (!fichier) return;
    const octets_b64 = await lireOctetsB64(fichier);   // octets bruts → détection d'encodage
    vider(zoneImport);
    zoneImport.append(h("p", { style: "color:var(--gris)" }, "Analyse du fichier…"));
    let cmp;
    try { cmp = await apiJson("/api/import/gedcom/comparer-detaille", "POST", { octets_b64 }); }
    catch (e) { vider(zoneImport); zoneImport.append(h("p", {}, "⚠ " + e.message)); return; }
    vider(zoneImport);
    if (cmp.encodage && cmp.encodage.charset && cmp.encodage.charset !== "utf-8") {
      zoneImport.append(h("p", { style: "font-size:13px;color:var(--gris)" },
        "🔤 Encodage détecté : ", h("strong", {}, cmp.encodage.charset),
        cmp.encodage.fiable ? "" : " (deviné)", " — accents rétablis automatiquement."));
    }
    // Fichier DÉJÀ abîmé : des « � » sont écrits dans le fichier lui-même (accents
    // perdus par un logiciel en amont). Aucune version ne peut les deviner : on
    // prévient honnêtement plutôt que de laisser croire à un bug d'Arboriane.
    if (cmp.encodage && cmp.encodage.perdus) {
      zoneImport.append(h("div", { class: "carte", style: "border-left:4px solid var(--alerte);background:#fff6f6" },
        h("p", { style: "color:var(--alerte);font-weight:600;margin:0 0 4px" },
          "⚠ Ce fichier contient déjà " + cmp.encodage.perdus + " caractère(s) perdu(s) « � »."),
        h("p", { style: "font-size:13px;margin:0" },
          "Ces accents ont été cassés par le logiciel qui a créé ce fichier — "
          + "Arboriane ne peut pas les deviner. Réimportez plutôt votre "
          + "fichier GEDCOM d'origine (celui de votre logiciel de généalogie), "
          + "pas un ré-export déjà abîmé.")));
    }
    zoneImport.append(h("div", { style: "margin:10px 0" },
      h("p", {}, h("strong", {}, "Avant : "), esp.personnes + " personnes  →  ",
        h("strong", {}, "Après remplacement : "), cmp.total_nouveau + " personnes"),
      h("p", {}, badge("+" + cmp.ajoutees.length + " nouvelles", "ok"), " ",
        cmp.modifiees.length ? badge("~" + cmp.modifiees.length + " modifiées", "info") : null, " ",
        cmp.disparues.length ? badge("−" + cmp.disparues.length + " absentes", "attention") : null)));
    // détail dépliable des personnes modifiées (champs touchés)
    if (cmp.modifiees.length) {
      const det = h("details", {}, h("summary", {}, "Voir les personnes modifiées"));
      const box = h("div", { class: "liste-pers compacte", style: "max-height:180px;overflow:auto" });
      cmp.modifiees.forEach((m) => box.append(h("div", { class: "ligne-pers" },
        h("span", {}, m.nom), h("span", { class: "meta" }, (m.champs || []).join(", ")))));
      det.append(box); zoneImport.append(det);
    }
    if (cmp.reduction_forte) {
      zoneImport.append(h("p", { style: "color:var(--alerte);font-weight:600" },
        "⚠ Le remplacement réduit fortement votre arbre. Préférez la fusion, ou "
        + "vérifiez que c'est bien voulu (une sauvegarde sera faite avant)."));
    }
    // Correspondance des lieux À L'IMPORT (Palier 2) : les lieux « à revoir »
    // (sans pays / doublons probables) sont proposés à la correction avant import.
    let collecterCorrections = () => ({});
    try {
      const lx = await apiJson("/api/import/gedcom/lieux", "POST", { octets_b64 });
      const aRevoir = (lx.lieux || []).filter((l) => l.sans_pays || l.doublon_de || l.parties_vides);
      if (aRevoir.length) {
        const refs = [];
        const det = h("details", { style: "margin:10px 0" },
          h("summary", {}, "🌍 Lieux à revoir — " + lx.nb_sans_pays
            + " sans pays, " + lx.nb_doublons + " doublon(s) probable(s)"));
        det.append(h("p", { class: "sous-titre", style: "margin:6px 0" },
          "Corrigez les lieux avant l'import (pays manquant, orthographe). "
          + "Laissez la valeur telle quelle pour ne rien changer."));
        if (lx.pays_defaut && lx.nb_sans_pays) {
          det.append(h("div", { class: "barre-actions", style: "margin:4px 0 8px" },
            h("button", { class: "bouton secondaire petit", onclick: () => {
              refs.forEach((r) => { if (r.l.sans_pays && r.l.propose) r.input.value = r.l.propose; });
              toast("« " + lx.pays_defaut + " » ajouté aux lieux sans pays.");
            } }, "🌍 Ajouter « " + lx.pays_defaut + " » aux lieux sans pays")));
        }
        const box = h("div", { class: "liste-pers compacte",
          style: "max-height:240px;overflow:auto" });
        aRevoir.forEach((l) => {
          const input = h("input", { type: "text", value: l.propose || l.nom,
            style: "flex:1;min-width:170px" });
          refs.push({ nom: l.nom, input, l });
          box.append(h("div", { class: "rangee",
            style: "gap:8px;padding:4px 0;align-items:center;flex-wrap:wrap" },
            h("span", { style: "min-width:130px;font-size:13px" }, l.nom),
            l.sans_pays ? badge("sans pays", "attention") : null,
            l.parties_vides ? badge("champ vide", "attention") : null,
            l.doublon_de ? badge("≈ " + l.doublon_de, "info") : null,
            input));
        });
        det.append(box);
        zoneImport.append(det);
        collecterCorrections = () => {
          const c = {};
          refs.forEach((r) => {
            const v = (r.input.value || "").trim();
            if (v && v !== r.nom) c[r.nom] = v;
          });
          return c;
        };
      }
    } catch { /* l'aperçu des lieux est un plus : ne jamais bloquer l'import */ }

    zoneImport.append(h("div", { class: "barre-actions" },
      h("button", { class: "bouton", onclick: async () => {
        try {
          const r = await apiJson("/api/import/gedcom/fusionner", "POST",
            { octets_b64, corrections_lieux: collecterCorrections() });
          const fam = [];
          if (r.familles_ajoutees) fam.push(r.familles_ajoutees + " familles ajoutées");
          if (r.familles_completees) fam.push(r.familles_completees + " complétées");
          const g7 = /^7(\.|$)/.test(String(r.version_fichier || "").trim());
          const sc = messageScans(r.scans);
          toast("Fusion réussie : +" + r.ajoutees + " personnes ajoutées, "
                + r.completees + " complétées"
                + (fam.length ? " · " + fam.join(", ") : "") + "." + sc
                + (g7 ? " ⚠ Fichier au format GEDCOM " + r.version_fichier
                        + " ; Arboriane lit le 5.5.1 : certaines informations "
                        + "récentes peuvent manquer." : ""),
                (g7 || (r.scans && r.scans.manquants)) ? { duree: 12000 } : undefined);
          input.value = ""; vider(zoneImport); aller("accueil");
        } catch (e) { toast(e.message); }
      }, title: "Ajoute et complète sans rien supprimer" }, "🔗 Fusionner (recommandé)"),
      h("button", { class: "bouton secondaire danger", onclick: async () => {
        if (!await confirmer(
          "Remplacer TOUT l'arbre actuel par le contenu de ce fichier ? Les "
          + "personnes actuelles seront retirées au profit de celles du fichier. "
          + "Une sauvegarde complète est faite juste avant, mais préférez "
          + "« Fusionner » si vous voulez conserver l'existant.",
          { titre: "Remplacer tout l'arbre", valider: "Remplacer", danger: true })) return;
        try {
          const r = await apiJson("/api/import/gedcom/appliquer", "POST",
            { octets_b64, corrections_lieux: collecterCorrections() });
          const bilan = bilanImport(r);
          toast(bilan.texte, bilan.alerte ? { duree: 12000 } : undefined);
          input.value = ""; vider(zoneImport); aller("accueil");
        } catch (e) { toast(e.message); }
      }, title: "Écrase l'arbre actuel" }, "Remplacer tout l'arbre"),
      h("button", { class: "bouton fantome", onclick: () => { input.value = ""; vider(zoneImport); } },
        "Annuler")));
  });

  vue.append(h("div", { class: "carte" },
    h("h2", {}, "📥 Importer un GEDCOM"),
    h("p", { class: "sous-titre" },
      "Depuis un autre logiciel. Arboriane vous montre d'abord ce qui changerait. "
      + "Vous pouvez FUSIONNER (ajoute et complète, sans rien perdre) ou remplacer "
      + "tout l'arbre. Une sauvegarde est faite avant."),
    h("button", { class: "bouton secondaire", onclick: () => input.click() },
      "Choisir un fichier .ged"),
    input, zoneImport));
}
