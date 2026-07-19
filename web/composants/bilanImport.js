// Ce qu'on dit à l'utilisateur après un import GEDCOM.
//
// Un import peut « réussir » et pourtant ne rien relier : c'est arrivé (des
// pointeurs de parenté mal lus), et l'application annonçait fièrement ses
// centaines de personnes pendant que l'arbre restait vide. Un import muet qui
// perd la parenté est pire qu'un import qui échoue : on ne le découvre que des
// heures plus tard. On regarde donc les liens, pas seulement les personnes.

const pluriel = (n, mot) => n + " " + mot + (n > 1 ? "s" : "");

// Arboriane lit le GEDCOM 5.5.1. Un fichier 7.0 s'importe — la grammaire des
// lignes est la même — mais ses structures nouvelles sont perdues sans bruit.
// Mieux vaut l'annoncer que de laisser l'utilisateur découvrir le trou.
const estGedcom7 = (v) => /^7(\.|$)/.test(String(v || "").trim());

// Bilan des scans référencés par le fichier : « N copiés · M non retrouvés ».
// Un scan cité par un chemin (D:\…) est copié dans l'arbre s'il est présent sur
// CE PC ; sinon il est signalé comme à compléter (fréquent quand on importe le
// fichier de quelqu'un d'autre : ses images ne sont pas sur notre disque).
export function messageScans(scans) {
  if (!scans) return "";
  const c = scans.copies || 0, m = scans.manquants || 0;
  if (!c && !m) return "";
  let s = "";
  if (c) s += " · " + pluriel(c, "scan") + " importé" + (c > 1 ? "s" : "");
  if (m) s += " · ⚠ " + m + " image" + (m > 1 ? "s" : "") + " non retrouvée"
              + (m > 1 ? "s" : "") + " sur ce PC (à compléter dans « Qualité des sources »)";
  return s;
}

// Balises niveau 1-2 du fichier que le lecteur n'a pas reprises (PARC-11).
// `non_lues` = { TAG: n }. Renvoie { total, entrees } trié (plus fréquent
// d'abord), ou null s'il n'y a rien à dire.
export function resumeNonLues(non_lues) {
  const entrees = Object.entries(non_lues || {}).filter(([, n]) => n > 0);
  if (!entrees.length) return null;
  entrees.sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
  return { total: entrees.reduce((s, [, n]) => s + n, 0), entrees };
}

// Phrase courte pour le toast : total + balises les plus fréquentes + conseil.
export function messageNonLues(non_lues) {
  const r = resumeNonLues(non_lues);
  if (!r) return "";
  const s = r.total > 1 ? "s" : "";
  const tetes = r.entrees.slice(0, 4).map(([t, n]) => t + " ×" + n).join(", ");
  const reste = r.entrees.length > 4 ? "…" : "";
  return " ℹ " + r.total + " information" + s + " du fichier non reprise" + s
       + " (balise" + (r.entrees.length > 1 ? "s" : "") + " : " + tetes + reste
       + "). Conservez votre fichier .ged d'origine : rien n'y est perdu.";
}

// Dépliant « N informations non reprises (détail par balise) » pour les écrans
// d'import (aperçu détaillé, vague 2). Rend null hors navigateur ou sans perte.
export function depliantNonLues(non_lues) {
  const r = resumeNonLues(non_lues);
  if (!r || typeof document === "undefined") return null;
  const det = document.createElement("details");
  det.className = "depliant-non-lues";
  const sum = document.createElement("summary");
  sum.textContent = r.total + " information" + (r.total > 1 ? "s" : "")
                  + " non reprise" + (r.total > 1 ? "s" : "")
                  + " (détail par balise)";
  det.append(sum);
  const ul = document.createElement("ul");
  r.entrees.forEach(([tag, n]) => {
    const li = document.createElement("li");
    li.textContent = tag + " — " + n + " occurrence" + (n > 1 ? "s" : "");
    ul.append(li);
  });
  det.append(ul);
  const p = document.createElement("p");
  p.className = "sous-titre";
  p.textContent = "Ces balises du fichier ne sont pas comprises par Arboriane "
                + "et n'ont pas été importées. Conservez votre fichier .ged "
                + "d'origine : il reste la copie complète de ces informations.";
  det.append(p);
  return det;
}

// r : { personnes, familles, sources, liens, liens_ignores, version_fichier,
//       scans, non_lues }
export function bilanImport(r) {
  const morceaux = [pluriel(r.personnes, "personne")];
  if (r.familles) morceaux.push(pluriel(r.familles, "famille"));
  if (r.sources) morceaux.push(pluriel(r.sources, "source"));
  const bilan = "Import réussi : " + morceaux.join(", ") + "." + messageScans(r.scans)
              + messageNonLues(r.non_lues);
  // dépliant à insérer par les écrans d'import (le toast, lui, reste du texte)
  const detail = depliantNonLues(r.non_lues);

  if (estGedcom7(r.version_fichier)) {
    return { texte: bilan + " ⚠ Ce fichier est au format GEDCOM "
                    + r.version_fichier + " ; Arboriane lit le 5.5.1. Les "
                    + "personnes et les familles sont reprises, mais certaines "
                    + "informations récentes peuvent manquer. Réexportez depuis "
                    + "votre logiciel en GEDCOM 5.5.1 si vous le pouvez.",
             alerte: true, detail };
  }
  if (r.personnes > 1 && !r.liens) {
    return { texte: bilan + " ⚠ Aucun lien de parenté n'a pu être lu : "
                    + "l'arbre sera vide. Signalez-le avec votre fichier.",
             alerte: true, detail };
  }
  if (r.liens_ignores) {
    const n = r.liens_ignores;
    return { texte: bilan + " ⚠ " + pluriel(n, "lien") + " de parenté "
                    + (n > 1 ? "désignaient" : "désignait")
                    + " une personne absente du fichier : "
                    + (n > 1 ? "ils ont été ignorés." : "il a été ignoré."),
             alerte: true, detail };
  }
  // les informations non reprises justifient un toast plus long (alerte douce)
  return { texte: bilan,
           alerte: !!((r.scans && r.scans.manquants) || resumeNonLues(r.non_lues)),
           detail };
}
