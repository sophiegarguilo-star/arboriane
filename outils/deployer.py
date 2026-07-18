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
    log("build OK")


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


def publier():
    """Crée/complète le release vX.Y.Z, y attache l'installeur et son empreinte
    SHA-256. Refuse si l'installeur est plus ANCIEN que le dernier commit
    (asset périmé = la panne du 2026-07-09)."""
    tag = "v" + VERSION
    asset_ts = int(os.path.getmtime(INSTALLEUR))
    if asset_ts < _dernier_commit_ts():
        raise SystemExit("Installeur plus ancien que le dernier commit : "
                         "recompile-le AVANT de publier (asset périmé).")
    fichier_somme, somme = _ecrire_empreinte()
    existe = subprocess.run([GH, "release", "view", tag, "--repo", DEPOT],
                            capture_output=True).returncode == 0
    if existe:
        log("upload de l'installeur sur le release %s…" % tag)
        cmd = [GH, "release", "upload", tag, INSTALLEUR, fichier_somme,
               "--repo", DEPOT, "--clobber"]
    else:
        log("création du release %s + installeur + empreinte…" % tag)
        cmd = [GH, "release", "create", tag, INSTALLEUR, fichier_somme,
               "--repo", DEPOT, "--title", "Arboriane " + VERSION,
               "--notes", _notes(somme)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0:
        raise SystemExit("Publication GitHub échouée :\n" + (r.stderr or ""))
    log("publié : https://github.com/%s/releases/tag/%s" % (DEPOT, tag))


def maj_page_github():
    """Met à jour la page GitHub Pages (docs/index.html) et la POUSSE. Le numéro
    de version y est déjà dynamique (lu via l'API GitHub côté client) ; ici on
    rafraîchit son repli figé et on pousse, pour que la page soit à jour à chaque
    publication. On ne commit QUE docs/index.html (le reste du code reste local,
    selon la discipline d'historique). À appeler APRÈS publier() : committer avant
    ferait échouer le garde-fou d'horodatage de l'installeur."""
    page = os.path.join(RACINE, "docs", "index.html")
    try:
        txt = open(page, encoding="utf-8").read()
    except OSError:
        return
    neuf = re.sub(r'(class="version-arboriane">)[^<]*(</span>)',
                  r"\g<1>" + VERSION + r"\g<2>", txt)
    if neuf != txt:
        open(page, "w", encoding="utf-8").write(neuf)
    if subprocess.run(["git", "diff", "--quiet", "--", "docs/index.html"],
                      cwd=RACINE).returncode == 0:
        log("page GitHub : déjà à jour (rien à pousser)")
        return
    for cmd in (["git", "add", "docs/index.html"],
                ["git", "commit", "-m", "Page : version " + VERSION, "--", "docs/index.html"],
                ["git", "push", "origin", "main"]):
        r = subprocess.run(cmd, cwd=RACINE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            log("page GitHub : étape « %s » a échoué (%s) — à pousser à la main."
                % (" ".join(cmd[:2]), (r.stderr or "").strip()[:140]))
            return
    log("page GitHub Pages mise à jour et poussée (docs/index.html)")


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

    if _tag_existe("v" + VERSION):
        raise SystemExit(
            "ARRÊT : la version %s est déjà publiée (tag v%s).\n"
            "Montez VERSION dans core/version.py, et ajoutez ses notes dans "
            "services/maj.py." % (VERSION, VERSION))

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
        publier()
        maj_page_github()                    # page GitHub Pages à jour (APRÈS publier)
    log("Terminé : version %s déployée et vérifiée." % VERSION)


if __name__ == "__main__":
    main()
