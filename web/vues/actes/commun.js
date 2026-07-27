// Vocabulaire et petits outils partagés par les trois écrans « Actes / Sources »
// (liste, détail, formulaire). Rien d'affiché ici : que des constantes.
import { toast } from "../../composants/toast.js";

// Statuts de recherche d'une source — la valeur reste le code GEDCOM/technique,
// mais on affiche un libellé parlant pour une débutante.
export const STATUTS = ["RETENU", "PISTE", "ECARTE", "A TRANCHER", "NEGATIF"];
export const STATUT_LABEL = {
  RETENU: "Retenu (preuve validée)", PISTE: "Piste à explorer",
  ECARTE: "Écarté", "A TRANCHER": "À trancher (doute)",
  NEGATIF: "Recherche négative (rien trouvé)",
};

// Petites aides de saisie (placeholder) pour les champs d'une source.
export const AIDE_SOURCE = {
  date: "ex. 12/03/1902 ou 1902",
  cote: "ex. 5 Mi 123/4 — référence du registre aux archives (facultatif)",
  page: "ex. vue 42 / acte 3 (facultatif)",
  ark: "Collez le lien vers l'acte en ligne (Gallica, Geneanet, AD…)",
};

export const FIAB = { haute: "ok", moyenne: "info", basse: "attention" };

// Descripteurs du document (PROPRIÉTÉS, pas des types) — restent hors du nom de
// fichier ; miroir de services/taxonomie_actes.py.
export const FORMES = ["Original", "Extrait", "Copie", "Transcription", "Photocopie", "Photographie"];
export const COMPLETUDE = ["Complet", "Incomplet", "Fragment"];
export const VISIBILITE = ["Public", "Privé", "Sensible"];

// Vocabulaire canonique des types d'acte (menu déroulant — évite les fautes de
// frappe, et donne son code court au nom de fichier côté serveur).
export const TYPES_ACTE = [
  "Acte de naissance", "Acte de baptême", "Acte de mariage", "Mariage religieux",
  "Acte de décès", "Acte de sépulture", "Publication de mariage",
  "Livret de famille", "Matricule militaire", "Recensement", "Acte notarié",
  "Acte de notoriété", "Naturalisation", "Pierre tombale / sépulture", "Faire-part",
  "Presse / article", "Document",
];

// Rôles d'une personne dans un acte (qui est cité, et à quel titre).
export const ROLES = ["sujet", "père", "mère", "conjoint·e", "enfant",
                      "témoin", "fratrie", "autre"];

// Pièces jointes : images affichées en vignette ; PDF/TIFF affichés en « fichier »
// (icône + nom, ouvrable dans un onglet), car les navigateurs ne rendent pas le
// TIFF dans une <img> et le PDF n'est pas une image.
const _EXT_IMAGE = /\.(png|jpe?g|gif|webp|bmp|avif|svg)$/i;
export function estImageFichier(nom) { return _EXT_IMAGE.test(nom || ""); }
export function fichierAccepte(f) {
  return f.type.startsWith("image/") || f.type === "application/pdf"
    || /\.(pdf|tiff?)$/i.test(f.name || "");
}

export function lireBase64(fichier) {
  return new Promise((res) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.readAsDataURL(fichier);
  });
}

export function exportCsv(sources) {
  const entete = ["Titre", "Type", "Date", "Lieu", "Dépôt", "Cote", "Fiabilité", "Statut", "Scans"];
  const lignes = sources.map((s) => [s.titre, s.type, s.date, s.lieu, s.depot, s.cote,
    s.fiabilite, s.statut, s.nb_fichiers].map((v) => '"' + String(v || "").replace(/"/g, '""') + '"').join(";"));
  const csv = "﻿" + [entete.join(";")].concat(lignes).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "sources.csv";
  a.click();
  toast("Export CSV téléchargé.");
}
