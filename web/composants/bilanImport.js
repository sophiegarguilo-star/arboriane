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

// r : { personnes, familles, sources, liens, liens_ignores, version_fichier, scans }
export function bilanImport(r) {
  const morceaux = [pluriel(r.personnes, "personne")];
  if (r.familles) morceaux.push(pluriel(r.familles, "famille"));
  if (r.sources) morceaux.push(pluriel(r.sources, "source"));
  const bilan = "Import réussi : " + morceaux.join(", ") + "." + messageScans(r.scans);

  if (estGedcom7(r.version_fichier)) {
    return { texte: bilan + " ⚠ Ce fichier est au format GEDCOM "
                    + r.version_fichier + " ; Arboriane lit le 5.5.1. Les "
                    + "personnes et les familles sont reprises, mais certaines "
                    + "informations récentes peuvent manquer. Réexportez depuis "
                    + "votre logiciel en GEDCOM 5.5.1 si vous le pouvez.",
             alerte: true };
  }
  if (r.personnes > 1 && !r.liens) {
    return { texte: bilan + " ⚠ Aucun lien de parenté n'a pu être lu : "
                    + "l'arbre sera vide. Signalez-le avec votre fichier.",
             alerte: true };
  }
  if (r.liens_ignores) {
    const n = r.liens_ignores;
    return { texte: bilan + " ⚠ " + pluriel(n, "lien") + " de parenté "
                    + (n > 1 ? "désignaient" : "désignait")
                    + " une personne absente du fichier : "
                    + (n > 1 ? "ils ont été ignorés." : "il a été ignoré."),
             alerte: true };
  }
  return { texte: bilan, alerte: !!(r.scans && r.scans.manquants) };
}
