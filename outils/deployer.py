# -*- coding: utf-8 -*-
"""
Déployeur Arboriane — build + déploiement + VÉRIFICATION reproductibles.

Encode le processus sûr (et la leçon apprise le 2026-07-08) :
  1. synchronise le numéro de version depuis core/version.py (source unique) ;
  2. purge les __pycache__ (évite le bytecode périmé) ;
  3. reconstruit l'exe (PyInstaller) ;
  4. arrête les instances d'Arboriane.exe en cours ;
  5. déploie vers %LOCALAPPDATA%\\Programs\\Arboriane (robocopy, désinstalleur
     préservé) ;
  6. VÉRIFIE l'exe déployé route par route EN CONFIRMANT QUE LE PID DE L'EXE
     POSSÈDE LE PORT testé — parade au faux « 404 » causé par un vieux serveur
     qui squatte le port.

Usage :
  python -X utf8 outils/deployer.py             # build + déploiement + vérif (local)
  python -X utf8 outils/deployer.py --release   # + installeur Inno + upload GitHub
  python -X utf8 outils/deployer.py --verif     # vérifie seulement l'exe déployé
  python -X utf8 outils/deployer.py --no-build  # déploie l'exe déjà construit

IMPORTANT (leçon 2026-07-09) : pour DISTRIBUER une correction, utiliser --release.
Sans lui, seul l'exe LOCAL est à jour ; l'installeur publié reste périmé et les
utilisateurs téléchargent l'ancienne version. --release recompile l'installeur et
le ré-uploade, en refusant tout asset plus ancien que le dernier commit.
"""

import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
from core.version import VERSION            # noqa: E402

DIST = os.path.join(RACINE, "dist", "Arboriane")
INSTALL = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Arboriane")
# Emplacements où l'app est réellement LANCÉE (raccourci Bureau, variable
# ARBORIANE_DONNEES=D:\Arboriane) : on y déploie aussi le programme pour ne pas
# tester une version périmée. Données préservées (robocopy /E, jamais /MIR).
EMPLACEMENTS_LANCES = (r"D:\Arboriane",)
INSTALLEUR = os.path.join(RACINE, "dist", "Installer-Arboriane.exe")
ISCC = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
DEPOT = "sophiegarguilo-star/arboriane"
_NO_WINDOW = 0x08000000


def log(msg):
    print("[deployer] " + msg, flush=True)


# ── 1. Synchroniser la version (source unique core/version.py) ───────────
def sync_version():
    maj, mineur, corr = (VERSION.split(".") + ["0", "0", "0"])[:3]
    tup = "(%s, %s, %s, 0)" % (maj, mineur, corr)
    vi = os.path.join(RACINE, "version_info.txt")
    if os.path.isfile(vi):
        t = open(vi, encoding="utf-8").read()
        t = re.sub(r"filevers=\([^)]*\)", "filevers=" + tup, t)
        t = re.sub(r"prodvers=\([^)]*\)", "prodvers=" + tup, t)
        t = re.sub(r"(StringStruct\('FileVersion', ')[^']*(')", r"\g<1>%s\g<2>" % VERSION, t)
        t = re.sub(r"(StringStruct\('ProductVersion', ')[^']*(')", r"\g<1>%s\g<2>" % VERSION, t)
        open(vi, "w", encoding="utf-8").write(t)
        log("version_info.txt -> %s" % VERSION)
    iss = os.path.join(RACINE, "installateur.iss")
    if os.path.isfile(iss):
        t = open(iss, encoding="utf-8").read()
        t2 = re.sub(r'(#define\s+AppVersion\s+")[^"]*(")', r"\g<1>%s\g<2>" % VERSION, t)
        if t2 != t:
            open(iss, "w", encoding="utf-8").write(t2)
            log("installateur.iss -> %s" % VERSION)


# ── 2+3. Build ───────────────────────────────────────────────────────────
def purger_pycache():
    for base, dirs, _ in os.walk(RACINE):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(base, d), ignore_errors=True)


def build():
    purger_pycache()
    log("PyInstaller (build propre)…")
    r = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                        "--clean", "Arboriane.spec"], cwd=RACINE)
    if r.returncode != 0:
        raise SystemExit("Build échoué (code %d)." % r.returncode)
    if not os.path.isfile(os.path.join(DIST, "Arboriane.exe")):
        raise SystemExit("Build : Arboriane.exe introuvable.")
    ecrire_build_info()
    log("build OK")


def _version_pyinstaller():
    try:
        import PyInstaller
        return getattr(PyInstaller, "__version__", "inconnue")
    except Exception:
        return "inconnue"


def _version_iscc():
    """Version d'ISCC.exe lue dans les métadonnées du fichier (PowerShell)."""
    if not os.path.isfile(ISCC):
        return "absente"
    ps = "(Get-Item '%s').VersionInfo.ProductVersion" % ISCC.replace("'", "''")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, creationflags=_NO_WINDOW)
    return (r.stdout or "").strip() or "inconnue"


def ecrire_build_info(dossier=None):
    """Écrit dist/build-info.txt : avec QUOI ce binaire a été construit.

    Reproductibilité (voir BUILD.md) : des mois plus tard, on doit pouvoir
    reconstruire le même binaire — donc savoir quelles versions de Python,
    PyInstaller et Inno Setup ont servi. Écrit à CHAQUE build."""
    dossier = dossier or os.path.join(RACINE, "dist")
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, "build-info.txt")
    lignes = [
        "Arboriane   : %s" % VERSION,
        "date        : %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "python      : %s" % sys.version.split()[0],
        "pyinstaller : %s" % _version_pyinstaller(),
        "inno setup  : %s" % _version_iscc(),
    ]
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lignes) + "\n")
    log("build-info.txt écrit -> %s" % chemin)
    return chemin


# ── 4+5. Déploiement ─────────────────────────────────────────────────────
def arreter_instances():
    subprocess.run(["taskkill", "/F", "/IM", "Arboriane.exe"],
                   capture_output=True, creationflags=_NO_WINDOW)
    time.sleep(0.7)


def deployer():
    if not INSTALL:
        raise SystemExit("LOCALAPPDATA introuvable.")
    arreter_instances()
    log("robocopy -> %s" % INSTALL)
    # sortie brute (bytes) : robocopy écrit en cp1252/OEM, ne pas décoder en utf-8
    r = subprocess.run(["robocopy", DIST, INSTALL, "/E", "/NFL", "/NDL",
                        "/NP", "/R:2", "/W:1"], capture_output=True)
    if r.returncode >= 8:                    # robocopy : <8 = succès
        raise SystemExit("robocopy a échoué (code %d)." % r.returncode)
    log("déploiement OK (désinstalleur %s)" %
        ("préservé" if os.path.isfile(os.path.join(INSTALL, "unins000.exe")) else "absent"))
    # Emplacements RÉELLEMENT lancés (raccourci Bureau -> D:\Arboriane). Sans ça,
    # on testerait une version périmée. On met à jour le PROGRAMME uniquement
    # (/E, jamais /MIR) : les données (« Mes arbres ») restent intactes.
    for extra in EMPLACEMENTS_LANCES:
        if os.path.isdir(extra) and os.path.exists(os.path.join(extra, "Arboriane.exe")):
            log("robocopy (emplacement lancé) -> %s" % extra)
            rr = subprocess.run(["robocopy", DIST, extra, "/E", "/NFL", "/NDL",
                                 "/NP", "/R:2", "/W:1"], capture_output=True)
            if rr.returncode >= 8:
                log("  ⚠ échec robocopy vers %s (code %d) — ignoré" % (extra, rr.returncode))


# ── 6. Vérification avec contrôle du PID ─────────────────────────────────
def _pid_du_port(port):
    """PID qui ÉCOUTE sur ce port (via PowerShell). None si aucun."""
    ps = ("$c = Get-NetTCPConnection -State Listen -LocalPort %d "
          "-ErrorAction SilentlyContinue | Select-Object -First 1; "
          "if ($c) { $c.OwningProcess }" % port)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, creationflags=_NO_WINDOW)
    out = (r.stdout or "").strip()
    return int(out) if out.isdigit() else None


def _get(url, origin):
    req = urllib.request.Request(url, headers={"Origin": origin})
    with urllib.request.urlopen(req, timeout=6) as rep:
        return rep.status, rep.read().decode("utf-8", "replace")


def _post(url, origin):
    req = urllib.request.Request(url, data=b"{}",
                                 headers={"Origin": origin,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as rep:
        return rep.status


def verifier(exe=None):
    exe = exe or os.path.join(INSTALL, "Arboriane.exe")
    if not os.path.isfile(exe):
        raise SystemExit("Exe à vérifier introuvable : %s" % exe)
    datadir = tempfile.mkdtemp(prefix="arbo_verif_")
    env = dict(os.environ, ARBORIANE_DONNEES=datadir,
               ARBORIANE_SANS_NAVIGATEUR="1")
    log("lancement de l'exe déployé (dossier de test isolé)…")
    proc = subprocess.Popen([exe], env=env, creationflags=_NO_WINDOW)
    echecs = []
    try:
        port = None
        pf = os.path.join(datadir, "donnees", "port.txt")
        for _ in range(50):
            time.sleep(0.4)
            if os.path.isfile(pf):
                port = (open(pf).read().strip() or None)
                if port:
                    break
        if not port:
            raise SystemExit("Le serveur de l'exe n'a pas démarré.")
        port = int(port)
        proprio = _pid_du_port(port)
        if proprio != proc.pid:
            raise SystemExit("Le port %d n'appartient PAS à l'exe testé "
                             "(PID port=%s, exe=%s) : vérif non fiable, "
                             "un autre serveur squatte le port." %
                             (port, proprio, proc.pid))
        log("port %d possédé par l'exe (PID %d) — vérif fiable" % (port, proc.pid))
        origin = "http://127.0.0.1:%d" % port
        _post("%s/api/espaces/demo" % origin, origin)      # charge la démo

        # version servie == source unique ?
        _, corps = _get("%s/api/version" % origin, origin)
        if ('"%s"' % VERSION) not in corps:
            echecs.append("/api/version ne renvoie pas %s (%s)" % (VERSION, corps[:60]))

        routes = ["/api/systeme", "/api/verif", "/api/depots", "/api/lieux-ref",
                  "/api/index-metiers", "/api/date/convertir?texte=12%20germinal%20an%20III",
                  "/api/fusion/doublons", "/api/fusion/lieux", "/api/favoris"]
        for r in routes:
            try:
                code, _ = _get(origin + r, origin)
                marque = "ok  " if code == 200 else "HTTP %s" % code
                if code != 200:
                    echecs.append("%s -> %s" % (r, code))
            except Exception as e:
                marque = "ERREUR"
                echecs.append("%s -> %s" % (r, e))
            log("  %-8s %s" % (marque, r.split("?")[0]))

        # café retiré du tableau de bord ?
        _, js = _get("%s/vues/tableau.js" % origin, origin)
        if "accueil-banniere" in js:
            echecs.append("bannière café encore présente dans tableau.js")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        shutil.rmtree(datadir, ignore_errors=True)

    if echecs:
        log("VÉRIFICATION ÉCHOUÉE :")
        for e in echecs:
            log("   ✗ " + e)
        raise SystemExit(1)
    log("VÉRIFICATION OK — toutes les routes répondent 200 sur le bon PID.")


# ── 7. Installeur + publication GitHub (publication ATOMIQUE) ────────────
# La leçon du 2026-07-09 : reconstruire l'exe en local NE SUFFIT PAS ; tant que
# l'installeur n'est pas recompilé ET re-uploadé, les utilisateurs téléchargent
# l'ancien. On enchaîne donc build → vérif → installeur → upload en UNE commande.
def construire_installateur():
    if not os.path.isfile(ISCC):
        raise SystemExit("Inno Setup introuvable : %s" % ISCC)
    log("compilation de l'installeur (Inno Setup)…")
    r = subprocess.run([ISCC, os.path.join(RACINE, "installateur.iss")],
                       cwd=RACINE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.isfile(INSTALLEUR):
        raise SystemExit("Compilation de l'installeur échouée :\n" + (r.stdout or "")[-800:])
    log("installeur OK : %s (%.1f Mo)" %
        (INSTALLEUR, os.path.getsize(INSTALLEUR) / (1024 * 1024)))


def _git(args):
    """git dans la RACINE, sortie capturée. Ne lève pas : à l'appelant de
    contrôler returncode (les échecs git doivent ARRÊTER une publication)."""
    return subprocess.run(["git", *args], cwd=RACINE, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def _arbre_git_propre():
    """True si `git status --porcelain` ne liste RIEN (arbre propre)."""
    r = _git(["status", "--porcelain"])
    if r.returncode != 0:
        raise SystemExit("ARRÊT : git status a échoué (%s)."
                         % (r.stderr or "").strip()[:200])
    return not (r.stdout or "").strip()


# Posé par exiger_arbre_propre() AVANT le build ; publier() refuse sans lui.
_ARBRE_VERIFIE_PROPRE = False


def exiger_arbre_propre():
    """ARRÊT si l'arbre git est sale. Appelé AVANT le build (barrière release) :
    ainsi le commit unique « Arboriane X.Y.Z » de publier() (git add -A) ne peut
    contenir QUE ce que le déployeur produit lui-même (version_info, installeur
    .iss, CHANGELOG, page), jamais un travail en cours embarqué par accident."""
    global _ARBRE_VERIFIE_PROPRE
    if not _arbre_git_propre():
        raise SystemExit(
            "ARRÊT : l'arbre git n'est pas propre (voir git status).\n"
            "Committez ou remisez votre travail en cours avant de publier.")
    _ARBRE_VERIFIE_PROPRE = True
    log("barrière : arbre git propre")


def _release_distante_existe(tag):
    """True si la release existe déjà CÔTÉ DISTANT (GitHub), pas seulement en
    tag local — c'est la seule vérité qui compte pour « déjà publié »."""
    return subprocess.run([GH, "release", "view", tag, "--repo", DEPOT],
                          capture_output=True).returncode == 0


def _dernier_commit_ts():
    r = subprocess.run(["git", "log", "-1", "--format=%ct"], cwd=RACINE,
                       capture_output=True, text=True)
    return int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0


def _empreinte(chemin):
    """Condensé SHA-256 d'un fichier, en hexadécimal minuscule."""
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def _ecrire_empreinte():
    """Écrit « <sha256>  Installer-Arboriane.exe » à côté de l'installeur.

    L'exe n'est pas signé : Windows dira « éditeur inconnu ». Publier le condensé
    ne remplace pas une signature, mais permet à qui le souhaite de vérifier que
    le fichier téléchargé est EXACTEMENT celui qu'on a construit — et de le
    comparer au code source, public. C'est gratuit, et c'est mieux que rien.
    """
    somme = _empreinte(INSTALLEUR)
    chemin = INSTALLEUR + ".sha256"
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write("%s  %s\n" % (somme, os.path.basename(INSTALLEUR)))
    log("empreinte SHA-256 : %s" % somme)
    return chemin, somme


def _notes(somme):
    return (
        "## Vérifier le téléchargement\n\n"
        "Arboriane n'est pas signé : Windows affichera « éditeur inconnu ». "
        "Vous pouvez vérifier que le fichier reçu est bien celui publié ici.\n\n"
        "Dans PowerShell :\n\n"
        "```powershell\n"
        "Get-FileHash .\\Installer-Arboriane.exe -Algorithm SHA256\n"
        "```\n\n"
        "Le résultat doit être :\n\n"
        "```\n%s\n```\n\n"
        "Le code source correspondant est celui du tag `v%s`.\n" % (somme, VERSION))


def _maj_page_version():
    """Aligne le repli figé du numéro de version dans docs/index.html (le
    numéro affiché est déjà dynamique via l'API GitHub, ceci n'est que le
    repli). MODIFIE LE FICHIER SEULEMENT : la modification part dans le commit
    unique « Arboriane X.Y.Z » de publier() — fini le commit séparé
    « Page : version X » qui doublait l'historique."""
    page = os.path.join(RACINE, "docs", "index.html")
    try:
        txt = open(page, encoding="utf-8").read()
    except OSError:
        return
    neuf = re.sub(r'(class="version-arboriane">)[^<]*(</span>)',
                  r"\g<1>" + VERSION + r"\g<2>", txt)
    if neuf != txt:
        open(page, "w", encoding="utf-8").write(neuf)
        log("docs/index.html -> %s (ira dans le commit de release)" % VERSION)


def publier():
    """Publie la release vX.Y.Z sur GitHub — UNIQUEMENT via cet outil.

    ⚠ INTERDICTION de publier « à la main » avec gh (release create/upload
    depuis un terminal). C'est arrivé pour la v1.9.10 : publiée hors outil,
    donc sans barrière de tests, sans commit ni tag poussés, et sans notes de
    version — le « Quoi de neuf » et le CHANGELOG ont pris cinq versions de
    retard (1.9.6 → 1.9.10, rattrapées le 2026-07-19). Le déployeur est le
    SEUL chemin de publication : tests verts, CHANGELOG vérifié, code source
    du tag = binaire publié, empreinte SHA-256.

    Étapes — refus à la moindre anomalie :
      1. l'arbre git était PROPRE avant le build (exiger_arbre_propre) ;
      2. la release n'existe PAS déjà côté DISTANT — si elle existe : ARRÊT,
         jamais de --clobber ; pour corriger un binaire publié, on MONTE la
         version (le fichier téléchargé par les utilisateurs ne doit jamais
         changer sous un même numéro) ;
      3. l'installeur n'est pas plus ancien que le dernier commit (asset
         périmé = la panne du 2026-07-09) ;
      4. docs/index.html aligné, puis UN SEUL commit « Arboriane X.Y.Z »
         (git add -A : uniquement ce que l'outil a produit, cf. étape 1),
         tag vX.Y.Z, et push origin main --tags — si le push échoue, RIEN
         n'est publié ;
      5. gh release create, ciblée (--target) sur le commit du tag.
    """
    tag = "v" + VERSION
    if not _ARBRE_VERIFIE_PROPRE:
        raise SystemExit(
            "ARRÊT : l'arbre git n'a pas été contrôlé propre avant le build "
            "(barrière contournée ?). Publication refusée — relancez avec "
            "--release SANS --sans-barriere.")
    if _release_distante_existe(tag):
        raise SystemExit(
            "ARRÊT : la release %s existe DÉJÀ sur GitHub.\n"
            "On ne remplace JAMAIS un binaire publié (pas de --clobber) : les "
            "utilisateurs et l'empreinte SHA-256 s'y fient. Pour corriger, "
            "montez VERSION dans core/version.py, ajoutez ses notes dans "
            "services/maj.py, et republiez." % tag)
    asset_ts = int(os.path.getmtime(INSTALLEUR))
    if asset_ts < _dernier_commit_ts():
        raise SystemExit("Installeur plus ancien que le dernier commit : "
                         "recompile-le AVANT de publier (asset périmé).")
    fichier_somme, somme = _ecrire_empreinte()

    # Commit de release UNIQUE : version_info.txt, installateur.iss,
    # CHANGELOG.md, docs/index.html… tout ce que l'outil vient de produire.
    _maj_page_version()
    r = _git(["add", "-A"])
    if r.returncode != 0:
        raise SystemExit("ARRÊT : git add a échoué (%s)." % (r.stderr or "").strip()[:200])
    if (_git(["status", "--porcelain"]).stdout or "").strip():
        r = _git(["commit", "-m", "Arboriane " + VERSION])
        if r.returncode != 0:
            raise SystemExit("ARRÊT : commit de release impossible :\n"
                             + (r.stderr or r.stdout or ""))
        log("commit de release : « Arboriane %s »" % VERSION)
    r = _git(["tag", tag])
    if r.returncode != 0:
        raise SystemExit("ARRÊT : impossible de poser le tag %s :\n%s"
                         % (tag, r.stderr or ""))
    r = _git(["push", "origin", "main", "--tags"])
    if r.returncode != 0:
        raise SystemExit(
            "ARRÊT : push refusé (%s).\nRIEN n'est publié tant que le dépôt "
            "distant n'a pas le commit et le tag : le code source public doit "
            "correspondre EXACTEMENT au binaire téléchargeable."
            % (r.stderr or "").strip()[:300])
    log("commit + tag %s poussés sur origin/main" % tag)

    # SHA du commit taggé : la release est épinglée dessus (--target), le
    # binaire publié correspond donc exactement à ce code source.
    sha = (_git(["rev-parse", tag + "^{commit}"]).stdout or "").strip()
    log("création de la release %s + installeur + empreinte…" % tag)
    cmd = [GH, "release", "create", tag, INSTALLEUR, fichier_somme,
           "--repo", DEPOT, "--title", "Arboriane " + VERSION,
           "--target", sha, "--notes", _notes(somme)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0:
        raise SystemExit("Publication GitHub échouée :\n" + (r.stderr or ""))
    log("publié : https://github.com/%s/releases/tag/%s" % (DEPOT, tag))


def _lancer(titre, cmd, cwd=RACINE):
    """Exécute une commande, laisse sa sortie s'afficher, et interrompt tout si
    elle échoue. La publication ne discute pas avec un test rouge."""
    log(titre)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        raise SystemExit("ARRÊT : %s — la publication est annulée." % titre)


def _tag_existe(tag):
    r = subprocess.run(["git", "tag", "--list", tag], cwd=RACINE,
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def _tests_js():
    """Lance les tests JavaScript si Node est présent. Bloquant s'ils échouent ;
    simplement signalé si Node manque (la machine de publication l'a)."""
    fichiers = sorted(glob.glob(os.path.join(RACINE, "tests", "js", "test_*.mjs")))
    if not fichiers:
        return
    node = shutil.which("node")
    if not node:
        log("⚠ Node absent : tests JavaScript non exécutés.")
        return
    _lancer("barrière : %d fichiers de tests JavaScript…" % len(fichiers),
            [node, "--test", *fichiers])


def barriere(release):
    """Ce qui doit être vrai AVANT de déployer, et a fortiori avant de publier.

    Le déployeur compilait, installait et publiait sans jamais lancer un test :
    les correctifs d'un matin pouvaient partir avec les bugs du matin suivant.
    C'est arrivé. Trois pertes de données sont parties en 1.7.5.

    Ordre : suite de tests toujours ; corpus GEDCOM et contrôle de version
    seulement pour une publication (le corpus est lent, et déployer chez soi
    n'engage personne).
    """
    tests = sorted(glob.glob(os.path.join(RACINE, "tests", "test_*.py")))
    if not tests:
        raise SystemExit("ARRÊT : aucun test trouvé. Refus de déployer à l'aveugle.")
    log("barrière : %d suites de tests…" % len(tests))
    for t in tests:
        r = subprocess.run([sys.executable, "-X", "utf8", t], cwd=RACINE,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0:
            print((r.stdout or "")[-2000:])
            raise SystemExit("ARRÊT : %s échoue. La publication est annulée."
                             % os.path.basename(t))
    log("barrière : suites vertes")
    _tests_js()

    if not release:
        return

    # PUB-01 : arbre PROPRE exigé AVANT le build — le commit de release
    # (git add -A dans publier()) n'embarquera que ce que l'outil produit.
    exiger_arbre_propre()

    if _tag_existe("v" + VERSION):
        raise SystemExit(
            "ARRÊT : la version %s est déjà publiée (tag v%s).\n"
            "Montez VERSION dans core/version.py, et ajoutez ses notes dans "
            "services/maj.py." % (VERSION, VERSION))
    if _release_distante_existe("v" + VERSION):
        raise SystemExit(
            "ARRÊT : la release v%s existe déjà sur GitHub (même sans tag "
            "local — publication faite hors outil ?). Montez VERSION dans "
            "core/version.py ; on ne remplace jamais un binaire publié."
            % VERSION)

    _lancer("barrière : corpus GEDCOM (non-régression sur fichiers réels)…",
            [sys.executable, "-X", "utf8",
             os.path.join(RACINE, "outils", "banc_gedcom.py")])
    _lancer("barrière : conformité 5.5.1 de notre export…",
            [sys.executable, "-X", "utf8",
             os.path.join(RACINE, "outils", "valider_gedcom.py"), "--export"])
    _lancer("barrière : CHANGELOG.md à jour…",
            [sys.executable, "-X", "utf8",
             os.path.join(RACINE, "outils", "generer_changelog.py"), "--verifier"])
    log("barrière : franchie — publication autorisée")


def main():
    args = sys.argv[1:]
    if "--verif" in args:
        return verifier()
    if "--sans-barriere" in args:            # dépannage : à n'utiliser qu'en connaissance
        log("⚠ BARRIÈRE DÉSACTIVÉE — ne publiez pas ainsi.")
    else:
        barriere(release="--release" in args)
    sync_version()
    if "--no-build" not in args:
        build()
    deployer()
    verifier()
    if "--release" in args:                  # publication atomique (exe + installeur)
        construire_installateur()
        publier()                            # commit unique (page incluse) + tag + push + release
    log("Terminé : version %s déployée et vérifiée." % VERSION)


if __name__ == "__main__":
    main()
