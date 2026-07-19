# Construire et publier Arboriane

Comment reconstruire l'exécutable et l'installeur, à l'identique, sur une
machine propre — et comment publier une version. **Une seule commande fait
tout** ; ne jamais publier « à la main » (voir plus bas).

## Prérequis exacts

| Outil | Version | Emplacement attendu |
|---|---|---|
| Python | 3.14 (build actuel : 3.14.6) | `python` dans le PATH |
| PyInstaller | 6.x (build actuel : 6.21.0) | `python -m PyInstaller` |
| Inno Setup 6 | 6.x | `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` |
| GitHub CLI (`gh`) | authentifié sur le dépôt | `C:\Program Files\GitHub CLI\gh.exe` |
| Git | quelconque récent | `git` dans le PATH |

Arboriane n'a **aucune dépendance Python externe** (stdlib pure) : seul
PyInstaller est à installer (`python -m pip install pyinstaller`).

Les chemins d'ISCC et de gh sont codés dans `outils/deployer.py` (constantes
`ISCC` et `GH`) : si votre installation diffère, ajustez-les là.

À chaque build, le déployeur écrit `dist/build-info.txt` (versions de Python,
PyInstaller, Inno Setup + date + version d'Arboriane) : c'est la carte
d'identité du binaire, à conserver pour pouvoir reconstruire pareil plus tard.

## La commande unique

```
python -X utf8 outils/deployer.py             # build + déploiement local + vérif
python -X utf8 outils/deployer.py --release   # idem + installeur + publication GitHub
```

Le déployeur enchaîne, dans l'ordre, et S'ARRÊTE à la moindre anomalie :

1. **Barrière** : toutes les suites de tests (`tests/test_*.py`), tests JS,
   et — pour `--release` — arbre git PROPRE exigé, corpus GEDCOM, conformité
   5.5.1 de l'export, CHANGELOG.md à jour **et aligné sur `core/version.py`** ;
2. synchronisation du numéro de version (source unique `core/version.py`) ;
3. build PyInstaller propre (purge des `__pycache__`) + `dist/build-info.txt` ;
4. déploiement local + vérification route par route (contrôle du PID) ;
5. (`--release`) compilation de l'installeur Inno Setup, empreinte SHA-256,
   **un seul commit « Arboriane X.Y.Z »** (inclut la page `docs/index.html`),
   tag `vX.Y.Z`, push, puis création de la release GitHub ciblée sur ce tag.

## Ce que le build ne touche JAMAIS

Le build et la vérification n'ouvrent **aucune donnée utilisateur** : la
vérification lance l'exe dans un dossier temporaire isolé
(`ARBORIANE_DONNEES` pointé sur un dossier jetable, supprimé ensuite).
`D:\Arboriane\Mes arbres`, `Documents`, réglages : intouchés. Le déploiement
vers les emplacements lancés copie le PROGRAMME uniquement (`robocopy /E`,
jamais `/MIR`).

## Interdits

- **Publier à la main avec `gh`** (`gh release create` / `upload` depuis un
  terminal) : c'est ainsi que la v1.9.10 est partie sans tests, sans tag et
  sans notes de version. Seul `outils/deployer.py --release` publie.
- **Remplacer un binaire publié** (`--clobber`) : un fichier téléchargé par
  les utilisateurs ne change jamais sous un même numéro (l'empreinte SHA-256
  publiée s'y fie). Pour corriger : monter `VERSION` dans `core/version.py`,
  ajouter ses notes dans `services/maj.py`, republier.
- `--sans-barriere` : dépannage local uniquement, jamais pour publier
  (`publier()` refuse de toute façon si l'arbre n'a pas été contrôlé propre).

## Politique de rétention des versions en ligne

**Conserver en ligne N-1 et N-2** (les deux versions précédant la courante),
supprimer les plus anciennes : assez pour redescendre d'une version en cas de
régression, sans laisser traîner de vieux binaires bogués téléchargeables.
Conséquence : aucun document ne doit pointer vers l'URL d'une release
ancienne — le CHANGELOG.md généré utilise des ancres internes, pas des liens
de tags.

## Revenir à la version précédente (pour l'utilisateur)

Si une mise à jour pose problème :

1. Télécharger l'installeur de la version précédente (N-1) sur la page des
   releases GitHub (elle reste en ligne, voir la rétention ci-dessus) ;
2. L'exécuter tel quel : il réinstalle par-dessus, **les données (« Mes
   arbres », réglages, scans) sont conservées** — elles vivent hors du
   dossier programme et l'installeur n'y touche jamais ;
3. Au besoin, une sauvegarde `.zip` faite depuis l'application se recharge
   via « Restaurer une sauvegarde ».
