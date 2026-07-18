// Garde-fou « format affichable ».
//
// Arboriane stocke les fichiers tels quels (aucune conversion : zéro
// dépendance). Or les navigateurs n'affichent PAS certains formats en <img> :
// une photo HEIC (iPhone), un scan TIFF ou un RAW d'appareil resteraient
// blancs. On prévient donc l'utilisateur AVANT l'envoi, au lieu de créer une
// vignette vide silencieuse.

const NON_AFFICHABLES = /\.(heic|heif|tiff?|arw|cr2|cr3|nef|orf|raf|rw2|dng|bmp3)$/i;

export function formatNonAffichable(nom) {
  return NON_AFFICHABLES.test(nom || "");
}

export const MSG_FORMAT_NON_AFFICHABLE =
  "Ce format ne s'affiche pas dans le navigateur (HEIC/photos iPhone, TIFF, RAW). "
  + "Convertissez la photo en JPEG ou PNG avant de l'ajouter.";
