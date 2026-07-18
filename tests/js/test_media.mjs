// Garde-fou « format affichable » (web/composants/media.js).
//
// Arboriane ne convertit pas les images (zéro dépendance). Les formats que les
// navigateurs n'affichent pas — HEIC (iPhone), TIFF, RAW — doivent être repérés
// AVANT l'envoi, sinon la photo reste une vignette blanche silencieuse.
//
//   node --test tests/js/test_media.mjs
import { test } from "node:test";
import assert from "node:assert/strict";

const { formatNonAffichable, MSG_FORMAT_NON_AFFICHABLE } =
  await import("../../web/composants/media.js");

test("HEIC (photo iPhone) est refusé", () => {
  assert.equal(formatNonAffichable("20251231_235135858_iOS.heic"), true);
  assert.equal(formatNonAffichable("photo.HEIC"), true);
  assert.equal(formatNonAffichable("image.heif"), true);
});

test("TIFF et RAW sont refusés", () => {
  for (const n of ["scan.tif", "scan.tiff", "photo.arw", "photo.cr2", "photo.nef", "photo.dng"]) {
    assert.equal(formatNonAffichable(n), true, n);
  }
});

test("les formats web classiques passent", () => {
  for (const n of ["photo.jpg", "photo.jpeg", "image.png", "anim.gif", "moderne.webp", "moderne.avif", "acte.pdf"]) {
    assert.equal(formatNonAffichable(n), false, n);
  }
});

test("un message d'aide clair est fourni", () => {
  assert.match(MSG_FORMAT_NON_AFFICHABLE, /HEIC/);
  assert.match(MSG_FORMAT_NON_AFFICHABLE, /JPEG|PNG/);
});
