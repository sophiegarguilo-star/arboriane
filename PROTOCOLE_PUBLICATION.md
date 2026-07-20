# Protocole de publication d'Arboriane

> **Pourquoi ce document.** Les versions 1.9.11 (formulaires blancs) et 1.9.12
> (démarrage cassé, publié en « Latest ») ont laissé passer des régressions
> qu'aucun test ne pouvait voir : les tests validaient le back-end et l'API,
> **jamais l'affichage réel des écrans**. Un « API qui répond 200 » ne prouve
> pas qu'un écran s'affiche. Ce protocole ferme ce trou, en profondeur.

Un bug doit franchir **4 couches** avant d'atteindre un utilisateur.

---

## Couche 1 — La machine refuse de *construire* du code qui ne se parse pas

Test : **`tests/js/test_syntaxe_vues.mjs`**
Passe chaque `web/**/*.js` (app.js inclus) à `node --check --input-type=module`.
Attrape **toute `SyntaxError`** — dont le doublon de déclaration qui a tué le
démarrage en 1.9.12. Contrôle de syntaxe pur : aucune exécution, aucun DOM.

## Couche 2 — La machine refuse de *publier* une app dont un écran ne charge pas

Deux tests complémentaires :

- **`tests/js/test_vues_chargent.mjs`** — importe réellement chaque vue et
  composant sous un stub DOM. Attrape ce qui se parse mais échoue au
  **chargement** : chemin d'import erroné, symbole importé non exporté, erreur
  levée au niveau haut d'un module.
- **`tests/js/test_imports_vues.mjs`** — analyse statique : signale toute vue qui
  **appelle un helper partagé sans l'importer** (le `ReferenceError` au rendu qui
  a rendu les formulaires blancs en 1.9.11 ; invisible pour un simple import).

> Ces trois tests vivent dans `tests/js/test_*.mjs` : **la barrière du déployeur
> (`outils/deployer.py`) les lance automatiquement** et refuse de publier si l'un
> rougit. Chacun a été prouvé « rouge sur le bug, vert sinon ».

## Couche 3 — Un humain *voit* que ça marche avant que ce soit « Latest »

- **Deux canaux : `bêta` (pré-version) → `stable` (Latest).** Rien ne devient
  « Latest » sans avoir d'abord tourné en bêta. (`core/version.py` gère déjà
  `CANAL`, et GitHub distingue pré-version / Latest.)
- **Checklist pré-publication** : ouvrir **chaque écran modifié** dans l'app
  construite et vérifier zéro erreur dans la console du navigateur.
- Publication toujours **sous les yeux de Sophie**, jamais à l'aveugle.

## Couche 4 — Si ça glisse quand même : retour arrière en une commande

- **Une release = un commit propre** (`Arboriane X.Y.Z`), un tag `vX.Y.Z`.
- Rollback = rebasculer « Latest » sur la version précédente + revert d'**un**
  commit. Éprouvé le 2026-07-20 : de « Latest cassé » à « 1.9.10 propre partout »
  en quelques minutes.

---

## Règles de travail (les erreurs *humaines* qui amplifient)

1. **Lire le fichier entier avant de l'éditer** (le doublon de 1.9.12 venait d'un
   fichier édité sans voir qu'il définissait déjà la fonction localement).
2. **Tout correctif = un test rouge AVANT, vert APRÈS.** Pas de correctif sans preuve.
3. **Vérifier le CODE, jamais la mémoire.** (La note « depots.js déjà cassé » était fausse.)
4. **Ne jamais copier-coller un correctif** d'un fichier à l'autre sans vérifier chaque cas.
5. **Petites releases**, pas des sauts de 100+ fichiers d'un coup.
6. **Aucune publication sans le feu vert explicite de Sophie.**

---

## Comment lancer les garde-fous

```bash
# toute la batterie JavaScript (ce que fait la barrière)
node --test tests/js/test_*.mjs

# la barrière complète + build + déploiement LOCAL (sans publier)
python -X utf8 outils/deployer.py

# publication (barrière + build + installeur + release GitHub)
python -X utf8 outils/deployer.py --release
```

La barrière est **bloquante** : si un test échoue, ni le build ni la publication
ne se font.
