# Charte graphique d'Arboriane

> Outil de généalogie **sobre et chaleureux**. Dense mais lisible, jamais
> tape-à-l'œil. Tout est local, aucune ressource externe (polices système,
> zéro CDN). La feuille `web/styles/style.css` est la **source de vérité** ;
> ce document explique quoi utiliser et quand.

## 1. Esprit

- **Chaleureux, pas clinquant** : vert profond + ivoire + une pointe de
  terracotta. On évite le bleu « logiciel », les dégradés criards, les ombres
  lourdes.
- **Le contenu d'abord** : la couleur souligne, elle ne décore pas. Une seule
  action principale par écran (terracotta) ; le reste est discret.
- **Cohérence** : on **réutilise les composants** de la charte plutôt que de
  bricoler du style en ligne. Un bouton se ressemble partout, un état vide
  aussi.

## 2. Couleurs (tokens `--var`, jamais de `#hex` en JS)

| Rôle | Token | Valeur |
|---|---|---|
| Vert profond (nav, titres) | `--vert` | `#1f4636` |
| Vert clair | `--vert-clair` | `#2d5c47` |
| Sauge / sauge pâle (fonds doux) | `--sauge` / `--sauge-pale` | `#8ba58d` / `#e4ece1` |
| Ivoire (fond de page) | `--ivoire` | `#f7f4ec` |
| Blanc cassé (cartes) | `--blanc` | `#fffdf8` |
| **Terracotta (action principale)** | `--accent` | `#c76b2a` |
| Or / pâle (accents secondaires) | `--accent-or` / `--accent-pale` | `#d99a3c` / `#f3e4d2` |
| Texte / gris / gris clair | `--texte` / `--gris` / `--gris-clair` | `#2a2b28` / `#6b7280` / `#9aa0a6` |
| Bordures | `--bord` | `#e4e1d6` |
| Homme / femme (pastilles) | `--homme` / `--femme` | `#d2e2f1` / `#f2d9e2` |
| Homme / femme / inconnu (barres, frises) | `--sexe-h` / `--sexe-f` / `--sexe-u` | `#7fa6c6` / `#cfa9b8` / `#a7bfa0` |
| OK / alerte | `--ok` / `--alerte` | `#3d7a54` / `#b3541e` |

**Règle d'or : aucune couleur en dur dans le JS.** Toujours `var(--token)`.
Pour Leaflet/canvas (qui n'accepte pas `var()`), lire une fois
`getComputedStyle(document.documentElement).getPropertyValue('--accent')`.

## 3. Typographie & rythme

- **Titres** : `--serif` (Georgia). `h1` de vue = 27px ; `h2` de carte = 18px ;
  sous-titres de section en serif vert.
- **Corps** : `--sans` (system-ui), 15px, interligne 1.5.
- **Rayon** : `--rayon` (10px). **Ombre** : `--ombre` (douce, verte).
- Espacements en multiples cohérents (gap 6 / 8 / 10 / 14 px). On évite les
  valeurs arbitraires (`margin:.7rem`, `gap:13px`…).

## 4. Composants (réutiliser, ne pas réinventer)

### Structure
- **`.carte`** — bloc de contenu (fond blanc, bord, ombre). Titre = `.carte h2`
  (serif). Variante **`.carte.compacte`** (padding/marge réduits).
- **`.grille-cartes`** — grille responsive de cartes (`auto-fit minmax(240px)`).
  Variante `.grille-cartes.large` (300px). *(`.grille-arbres` = variante espaces.)*
- **`.stats` / `.stat`** — bandeau de chiffres clés. **`.kpis` / `.kpi`** —
  cartes chiffrées du tableau de bord.

### Actions
- **`.bouton`** — action **principale** (terracotta plein). Un seul par écran
  idéalement.
- **`.bouton.secondaire`** — action secondaire (ivoire, texte vert, bord).
- **`.bouton.danger`** — suppression (jamais `style="color:var(--alerte)"` :
  utiliser la classe). **`.bouton.petit`** — version compacte.
- **`.lien`** — action en lien texte. **`.lien.danger`** — retrait/suppression discret.
- **`.barre-actions`** — rangée de boutons (flex, retour à la ligne, gap 10).

### Mise en page (utilitaires)
- **`.rangee`** — rangée flex alignée (variantes `.serre` gap 6, `.haut` haut).
- **`.pousse`** — pousse un élément à droite (`margin-left:auto`).
- **`.separateur`** — filet horizontal. **`.liste-defilante`** — hauteur bornée.
- **`.sur-titre`** — petite étiquette majuscule (catégorie/groupe).
- **`.sous-onglets` / `.sous-onglet`** — bascules internes à une vue.

### Données
- **`.def-ligne` / `.def-cle` / `.def-val`** — paires clé/valeur (fiches, sources).
- **`.ligne-pers` / `.liste-pers`** (`.compacte`) — listes de personnes.
- **`.badge`** (`.info` / `.ok` / `.attention`) — étiquettes.
- **`.pastille-sexe.M/.F`** — point de couleur. **`.barre-progres`** — jauge.
- **`.legende` / `.legende-item` / `.legende-pastille`** — légendes de carte/graphe.
- **`.repere`**, **`.timeline` / `.tl-item`**, **`.chrono-ligne`** — repères & frises.

### États & retours
- **`.vide`** — **état vide standard** (centré, pointillé, `.grand` pour l'emoji).
  Variante **`.vide.compacte`** dans une carte.
- **`.message`** — statut/info discret dans une carte (« Calcul… », petit vide).
- **`.encart`** (`.attention` / `.astuce` / `.aretenir`) — encadrés d'aide.
- **`.toast`** — notification fugace. **`.chargeur`** — spinner.

### Saisie
- `input / select / textarea` sont stylés globalement. **`.champ`** = un champ
  (label + contrôle). **`.champ-couleur`** = sélecteur de couleur normalisé.
- **`.form-perso` / `.form-actions`** — formulaire à barre d'action collante.
- **`.liste-rep` / `.rep-ligne` / `.rep-x`** — listes répétables.
- **`.bloc-avance`** — section repliable (`<details>`).

### Surfaces
- **`.modale`**, **`.volet`**, **`.visio`** (visionneuse) — overlays, avec leurs
  fonds et animations. **`.fiche-onglets` / `.fiche-onglet`** — onglets de fiche.

## 5. Lieux partiels — un état légitime

Un lieu **incomplet n'est pas une erreur**. On accepte :
- **commune seule** (« Marseille ») → traitée comme commune, géocodable ;
- **pays seul** (« Algérie », « Malte », « Macédoine du Nord ») → traité comme
  pays, géocodé au centre du pays.

La saisie du champ *lieu* est **libre** ; le référentiel des lieux (L15) type
automatiquement chaque partie (`lieu-dit → commune → département → région →
pays`) et sait qu'une chaîne à une seule partie peut être une commune **ou** un
pays (liste `_PAYS`). On ne réclame jamais les parties manquantes.

## 6. Filet de sécurité

Un `<button>` sans classe reçoit automatiquement l'aspect « secondaire »
(`button:not([class])`), pour ne jamais retomber sur le bouton gris du
navigateur. Mais **on met toujours la bonne classe explicitement**.

## 7. Accessibilité & impression

- Focus visible partout (`outline` or/terracotta).
- `@media (prefers-reduced-motion)` coupe les animations.
- `@media print` masque nav/overlays et allège les cartes.
