# 🌳 Arboriane

**Un atelier local de généalogie sourcée.** Arboriane aide à transformer des
documents en preuves, des preuves en faits, et des faits en une histoire
familiale transmissible.

> **Locale · privée · sans cloud obligatoire · sans télémétrie.**
> Tout reste sur votre ordinateur. Aucune inscription, aucune donnée envoyée à
> votre insu. L'application ouvre une petite interface dans votre navigateur,
> mais le serveur n'écoute que sur `127.0.0.1` — rien ne sort de la machine.

🔎 **Présentation en ligne :** https://sophiegarguilo-star.github.io/arboriane/
*(GitHub Pages — voir le dossier `docs/`)*

---

## Ce que fait Arboriane

### 👥 Personnes & fiches
Fiches riches (noms multiples, surnoms, faits datés, professions, résidences,
notes biographiques), chronologie de vie, cellule familiale, portraits, et une
**recherche web pré-remplie** (le lien s'ouvre dans votre navigateur — aucune
donnée de l'arbre n'est transmise).

### 🌳 Arbre
Quatre rendus — **éventail, ascendance, descendance, tableau par génération** —
avec un panneau de personnalisation (thèmes, Sosa, professions, preuves colorées,
photos sur les cartes, fond, cadre, connecteurs…). Impression et export image,
et une **mosaïque A4 / A3 / A0** pour afficher un grand arbre au mur.

### 📄 Sources & preuves
Modèle de preuve complet : sources typées, **citations qualifiées** (acte /
déclaré / estimé), transcriptions, visionneuse d'actes, et un 3ᵉ niveau de
sourçage — les **dépôts d'archives** (Dépôt → Source → Citation), exportés en
GEDCOM (REPO).

### 🗺️ Lieux
Carte des lieux (géocodage **optionnel**, opt-in, qui n'envoie que des noms de
communes) et un **référentiel des lieux** hiérarchique (commune → département →
pays) avec **noms datés** (une commune renommée garde son nom d'époque). Une
commune seule ou un pays seul sont des états parfaitement valides.

### 🧭 Analyse généalogique
Sosa à la volée et **Sosa permanent**, parenté entre deux personnes, **implexe**,
**consanguinité**, numérotation **d'Aboville**, chronologie multi-personnes et
contemporains.

### 🩺 Qualité de l'arbre
Écrans **Cohérence**, **Santé de l'arbre** et **Qualité des sources** : anomalies
de dates, fichiers manquants, actes à transcrire, sexes/noms à compléter, plan de
recherche par dépôt. Plus **fusion assistée** des doublons de personnes et de
lieux.

### 📋 Listes, favoris, carnet
Index des métiers, unions, ascendance/descendance textuelles, éphéméride des
naissances (tous exportables en CSV), **favoris & ensembles** de personnes, et un
**carnet de bord** de recherche.

### 🔄 Interopérabilité GEDCOM
Import / export **GEDCOM 5.5.1** fidèle (aller-retour préservé), détection
d'encodage, validation des dates, **calendrier républicain**, et un export
**autoporteur** (images embarquées).

---

## Découvrir

Au premier lancement, ouvrez l'**arbre de démonstration** (famille 100 % fictive,
~90 personnes sur 12 générations) : sources et actes-spécimens, dépôts, lieux
géocodés, carte, référentiel, favoris, portraits, et quelques cas de test pour
les écrans Cohérence et Santé. Rien de réel, aucune dépendance externe.

## Lancer

- **Windows, sans rien installer** : double-clic sur `Arboriane.exe`.
- **Avec Python** (3.11+) : `python app.py`, ou double-clic sur `lanceur.py`
  (petite fenêtre, sans console).

Le serveur choisit un port libre à partir de `8770` et ouvre votre navigateur.
Une seule instance à la fois (un second lancement rouvre la fenêtre existante).

## Architecture

Zéro dépendance externe : Python **standard library** au dos, JavaScript
**vanilla** (modules ES) au front.

```
app.py            serveur local (127.0.0.1) : routage, sécurité, fichiers statiques
core/             noyau métier sans HTTP (modèle, stockage, espace, gedcom, version…)
routes/           API HTTP — une déclaration @route par point d'entrée
services/         logique métier (arbre, sources, dépôts, lieux, fusion, démo…)
web/              interface vanilla — noyau/ (dom, api, état), composants/, vues/
  styles/style.css   la charte graphique (voir docs/charte-graphique.md)
docs/             documentation (charte graphique, notre GEDCOM) + page de présentation
tests/            tests (sans serveur) — exécuter chaque tests/test_*.py
```

**Un arbre = un dossier** autonome (`arboriane.json`, `Sources/`, `Photos/`,
`GEDCOM/`, `Sauvegardes/`, `Carnet/`…). Arboriane lit et écrit **uniquement** dans
ce dossier, avec sauvegardes horodatées automatiques.

## Tests

```
python -X utf8 tests/test_socle.py     # (ou n'importe quel tests/test_*.py)
```

Le noyau frontend a ses propres tests, sans dépendance (lanceur intégré de
Node) :

```
node --test tests/js/test_*.mjs
```

Les suites tournent automatiquement à chaque poussée (GitHub Actions, Windows).
Avant toute publication, une barrière refuse de publier si une suite (Python ou
JavaScript) échoue, si l'export GEDCOM n'est pas conforme à la norme 5.5.1, si le
`CHANGELOG.md` est périmé, si la version est déjà publiée, ou si un banc de
non-régression détecte le moindre changement dans l'import d'un corpus de
fichiers GEDCOM réels, produits par d'autres logiciels de généalogie.

Le [journal des versions](CHANGELOG.md) est **généré** depuis les notes de
l'application : `python -X utf8 outils/generer_changelog.py`.

## Vérifier le téléchargement

Arboriane **n'est pas signé numériquement** : Windows affichera « éditeur
inconnu » à l'installation. Chaque version publie l'empreinte **SHA-256** de son
installateur. Pour vérifier que le fichier reçu est bien celui construit à partir
de ce code :

```powershell
Get-FileHash .\Installer-Arboriane.exe -Algorithm SHA256
```

Le résultat doit correspondre à l'empreinte affichée sur la
[page de la dernière version](https://github.com/sophiegarguilo-star/arboriane/releases/latest).

## Sécurité & vie privée

- serveur limité à `127.0.0.1` ; contrôle Host/Origin sur toute mutation ;
- `Content-Type: application/json` exigé pour les mutations ; corps ≤ 32 Mo ;
- écriture atomique + sauvegardes automatiques avant les actions sensibles ;
- clé de l'assistant (facultatif) chiffrée localement (DPAPI) ;
- **aucune donnée personnelle dans ce dépôt** (voir `.gitignore`).

Une faille de sécurité se signale en privé, jamais par une issue publique : voir
[SECURITY.md](SECURITY.md).

## Licence

**GNU Affero General Public License v3.0** — voir [LICENSE](LICENSE).

Vous pouvez utiliser, étudier, modifier et redistribuer Arboriane. Si vous en
distribuez une version modifiée, ou si vous la proposez comme service accessible
par un réseau, vous devez publier votre code source sous la même licence. Cette
réciprocité est délibérée : Arboriane est locale, privée et gratuite, et doit le
rester pour celles et ceux qui en hériteront.

## Contact

arboriane.app@gmail.com

---

© 2026 Sophie Garguilo — sous licence AGPL v3.
