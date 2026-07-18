# -*- coding: utf-8 -*-
"""
Application — l'état vivant d'Arboriane, indépendant du serveur HTTP.

Détient : les dossiers de l'installation (donnees/, Mes arbres/), le registre
des espaces connus, l'espace actif et sa base. Sépare la logique applicative
du transport HTTP (app.py) pour que tout soit testable sans serveur.
"""

import atexit
import base64
import json
import os
import shutil
import threading
import time
import zipfile

from core import coffre
from core import espace as espace_mod
from core import stockage
from core.fichiers import dans, horodatage, nom_sur, taille_dossier
from services import synchro


class Application:
    def __init__(self, dossier_app):
        self.dossier_app = os.path.abspath(dossier_app)
        self.dossier_donnees = os.path.join(self.dossier_app, "donnees")
        self.dossier_arbres = os.path.join(self.dossier_app, "Mes arbres")
        self.registre = os.path.join(self.dossier_donnees, "espaces.json")
        os.makedirs(self.dossier_donnees, exist_ok=True)
        os.makedirs(self.dossier_arbres, exist_ok=True)
        self.espace_chemin = None
        self.manifeste = None
        self.base = None
        # Le serveur est multi-thread : ce verrou sérialise les bascules d'espace
        # (activer/ouvrir/créer/supprimer) pour éviter qu'une écriture en cours et
        # une suppression du même arbre ne se télescopent.
        self._verrou = threading.RLock()
        self._cache_taille = {}          # chemin -> (instant, taille) : évite de
        self._reprendre_dernier()        # re-parcourir tout le disque à chaque listing
        # À la fermeture propre du programme, on retire notre verrou souple pour
        # libérer aussitôt l'arbre sur les autres postes (un plantage laisserait
        # le verrou expirer de lui-même après la péremption).
        atexit.register(self._liberer_verrou)

    # ── Registre des espaces connus ───────────────────────────────────
    def _lire_registre(self):
        try:
            with open(self.registre, "r", encoding="utf-8") as f:
                r = json.load(f)
        except (OSError, ValueError):
            r = {}
        r.setdefault("actif", "")
        r.setdefault("connus", [])
        return r

    def _ecrire_registre(self, r):
        tmp = self.registre + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.registre)

    def _memoriser(self, chemin, actif=True):
        chemin = os.path.normpath(chemin)
        r = self._lire_registre()
        r["connus"] = [c for c in r["connus"] if os.path.normpath(c) != chemin]
        r["connus"].insert(0, chemin)
        if actif:
            r["actif"] = chemin
        self._ecrire_registre(r)

    def _reprendre_dernier(self):
        r = self._lire_registre()
        if r["actif"] and espace_mod.est_espace(r["actif"]):
            try:
                self._activer(r["actif"])
            except OSError:
                pass

    # ── Ouvrir / créer / démo ─────────────────────────────────────────
    def _activer(self, chemin):
        with self._verrou:
            self._liberer_verrou()            # libère l'arbre qu'on quitte
            self.manifeste = espace_mod.charger(chemin)
            c = espace_mod.chemins(chemin)
            self.base = stockage.Base(c["base"], c["sauvegardes"])
            self.espace_chemin = os.path.normpath(chemin)
            self._poser_verrou()              # pose le verrou (arbres cloud only)

    # ── Verrou souple multi-ordinateurs (arbres en dossier synchronisé) ──
    def _poser_verrou(self):
        """Dépose le verrou de cette machine — SEULEMENT si l'arbre est dans un
        dossier synchronisé (sinon aucun fichier n'est ajouté à un arbre local)."""
        if self.espace_chemin and synchro.detecter_cloud(self.espace_chemin):
            try:
                synchro.poser_verrou(self.espace_chemin)
            except OSError:
                pass

    def _liberer_verrou(self):
        """Retire notre verrou de l'arbre courant (sans effet s'il n'y en a pas)."""
        if self.espace_chemin:
            try:
                synchro.liberer_verrou(self.espace_chemin)
            except OSError:
                pass

    def verrou_etranger(self, chemin):
        """Info de verrou si l'arbre `chemin` semble ouvert sur une AUTRE
        machine (récent), sinon None. Lecture seule — n'active rien."""
        try:
            return synchro.verrou_etranger(chemin)
        except OSError:
            return None

    def rafraichir_verrou(self, intervalle=300):
        """Rafraîchit (throttlé) le verrou de l'arbre actif tant qu'on l'utilise.
        Appelé au fil de la navigation ; n'écrit qu'au plus une fois par
        `intervalle` secondes, pour ne pas solliciter le cloud à chaque clic."""
        if not self.espace_chemin or not synchro.detecter_cloud(self.espace_chemin):
            return
        v = synchro.lire_verrou(self.espace_chemin)
        if (v and v.get("machine") == synchro.nom_machine()
                and (time.time() - float(v.get("horodatage", 0) or 0)) < intervalle):
            return                            # encore frais : on n'écrit pas
        self._poser_verrou()

    def cloud_actif(self):
        """Fournisseur cloud de l'arbre actif ({'fournisseur': …}) ou None."""
        return synchro.detecter_cloud(self.espace_chemin) if self.espace_chemin else None

    def ouvrir(self, chemin):
        if not espace_mod.est_espace(chemin):
            raise ValueError("Ce dossier n'est pas un espace Arboriane.")
        self._activer(chemin)
        self._memoriser(chemin)
        return self.manifeste

    def creer(self, nom, parent=None):
        """Crée un nouvel arbre. `parent` = dossier où le ranger (ex. un dossier
        sur le disque D:) ; par défaut « Mes arbres/ ». Le registre gère les
        chemins absolus, donc un arbre créé ailleurs est listé et rouvert
        normalement."""
        nom = (nom or "").strip() or "Nouvel arbre"
        dossier_parent = self._parent_valide(parent)
        cible = os.path.join(dossier_parent, nom_sur(nom))
        base = cible
        n = 2
        while os.path.exists(base):
            base = "%s (%d)" % (cible, n)
            n += 1
        espace_mod.creer(base, nom)
        self._activer(base)
        self._memoriser(base)
        return self.manifeste

    def _parent_valide(self, parent):
        """Valide le dossier parent choisi pour un nouvel arbre. Renvoie
        « Mes arbres/ » si aucun n'est fourni. Lève ValueError si le dossier est
        inaccessible, inscriptible en apparence seulement, ou (dans) un arbre
        existant (pas d'arbres imbriqués)."""
        if not parent:
            return self.dossier_arbres
        parent = os.path.abspath(parent)
        if not os.path.isdir(parent):
            raise ValueError("Ce dossier n'existe pas : %s" % parent)
        # Refus d'un dossier qui EST ou est DANS un arbre Arboriane.
        p = parent
        while True:
            if espace_mod.est_espace(p):
                raise ValueError("Ce dossier est (ou est à l'intérieur d')un arbre "
                                 "Arboriane. Choisissez un dossier ordinaire.")
            haut = os.path.dirname(p)
            if haut == p:
                break
            p = haut
        # Inscriptibilité RÉELLE : os.access(W_OK) ment sous Windows (ACL).
        temoin = os.path.join(parent, ".arboriane_test_ecriture")
        try:
            with open(temoin, "w") as f:
                f.write("ok")
            os.remove(temoin)
        except OSError:
            raise ValueError("Ce dossier n'est pas accessible en écriture : %s" % parent)
        return parent

    def ouvrir_demo(self, generer_si_absent, version=None):
        """Ouvre (ou (re)génère) l'arbre de démonstration. `generer_si_absent`
        est un callable(chemin) qui peuple un espace neuf. Si `version` est
        fourni et que la démo existante est plus ancienne, elle est régénérée
        (l'arbre de démonstration est jetable par définition)."""
        import shutil
        cible = os.path.join(self.dossier_arbres, "Demo")
        besoin = not espace_mod.est_espace(cible)
        if not besoin and version is not None:
            m = espace_mod.charger(cible) or {}
            if m.get("demo_version") != version:
                besoin = True
                shutil.rmtree(cible, ignore_errors=True)
        if besoin:
            espace_mod.creer(cible, "Arbre de démonstration")
            generer_si_absent(cible)
        self._activer(cible)
        self._memoriser(cible)
        return self.manifeste

    # ── Liste des espaces (pour l'onglet Espace de travail) ────────────
    def lister(self):
        r = self._lire_registre()
        # Déduplication défensive : un même arbre a pu entrer deux fois au
        # registre (formes de chemin différentes) — il apparaissait alors en
        # double dans la liste (ex. « Arbre de démonstration » ×2).
        vus = set()
        chemins = []

        def _ajouter(p):
            cle = os.path.normcase(os.path.normpath(p))
            if cle not in vus:
                vus.add(cle)
                chemins.append(p)

        for c in r["connus"]:
            _ajouter(c)
        # ajouter les arbres présents dans Mes arbres/ non encore connus
        try:
            for nom in os.listdir(self.dossier_arbres):
                p = os.path.join(self.dossier_arbres, nom)
                if espace_mod.est_espace(p):
                    _ajouter(p)
        except OSError:
            pass
        cartes = []
        for chemin in chemins:
            carte = self._carte_espace(chemin)
            if carte:
                cartes.append(carte)
        return cartes

    def _carte_espace(self, chemin):
        m = espace_mod.charger(chemin)
        if not m:
            return None                # présent au registre mais disparu/illisible
        c = espace_mod.chemins(chemin)
        nb_pers = nb_src = 0
        try:
            with open(c["base"], "r", encoding="utf-8") as f:
                d = json.load(f)
            nb_pers = len(d.get("individus", {}))
            nb_src = len(d.get("sources", {}))
        except (OSError, ValueError):
            pass
        return {
            "chemin": os.path.normpath(chemin),
            "nom": m.get("nom", os.path.basename(chemin)),
            "actif": os.path.normpath(chemin) == (self.espace_chemin or ""),
            "demo": os.path.basename(os.path.normpath(chemin)) == "Demo",
            "personnes": nb_pers,
            "sources": nb_src,
            "taille": self._taille_cachee(chemin),
            "cloud": synchro.detecter_cloud(chemin),   # {'fournisseur': …} ou None
        }

    def _taille_cachee(self, chemin, ttl=60):
        """Taille du dossier, mise en cache `ttl` secondes : ouvrir l'onglet
        Espaces à répétition ne re-parcourt plus des Go de scans à chaque fois."""
        cle = os.path.normpath(chemin)
        instant, val = self._cache_taille.get(cle, (0, None))
        if val is not None and (time.time() - instant) < ttl:
            return val
        val = taille_dossier(chemin)
        self._cache_taille[cle] = (time.time(), val)
        return val

    def oublier(self, chemin):
        """Retire un espace de la liste SANS toucher au dossier."""
        chemin = os.path.normpath(chemin)
        r = self._lire_registre()
        r["connus"] = [c for c in r["connus"] if os.path.normpath(c) != chemin]
        if os.path.normpath(r["actif"]) == chemin:
            r["actif"] = ""
            if self.espace_chemin == chemin:
                self._liberer_verrou()
                self.espace_chemin = self.manifeste = self.base = None
        self._ecrire_registre(r)

    def renommer(self, chemin, nouveau_nom):
        m = espace_mod.charger(chemin)
        if not m:
            raise ValueError("Espace introuvable.")
        m["nom"] = (nouveau_nom or "").strip() or m["nom"]
        espace_mod.sauver_manifeste(chemin, m)
        if os.path.normpath(chemin) == (self.espace_chemin or ""):
            self.manifeste = m
        return m

    def racine_valide(self):
        """La racine du manifeste existe-t-elle vraiment ? Un arbre neuf porte
        « I1 » par défaut, et un GEDCOM importé peut n'avoir aucun I1."""
        if not self.base or not self.manifeste:
            return False
        return self.manifeste.get("racine_id") in self.base.donnees["individus"]

    def garantir_racine(self, pid):
        """Adopte `pid` comme racine SI la racine actuelle n'existe pas. Rend la
        racine auto-réparante : première personne créée, ou 1re personne d'un
        GEDCOM importé dont les identifiants ne commencent pas par I1."""
        if not self.espace_chemin or not self.manifeste or self.racine_valide():
            return self.manifeste
        return self.definir_racine(pid)

    def definir_racine(self, pid):
        """Définit la personne de référence (racine) de l'arbre courant —
        celle autour de laquelle se construisent arbre, Sosa et plan."""
        if not self.espace_chemin or not self.manifeste:
            raise ValueError("Aucun arbre ouvert.")
        m = espace_mod.charger(self.espace_chemin)
        m["racine_id"] = pid
        espace_mod.sauver_manifeste(self.espace_chemin, m)
        self.manifeste = m
        return m

    def enregistrer_fond_arbre(self, fond, opacite=60):
        """Mémorise l'arrière-plan de l'arbre DANS l'arbre (manifeste), pour le
        retrouver d'un poste à l'autre. `fond` vide efface la mémorisation."""
        if not self.espace_chemin or not self.manifeste:
            raise ValueError("Aucun arbre ouvert.")
        m = espace_mod.charger(self.espace_chemin)
        fond = (fond or "").strip()
        if fond:
            try:
                op = max(10, min(100, int(opacite)))
            except (TypeError, ValueError):
                op = 60
            m["arbre_fond"] = {"fond": fond, "fond_opacite": op}
        else:
            m.pop("arbre_fond", None)
        espace_mod.sauver_manifeste(self.espace_chemin, m)
        self.manifeste = m
        return m.get("arbre_fond", {})

    def supprimer(self, chemin):
        """Supprime un espace APRÈS avoir déposé une archive de sécurité dans
        donnees/_corbeille/. On ne supprime jamais sans filet."""
        chemin = os.path.normpath(chemin)
        if not espace_mod.est_espace(chemin):
            raise ValueError("Espace introuvable.")
        corbeille = os.path.join(self.dossier_donnees, "_corbeille")
        os.makedirs(corbeille, exist_ok=True)
        archive = os.path.join(corbeille, "%s_%s.zip"
                               % (nom_sur(os.path.basename(chemin)), horodatage()))
        self.archiver_zip(chemin, archive)
        with self._verrou:
            # Supprimer D'ABORD ; ne fermer l'espace actif qu'en cas de succès.
            # Ainsi, si un fichier est verrouillé (rmtree lève), l'état reste
            # cohérent (l'arbre demeure ouvert) — l'archive de sécurité est déjà là.
            shutil.rmtree(chemin)
            if os.path.normpath(self.espace_chemin or "") == chemin:
                self.espace_chemin = self.manifeste = self.base = None
        self.oublier(chemin)
        return {"archive": archive}

    # ── Sauvegarde complète (.zip) ────────────────────────────────────
    def archiver_zip(self, chemin, cible):
        """Zippe le dossier de l'espace (réimportable), SANS le sous-dossier
        Exports/ — celui-ci contient les sauvegardes et exports volumineux ;
        les y inclure ferait grossir chaque archive de toutes les précédentes
        (croissance exponentielle qui remplit le disque)."""
        chemin = os.path.abspath(chemin)
        cible_abs = os.path.abspath(cible)
        os.makedirs(os.path.dirname(cible), exist_ok=True)
        with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
            for base, dirs, fics in os.walk(chemin):
                if os.path.abspath(base) == chemin:
                    dirs[:] = [d for d in dirs if d != "Exports"]
                for f in fics:
                    if f == synchro.NOM_VERROU:
                        continue          # verrou souple : local à chaque machine
                    plein = os.path.join(base, f)
                    if os.path.abspath(plein) == cible_abs:
                        continue          # ne jamais s'inclure soi-même
                    z.write(plein, os.path.relpath(plein, chemin))
        return cible

    def sauvegarde_complete(self):
        """Crée une sauvegarde .zip de l'espace actif dans son Exports/.
        Renvoie le chemin de l'archive."""
        if not self.espace_chemin:
            raise ValueError("Aucun arbre ouvert.")
        c = espace_mod.chemins(self.espace_chemin)
        cible = dans(c["exports"],
                     "%s_sauvegarde_%s.zip"
                     % (nom_sur(self.manifeste.get("nom", "arbre")), horodatage()))
        return self.archiver_zip(self.espace_chemin, cible)

    # ── Fichiers image (scans d'actes, photos) ────────────────────────
    CATEGORIES = {"Sources": "Sources", "Photos": "Photos", "Fonds": "Fonds"}

    def enregistrer_media(self, categorie, nom, data_base64):
        """Écrit un fichier (image) dans Sources/ ou Photos/ de l'arbre actif.
        Renvoie le nom de fichier retenu (unique). data_base64 peut être un
        data-URI (« data:image/jpeg;base64,… ») ou du base64 pur."""
        if not self.espace_chemin:
            raise ValueError("Aucun arbre ouvert.")
        dossier = self.CATEGORIES.get(categorie)
        if not dossier:
            raise ValueError("Catégorie inconnue.")
        if "," in data_base64 and data_base64.strip().startswith("data:"):
            data_base64 = data_base64.split(",", 1)[1]
        donnees = base64.b64decode(data_base64)
        base_dir = os.path.join(self.espace_chemin, dossier)
        os.makedirs(base_dir, exist_ok=True)
        propre = nom_sur(nom, "image")
        cible = dans(base_dir, propre)
        racine, ext = os.path.splitext(cible)
        n = 2
        while os.path.exists(cible):        # ne jamais écraser un fichier présent
            cible = "%s (%d)%s" % (racine, n, ext)
            n += 1
        with open(cible, "wb") as f:
            f.write(donnees)
        return os.path.basename(cible)

    def renommer_media(self, categorie, de, vers):
        """Renomme un média dans sa catégorie. Ne sert qu'aux scans qui viennent
        d'être déposés et ne sont encore référencés nulle part : renommer un
        fichier déjà cité casserait la source qui le cite. N'écrase jamais un
        fichier existant. Renvoie le nom finalement retenu."""
        if not self.espace_chemin:
            raise ValueError("Aucun arbre ouvert.")
        dossier = self.CATEGORIES.get(categorie)
        if not dossier:
            raise ValueError("Catégorie inconnue.")
        base_dir = os.path.join(self.espace_chemin, dossier)
        source = dans(base_dir, de)
        if not os.path.isfile(source):
            raise ValueError("Fichier introuvable.")
        cible = dans(base_dir, nom_sur(vers, "scan"))
        if os.path.normcase(source) == os.path.normcase(cible):
            return os.path.basename(source)
        racine, ext = os.path.splitext(cible)
        n = 2
        while os.path.exists(cible):
            cible = "%s (%d)%s" % (racine, n, ext)
            n += 1
        os.rename(source, cible)
        return os.path.basename(cible)

    def lister_medias(self, categorie):
        """Noms des fichiers déjà présents dans une catégorie (Sources, Photos…).
        Sert à proposer un nom de scan qui n'entre en collision avec rien."""
        dossier = self.CATEGORIES.get(categorie)
        if not self.espace_chemin or not dossier:
            return []
        base_dir = os.path.join(self.espace_chemin, dossier)
        try:
            return sorted(os.listdir(base_dir))
        except OSError:
            return []

    def chemin_media(self, categorie, nom):
        """Chemin absolu d'un média (pour le servir), garanti dans l'arbre."""
        if not self.espace_chemin:
            return None
        dossier = self.CATEGORIES.get(categorie)
        if not dossier:
            return None
        try:
            cible = dans(os.path.join(self.espace_chemin, dossier), nom)
        except ValueError:
            return None
        return cible if os.path.isfile(cible) else None

    def _media_reference(self, nom):
        """Un fichier média est-il référencé quelque part (source, photo de
        personne, fond d'arbre) ? Sert de garde-fou avant suppression."""
        if not self.base:
            return False
        for s in self.base.donnees.get("sources", {}).values():
            if nom in (s.get("fichiers") or []) or s.get("fichier") == nom:
                return True
        for ind in self.base.donnees.get("individus", {}).values():
            for m in ind.get("medias") or []:
                fic = m.get("fichier") if isinstance(m, dict) else m
                if fic == nom:
                    return True
        fond = (self.manifeste or {}).get("arbre_fond") or {}
        if fond.get("fond") == "img:" + nom:
            return True
        return False

    def supprimer_media_si_inutilise(self, categorie, nom):
        """Supprime un fichier média SEULEMENT s'il n'est référencé nulle part —
        p. ex. un import abandonné (source créée puis annulée). Ne supprime
        jamais un fichier réellement utilisé. Renvoie True si supprimé."""
        cible = self.chemin_media(categorie, nom)
        if not cible or self._media_reference(nom):
            return False
        try:
            os.remove(cible)
            return True
        except OSError:
            return False

    # ── Réglages locaux (jamais dans un arbre : clés API à part) ───────
    @property
    def _fichier_reglages(self):
        return os.path.join(self.dossier_donnees, "reglages.json")

    def _sauver_reglages(self, r):
        """Écriture atomique du fichier de réglages."""
        tmp = self._fichier_reglages + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._fichier_reglages)

    def lire_reglages(self):
        """Réglages sur disque. La clé API n'y figure que CHIFFRÉE (champ
        « ia_cle_chiffree »). Migration transparente : une éventuelle ancienne
        clé « ia_cle » en clair est chiffrée puis retirée du fichier."""
        try:
            with open(self._fichier_reglages, "r", encoding="utf-8") as f:
                r = json.load(f)
        except (OSError, ValueError):
            return {}
        if "ia_cle" in r:                       # ancien format en clair -> migrer
            clair = r.pop("ia_cle") or ""
            if clair and not r.get("ia_cle_chiffree"):
                r["ia_cle_chiffree"] = coffre.chiffrer(clair)
            try:
                self._sauver_reglages(r)
            except OSError:
                pass
        return r

    def ecrire_reglages(self, champs):
        """Fusionne des réglages. Une clé reçue en clair (« ia_cle ») est
        CHIFFRÉE avant écriture — jamais stockée en clair au repos ; « ia_cle »
        vide efface la clé. Une clé absente des champs ne touche pas l'existante."""
        champs = dict(champs)
        if "ia_cle" in champs:
            clair = (champs.pop("ia_cle") or "").strip()
            champs["ia_cle_chiffree"] = coffre.chiffrer(clair) if clair else ""
        r = self.lire_reglages()
        r.update(champs)
        r.pop("ia_cle", None)                    # jamais de clé en clair au repos
        if not r.get("ia_cle_chiffree"):
            r.pop("ia_cle_chiffree", None)       # champ vide = pas de clé
        self._sauver_reglages(r)
        return r

    def cle_ia(self):
        """Clé API en clair (déchiffrée à la volée en mémoire), '' si absente.
        À n'utiliser qu'au moment d'un appel à l'assistant."""
        return coffre.dechiffrer(self.lire_reglages().get("ia_cle_chiffree") or "")

    def reglages_publics(self):
        """Réglages SANS la clé : on n'expose que sa présence et un aperçu."""
        r = self.lire_reglages()
        cle = coffre.dechiffrer(r.get("ia_cle_chiffree") or "")
        return {
            "ia_fournisseur": r.get("ia_fournisseur", "anthropic"),
            "ia_modele": r.get("ia_modele", ""),
            "cle_definie": bool(r.get("ia_cle_chiffree")),
            "cle_apercu": ("…" + cle[-4:]) if len(cle) >= 4 else "",
            "geocodage_ok": bool(r.get("geocodage_ok")),
            "pays_defaut": r.get("pays_defaut") or "",
            "navigateur": r.get("navigateur") or "",
        }
