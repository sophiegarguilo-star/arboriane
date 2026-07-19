# -*- coding: utf-8 -*-
"""
Stockage de l'arbre — un fichier JSON par espace (arboriane.json).

Charge, sauvegarde (copie horodatée à chaque écriture, dans Sauvegardes/) et
offre les opérations d'édition qui maintiennent la cohérence des liens
famille ↔ individu. La source de vérité des liens est TOUJOURS la table des
familles ; fams/famc des individus en découlent.
"""

import copy
import functools
import json
import os
import shutil
import sys
import threading
import time

from core import modele
from core.fichiers import horodatage


def _synchronise(methode):
    """Sérialise l'appel via le verrou réentrant de l'instance : plusieurs
    requêtes HTTP peuvent modifier la base en même temps."""
    @functools.wraps(methode)
    def enveloppe(self, *a, **k):
        with self._verrou:
            return methode(self, *a, **k)
    return enveloppe


class Base:
    def __init__(self, chemin_json, dossier_sauvegardes):
        self.chemin = chemin_json
        self.dossier_sauvegardes = dossier_sauvegardes
        self._verrou = threading.RLock()
        self.donnees = modele.base_vide()
        # Compteur de version : incrémenté à chaque écriture/rechargement. Sert
        # de jeton d'invalidation aux caches de lecture (services/personnes).
        self.version = 0
        # "corrompu" si le JSON a dû être mis en quarantaine (bandeau UI futur).
        self.avertissement = ""
        self.charger()

    # ── Chargement / sauvegarde ───────────────────────────────────────
    @_synchronise
    def charger(self):
        self.avertissement = ""
        if os.path.exists(self.chemin):
            try:
                with open(self.chemin, "r", encoding="utf-8") as f:
                    self.donnees = json.load(f)
            except OSError as e:
                # Fichier momentanément INACCESSIBLE (antivirus, cloud en cours
                # de synchro, droits) : les données sont probablement intactes —
                # on REFUSE d'ouvrir plutôt que de repartir à vide (une
                # sauvegarde ultérieure écraserait l'arbre par une base vide).
                raise OSError(
                    "Le fichier de l'arbre est momentanément inaccessible "
                    "(%s). Ouverture refusée pour protéger vos données — "
                    "réessayez dans un instant. Détail : %s" % (self.chemin, e))
            except ValueError as e:
                # JSON corrompu : on le met de côté, on ne le perd jamais, et on
                # repart sur une base vide (aucune sauvegarde ne l'écrasera avant
                # une action explicite).
                self._mettre_de_cote_corrompu(e)
                self.donnees = modele.base_vide()
                self.avertissement = "corrompu"
        self.version += 1
        modele.garantir_cles(self.donnees)
        # Migration douce : dates au format interne français (« 20 JUL 1984 » →
        # « 20/07/1984 »). Idempotent — un arbre déjà en français ne bouge pas.
        from core.gedcom.lecture import franciser_dates   # import tardif (cycle)
        franciser_dates(self.donnees)

    def _mettre_de_cote_corrompu(self, err):
        try:
            os.makedirs(self.dossier_sauvegardes, exist_ok=True)
            cible = os.path.join(self.dossier_sauvegardes,
                                 "CORROMPU_%s.json" % horodatage())
            shutil.copy2(self.chemin, cible)
            sys.stderr.write("[stockage] base illisible (%s) — copie : %s\n"
                             % (err, cible))
        except OSError:
            pass

    @_synchronise
    def sauvegarder(self, horodatee=True, forcer_horodatage=False):
        self.version += 1                # invalide les caches de lecture
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        tmp = self.chemin + ".tmp"                      # écriture atomique
        # Fichier principal COMPACT (sans indent) : lu par la machine seulement,
        # ~2× plus petit et plus rapide à (ré)écrire sur un gros arbre.
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.donnees, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())         # vraiment sur le disque avant replace
        os.replace(tmp, self.chemin)
        # Copie horodatée dans Sauvegardes/, mais PAS à chaque micro-édition :
        # sur un gros arbre, archiver l'intégralité du JSON à chaque clic use le
        # disque pour rien. On garde au plus une archive toutes ~90 s.
        if horodatee and (forcer_horodatage or not self._archivage_recent()):
            os.makedirs(self.dossier_sauvegardes, exist_ok=True)
            cible = os.path.join(self.dossier_sauvegardes,
                                 "arboriane_%s.json" % horodatage())
            n = 2
            while os.path.exists(cible):     # deux archives la même seconde
                cible = os.path.join(self.dossier_sauvegardes,
                                     "arboriane_%s (%d).json" % (horodatage(), n))
                n += 1
            try:
                # Les archives RESTENT indentées : elles sont là pour être
                # ouvertes et lues à la main en cas de pépin.
                with open(cible, "w", encoding="utf-8") as fa:
                    json.dump(self.donnees, fa, ensure_ascii=False, indent=2)
                self._purger_sauvegardes(garder=30)
            except OSError:
                pass

    def _archivage_recent(self, intervalle=90):
        """Vrai si une sauvegarde horodatée a été faite il y a moins de
        `intervalle` secondes (pour espacer les copies intégrales)."""
        try:
            recents = [os.path.getmtime(os.path.join(self.dossier_sauvegardes, n))
                       for n in os.listdir(self.dossier_sauvegardes)
                       if n.startswith("arboriane_") and n.endswith(".json")]
        except OSError:
            return False
        return bool(recents) and (time.time() - max(recents)) < intervalle

    def _purger_sauvegardes(self, garder=30, plafond_corrompus=5):
        """Rétention GÉNÉRATIONNELLE : les `garder` archives les plus récentes
        + la PREMIÈRE archive de chacun des `garder` derniers jours (un point de
        restauration quotidien survit donc aux rafales d'éditions d'une même
        journée). Les copies CORROMPU_* sont plafonnées à `plafond_corrompus`."""
        try:
            fichiers = sorted(
                (os.path.join(self.dossier_sauvegardes, n)
                 for n in os.listdir(self.dossier_sauvegardes)
                 if n.startswith("arboriane_") and n.endswith(".json")),
                key=os.path.getmtime)
            a_garder = set(fichiers[-garder:])
            maintenant = time.time()
            premiere_du_jour = {}
            for f in fichiers:                        # du plus ancien au plus récent
                mt = os.path.getmtime(f)
                if (maintenant - mt) > garder * 86400:
                    continue                          # au-delà des N derniers jours
                jour = time.strftime("%Y-%m-%d", time.localtime(mt))
                premiere_du_jour.setdefault(jour, f)  # la 1re archive du jour
            a_garder.update(premiere_du_jour.values())
            for vieux in fichiers:
                if vieux not in a_garder:
                    os.remove(vieux)
            corrompus = sorted(
                (os.path.join(self.dossier_sauvegardes, n)
                 for n in os.listdir(self.dossier_sauvegardes)
                 if n.startswith("CORROMPU_") and n.endswith(".json")),
                key=os.path.getmtime)
            for vieux in corrompus[:-plafond_corrompus]:
                os.remove(vieux)
        except OSError:
            pass

    @_synchronise
    def remplacer(self, donnees):
        """Remplace toute la base (import GEDCOM/ZIP, restauration d'archive)."""
        modele.garantir_cles(donnees)
        self.donnees = donnees
        # L'avertissement « corrompu » signale une base repartie à vide après
        # quarantaine : un remplacement VOLONTAIRE (restauration, import) la
        # remet d'aplomb — le bandeau ne doit pas survivre à la réparation.
        self.avertissement = ""
        # Réaligne fams/famc sur la table des familles : purge les pointeurs
        # pendants et corrige les GEDCOM asymétriques (union/enfant fantômes).
        self._recalc_tous_liens()
        # Ancre les compteurs monotones sur les ids importés : sans cela,
        # supprimer le plus grand id d'un import puis créer quelqu'un le
        # RECYCLAIT (références orphelines héritées, corbeille ambiguë).
        self._ancrer_compteurs()
        self.sauvegarder()

    def _ancrer_compteurs(self):
        """meta.compteurs >= plus grand numéro présent, pour chaque table à
        identifiants monotones. Défensif : tolère un meta/compteurs malformé."""
        meta = self.donnees.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            self.donnees["meta"] = meta
        compteurs = meta.get("compteurs")
        if not isinstance(compteurs, dict):
            compteurs = {}
            meta["compteurs"] = compteurs
        for table, prefixe in (("individus", "I"), ("familles", "F"),
                               ("sources", "S"), ("ensembles", "E")):
            plus_grand = modele._plus_grand_numero(
                self.donnees.get(table) or {}, prefixe)
            try:
                actuel = int(compteurs.get(prefixe, 0) or 0)
            except (TypeError, ValueError):
                actuel = 0
            if plus_grand > actuel:
                compteurs[prefixe] = plus_grand

    # ── Individus ─────────────────────────────────────────────────────
    @_synchronise
    def creer_individu(self, champs):
        ident = modele.nouvel_id_monotone(self.donnees, "individus", "I")
        ind = {
            "id": ident,
            "sexe": champs.get("sexe", "U"),
            "prenoms": champs.get("prenoms", ""),
            "nom": champs.get("nom", ""),
            "prenom_principal": champs.get("prenom_principal", ""),
            "prenoms_secondaires": champs.get("prenoms_secondaires", ""),
            "nom_particule": champs.get("nom_particule", ""),
            "nom_prefixe": champs.get("nom_prefixe", ""),   # NPFX (Dr, Me, Rév.)
            "nom_suffixe": champs.get("nom_suffixe", ""),   # NSFX (Jr, III, aîné)
            "nom_marital": champs.get("nom_marital", ""),
            "surnom": champs.get("surnom", ""),
            "noms_alternatifs": champs.get("noms_alternatifs", []),
            "naissance": champs.get("naissance", {"date": "", "lieu": ""}),
            "deces": champs.get("deces", {"date": "", "lieu": ""}),
            "professions": champs.get("professions", []),
            "residences": champs.get("residences", []),
            "note": champs.get("note", ""),
            "tags": champs.get("tags", []),
            "pistes": champs.get("pistes", []),
            "evenements": champs.get("evenements", []),
            "medias": champs.get("medias", []),
            "citations": champs.get("citations", []),
            "associations": champs.get("associations", []),
            "refn": champs.get("refn", ""),
            "resn": champs.get("resn", ""),
            "famc": [],
            "fams": [],
        }
        if "vivant" in champs:
            ind["vivant"] = champs["vivant"]
        self.donnees["individus"][ident] = ind
        self.sauvegarder()
        return ind

    CHAMPS_INDIVIDU = (
        "sexe", "prenoms", "nom", "prenom_principal", "prenoms_secondaires",
        "nom_particule", "nom_prefixe", "nom_suffixe",
        "nom_marital", "surnom", "noms_alternatifs",
        "naissance", "deces", "professions", "residences", "note", "tags",
        "pistes", "evenements", "medias", "citations", "vivant",
        "associations", "refn", "resn",       # importés du GEDCOM : rendre éditables
    )

    # Champs qui DOIVENT rester des listes / des dicts : une valeur d'un autre
    # type (envoyée par un client bogué ou hostile) casserait l'affichage
    # (`.forEach`/`.map` côté fiche) — on la neutralise plutôt que de la stocker.
    _CHAMPS_LISTE = frozenset((
        "noms_alternatifs", "professions", "residences", "tags", "pistes",
        "evenements", "medias", "citations", "associations"))
    _CHAMPS_DICT = frozenset(("naissance", "deces"))
    _SEXES_VALIDES = frozenset(("M", "F", "X", "N", "U"))

    @classmethod
    def _assainir_champ_individu(cls, cle, valeur):
        """Contraint chaque champ à son type attendu (défense en profondeur :
        l'API tolère des entrées mal formées sans jamais corrompre la base)."""
        if cle in cls._CHAMPS_LISTE:
            return valeur if isinstance(valeur, list) else []
        if cle in cls._CHAMPS_DICT:
            return valeur if isinstance(valeur, dict) else {}
        if cle == "vivant":
            return bool(valeur)
        if cle == "sexe":
            return valeur if valeur in cls._SEXES_VALIDES else "U"
        # champs texte : forcer en chaîne et borner (la note biographique est
        # plus longue que les autres).
        maxi = 20000 if cle == "note" else 2000
        if valeur is None:
            return ""
        return (valeur if isinstance(valeur, str) else str(valeur))[:maxi]

    @_synchronise
    def modifier_individu(self, ident, champs):
        ind = self.donnees["individus"].get(ident)
        if not ind:
            return None
        for cle in self.CHAMPS_INDIVIDU:
            if cle in champs:
                valeur = self._assainir_champ_individu(cle, champs[cle])
                # Ne JAMAIS perdre les preuves d'un fait vital : un écran (ou un
                # client) qui renvoie naissance/décès sans « citations » ne doit
                # pas effacer celles déjà attachées (même règle que le mariage).
                if cle in self._CHAMPS_DICT and "citations" not in valeur:
                    anciennes = (ind.get(cle) or {}).get("citations")
                    if anciennes:
                        valeur["citations"] = anciennes
                ind[cle] = valeur
        self.sauvegarder()
        return ind

    @_synchronise
    def definir_medias(self, ident, medias):
        """Remplace la galerie d'une personne. Garantit au plus une principale."""
        ind = self.donnees["individus"].get(ident)
        if ind is None:
            return None
        propre, vu_prim = [], False
        for m in (medias or []):
            f = (m.get("fichier") or "").strip()
            if not f:
                continue
            prim = bool(m.get("principale")) and not vu_prim
            vu_prim = vu_prim or prim
            entree = {"fichier": f, "titre": (m.get("titre") or "").strip(),
                      "principale": prim}
            cadrage = (m.get("cadrage") or "").strip()   # cadrage carré (« x% y% »), non destructif
            if cadrage:
                entree["cadrage"] = cadrage
            propre.append(entree)
        if propre and not vu_prim:
            propre[0]["principale"] = True
        ind["medias"] = propre
        self.sauvegarder()
        return ind

    # ── Corbeille : suppression de personne RÉVERSIBLE (UX-03) ────────
    # Avant chaque suppression, un instantané JSON (fiche complète + liens
    # familiaux + favoris/ensembles) est déposé dans <arbre>/Corbeille/.
    # « Annuler » recrée la personne SOUS SON ID D'ORIGINE (jamais recyclé,
    # compteurs monotones) et retisse ses liens dans les familles survivantes.
    @property
    def dossier_corbeille(self):
        return os.path.join(os.path.dirname(self.chemin), "Corbeille")

    def _fichiers_corbeille(self):
        """Instantanés présents, du plus ancien au plus récent (mtime puis nom,
        pour rester déterministe si deux suppressions tombent la même seconde)."""
        try:
            return sorted(
                (os.path.join(self.dossier_corbeille, n)
                 for n in os.listdir(self.dossier_corbeille)
                 if n.startswith("personne_") and n.endswith(".json")),
                key=lambda p: (os.path.getmtime(p), p))
        except OSError:
            return []

    def _deposer_corbeille(self, ident):
        """Dépose l'instantané d'une personne AVANT sa suppression : fiche
        complète, liens familiaux (famille + rôle + place), favori et
        ensembles. Garde les 20 derniers. Une erreur d'écriture ne bloque
        jamais la suppression (la corbeille est un filet, pas un verrou)."""
        ind = self.donnees["individus"].get(ident)
        if not ind:
            return
        liens = []
        for fid, fam in self.donnees["familles"].items():
            if fam.get("mari") == ident:
                liens.append({"famille": fid, "role": "mari"})
            if fam.get("epouse") == ident:
                liens.append({"famille": fid, "role": "epouse"})
            enfants = fam.get("enfants") or []
            if ident in enfants:
                liens.append({"famille": fid, "role": "enfant",
                              "place": enfants.index(ident)})
        favoris = self.donnees.get("favoris")
        favori = favoris.get(ident) if isinstance(favoris, dict) else None
        ensembles = [eid for eid, ens in (self.donnees.get("ensembles") or {}).items()
                     if isinstance(ens, dict) and ident in (ens.get("membres") or [])]
        instantane = {
            "quoi": "personne_supprimee",
            "quand": horodatage(),
            "individu": copy.deepcopy(ind),
            "liens": liens,
            "favori": favori,
            "ensembles": ensembles,
        }
        try:
            os.makedirs(self.dossier_corbeille, exist_ok=True)
            cible = os.path.join(self.dossier_corbeille,
                                 "personne_%s_%s.json" % (ident, horodatage()))
            with open(cible, "w", encoding="utf-8") as f:
                json.dump(instantane, f, ensure_ascii=False, indent=2)
            for vieux in self._fichiers_corbeille()[:-20]:   # garder les 20 derniers
                os.remove(vieux)
        except OSError:
            pass

    @_synchronise
    def restaurer_dernier_supprime(self):
        """Restaure la DERNIÈRE personne supprimée (instantané le plus récent
        de Corbeille/) : recrée la fiche sous son id d'origine et retisse ses
        liens — dans les familles qui existent ENCORE seulement, sans jamais
        déloger un conjoint arrivé entre-temps. Renvoie l'individu restauré,
        ou None (corbeille vide, instantané illisible, id déjà repris)."""
        fichiers = self._fichiers_corbeille()
        if not fichiers:
            return None
        dernier = fichiers[-1]
        try:
            with open(dernier, "r", encoding="utf-8") as f:
                instantane = json.load(f)
        except (OSError, ValueError):
            return None
        ind = instantane.get("individu")
        if not isinstance(ind, dict) or not ind.get("id"):
            return None
        ident = ind["id"]
        if ident in self.donnees["individus"]:
            return None                       # id déjà occupé : on ne fusionne pas
        ind["fams"], ind["famc"] = [], []     # re-dérivés depuis les familles
        self.donnees["individus"][ident] = ind
        fams = self.donnees["familles"]
        for lien in instantane.get("liens") or []:
            fam = fams.get((lien or {}).get("famille"))
            if not fam:
                continue                      # la famille a disparu entre-temps
            role = lien.get("role")
            if role in ("mari", "epouse"):
                if not fam.get(role):         # créneau libre seulement
                    fam[role] = ident
            elif role == "enfant":
                enfants = fam.setdefault("enfants", [])
                if ident not in enfants:
                    place = lien.get("place")
                    if isinstance(place, int) and 0 <= place <= len(enfants):
                        enfants.insert(place, ident)
                    else:
                        enfants.append(ident)
        if instantane.get("favori") is not None:
            favoris = self.donnees.setdefault("favoris", {})
            if isinstance(favoris, dict):
                favoris[ident] = instantane["favori"]
        for eid in instantane.get("ensembles") or []:
            ens = (self.donnees.get("ensembles") or {}).get(eid)
            if isinstance(ens, dict):
                membres = ens.setdefault("membres", [])
                if ident not in membres:
                    membres.append(ident)
        self._recalc_tous_liens()
        self.sauvegarder()
        try:
            os.remove(dernier)                # l'annulation est consommée
        except OSError:
            pass
        return ind

    @_synchronise
    def supprimer_individu(self, ident):
        if ident not in self.donnees["individus"]:
            return False
        self._deposer_corbeille(ident)        # filet : suppression annulable
        for fam in self.donnees["familles"].values():
            if fam.get("mari") == ident:
                fam["mari"] = ""
            if fam.get("epouse") == ident:
                fam["epouse"] = ""
            if ident in fam.get("enfants", []):
                fam["enfants"] = [e for e in fam["enfants"] if e != ident]
        # Nettoie les citations « personnes citées » des sources : sinon la
        # personne supprimée y reste en lien fantôme (source qui cite quelqu'un
        # qui n'existe plus, invisible mais présent dans les données).
        for src in self.donnees.get("sources", {}).values():
            if src.get("personnes"):
                src["personnes"] = [p for p in src["personnes"] if p.get("id") != ident]
        # Cascade complète : favoris, ensembles et associations (parrain/témoin)
        # de TOUS les individus — sinon un futur individu recevant un id recyclé
        # hériterait de ces références, et les listes afficheraient des fantômes.
        favoris = self.donnees.get("favoris")
        if isinstance(favoris, dict):
            favoris.pop(ident, None)
        for ens in (self.donnees.get("ensembles") or {}).values():
            if isinstance(ens, dict) and ident in (ens.get("membres") or []):
                ens["membres"] = [m for m in ens["membres"] if m != ident]
        for autre in self.donnees["individus"].values():
            assos = autre.get("associations")
            if assos and any(isinstance(a, dict) and a.get("id") == ident for a in assos):
                autre["associations"] = [a for a in assos
                                         if not (isinstance(a, dict) and a.get("id") == ident)]
        del self.donnees["individus"][ident]
        self._nettoyer_familles_vides()
        self.sauvegarder()
        return True

    # ── Familles / liens ──────────────────────────────────────────────
    def _famille_pour_couple(self, pere_id, mere_id):
        """Trouve la famille du couple, sinon en crée une. Ne réutilise pas une
        famille dont la place du parent manquant est déjà prise (sinon on
        inventerait un conjoint)."""
        fams = self.donnees["familles"]
        if pere_id and mere_id:
            for fam in fams.values():
                if {pere_id, mere_id} <= {fam.get("mari"), fam.get("epouse")}:
                    return fam
            # Un seul des deux est déjà parent d'une famille SANS enfant (cas
            # « ＋ Père » puis « ＋ Mère ») : on la COMPLÈTE au lieu d'en créer une
            # seconde — sinon la première survivait en union fantôme
            # « conjoint·e inconnu·e ». On exige « sans enfant » pour ne jamais
            # attribuer les enfants d'une union précédente au nouveau conjoint.
            for fam in fams.values():
                membres = {fam.get("mari"), fam.get("epouse")} - {"", None}
                if len(membres) == 1 and membres <= {pere_id, mere_id} \
                        and not fam.get("enfants"):
                    return fam
        else:
            connu = pere_id or mere_id
            for fam in fams.values():
                if connu in (fam.get("mari"), fam.get("epouse")):
                    coparent = (fam.get("epouse") if fam.get("mari") == connu
                                else fam.get("mari"))
                    if not coparent:
                        return fam
        fid = modele.nouvel_id_monotone(self.donnees, "familles", "F")
        fam = {"id": fid, "mari": "", "epouse": "", "enfants": [],
               "mariage": {"date": "", "lieu": ""}, "note": ""}
        fams[fid] = fam
        return fam

    def _placer_parent(self, fam, pid):
        if not pid:
            return
        ind = self.donnees["individus"].get(pid)
        if not ind:                     # id inexistant : on n'invente rien
            return
        sexe = ind.get("sexe", "U")
        prefere = "epouse" if sexe == "F" else ("mari" if sexe == "M" else None)
        if prefere:
            autre = "epouse" if prefere == "mari" else "mari"
            # Ne JAMAIS écraser un créneau déjà occupé par une AUTRE personne :
            # pour un couple de même sexe, on bascule sur le créneau libre.
            if fam.get(prefere) in ("", None, pid):
                cible = prefere
            elif fam.get(autre) in ("", None, pid):
                cible = autre
            else:
                cible = prefere
        else:
            cible = "mari" if not fam.get("mari") else "epouse"
        fam[cible] = pid
        if fam["id"] not in ind.get("fams", []):
            ind.setdefault("fams", []).append(fam["id"])

    @_synchronise
    def definir_parents(self, enfant_id, pere_id, mere_id):
        """Rattache un enfant à un couple (crée la famille si besoin)."""
        enfant = self.donnees["individus"].get(enfant_id)
        if not enfant:
            return None
        for fid in list(enfant.get("famc", [])):        # détacher de l'ancienne
            fam = self.donnees["familles"].get(fid)
            if fam and enfant_id in fam.get("enfants", []):
                fam["enfants"] = [e for e in fam["enfants"] if e != enfant_id]
        enfant["famc"] = []

        if not pere_id and not mere_id:
            self._nettoyer_familles_vides()
            self.sauvegarder()
            return enfant

        fam = self._famille_pour_couple(pere_id, mere_id)
        self._placer_parent(fam, pere_id)
        self._placer_parent(fam, mere_id)
        if enfant_id not in fam["enfants"]:
            fam["enfants"].append(enfant_id)
        enfant["famc"] = [fam["id"]]
        self._nettoyer_familles_vides()
        self.sauvegarder()
        return enfant

    @_synchronise
    def ajouter_conjoint(self, ident, conjoint_id, mariage=None):
        fams = self.donnees["familles"]
        fam = None
        for f in fams.values():                         # 1) couple déjà relié
            if {ident, conjoint_id} <= {f.get("mari"), f.get("epouse")}:
                fam = f
                break
        if fam is None:                                 # 2) famille solo à compléter
            for f in fams.values():
                if ident in (f.get("mari"), f.get("epouse")):
                    autre = (f.get("epouse") if f.get("mari") == ident
                             else f.get("mari"))
                    if not autre:
                        fam = f
                        break
        if fam is None:                                 # 3) nouvelle famille
            fid = modele.nouvel_id_monotone(self.donnees, "familles", "F")
            fam = {"id": fid, "mari": "", "epouse": "", "enfants": [],
                   "mariage": {"date": "", "lieu": ""}, "note": ""}
            fams[fid] = fam
        self._placer_parent(fam, ident)
        self._placer_parent(fam, conjoint_id)
        if mariage:
            fam["mariage"] = mariage
        self._nettoyer_familles_vides()
        self.sauvegarder()
        return fam

    @_synchronise
    def ajouter_enfant(self, parent_id, enfant_id, nouvelle=False):
        """Ajoute un enfant à `parent_id`. Par défaut, l'enfant rejoint la
        PREMIÈRE union du parent (ou une union créée pour lui s'il n'en a
        aucune). `nouvelle=True` force une union neuve (autre parent inconnu),
        utile quand le parent a déjà plusieurs unions."""
        ind = self.donnees["individus"].get(parent_id)
        if not ind:
            return None
        if nouvelle:
            fams = self.donnees["familles"]
            fid = modele.nouvel_id_monotone(self.donnees, "familles", "F")
            fam = {"id": fid, "mari": "", "epouse": "", "enfants": [],
                   "mariage": {"date": "", "lieu": ""}, "note": ""}
            fams[fid] = fam
            self._placer_parent(fam, parent_id)
        else:
            # On dérive la 1ʳᵉ famille du parent depuis la TABLE DES FAMILLES
            # (source de vérité), pas depuis ind["fams"] qui peut être périmé ou
            # asymétrique (GEDCOM importé malformé) : sinon on créerait une union
            # fantôme « conjoint·e inconnu·e » alors que le couple existe déjà.
            fam = next((f for f in self.donnees["familles"].values()
                        if parent_id in (f.get("mari"), f.get("epouse"))), None)
            if fam is None:
                fam = self._famille_pour_couple(parent_id, "")
                self._placer_parent(fam, parent_id)
        return self._rattacher_enfant(fam, enfant_id)

    @_synchronise
    def ajouter_enfant_famille(self, fid, enfant_id):
        """Ajoute un enfant à une FAMILLE précise (bouton « ＋ enfant » d'une
        union donnée) — sans jamais retomber sur `fams[0]`."""
        fam = self.donnees["familles"].get(fid)
        if not fam:
            return None
        return self._rattacher_enfant(fam, enfant_id)

    @_synchronise
    def ajouter_fratrie(self, pid, frere_id):
        """Ajoute un frère / une sœur : la personne devient un enfant DE PLUS de
        la famille-parents de `pid`. Si `pid` n'a pas de parents connus, on crée
        une famille-parents (vide) et on y range les deux comme enfants."""
        if pid not in self.donnees["individus"] or frere_id not in self.donnees["individus"]:
            return None
        fam = next((f for f in self.donnees["familles"].values()
                    if pid in f.get("enfants", [])), None)
        if fam is None:
            fid = modele.nouvel_id_monotone(self.donnees, "familles", "F")
            fam = {"id": fid, "mari": "", "epouse": "", "enfants": [pid],
                   "mariage": {"date": "", "lieu": ""}, "note": ""}
            self.donnees["familles"][fid] = fam
        return self._rattacher_enfant(fam, frere_id)

    def _rattacher_enfant(self, fam, enfant_id):
        enfant = self.donnees["individus"].get(enfant_id)
        if enfant:
            # Détacher l'enfant de toute AUTRE famille-enfant (sinon double
            # filiation : il resterait listé dans les enfants de son ancienne famille).
            for fid in list(enfant.get("famc", [])):
                autre = self.donnees["familles"].get(fid)
                if autre and autre is not fam and enfant_id in autre.get("enfants", []):
                    autre["enfants"] = [e for e in autre["enfants"] if e != enfant_id]
            enfant["famc"] = [fam["id"]]
        if enfant_id not in fam["enfants"]:
            fam["enfants"].append(enfant_id)
        self._nettoyer_familles_vides()
        self.sauvegarder()
        return fam

    @_synchronise
    def modifier_famille(self, fid, champs):
        fam = self.donnees["familles"].get(fid)
        if not fam:
            return None
        if "mariage" in champs:
            # Ne JAMAIS perdre les preuves du mariage : un écran qui n'envoie que
            # date/lieu ne doit pas effacer les citations déjà attachées.
            ancien = fam.get("mariage") or {}
            recu = champs["mariage"]
            nouveau = dict(recu) if isinstance(recu, dict) else {}  # tolère un type invalide
            if "citations" not in nouveau and ancien.get("citations"):
                nouveau["citations"] = ancien["citations"]
            fam["mariage"] = nouveau
        if "evenements" in champs:                 # doit rester une liste
            ev = champs["evenements"]
            fam["evenements"] = ev if isinstance(ev, list) else []
        if "note" in champs:
            note = champs["note"]
            fam["note"] = (note if isinstance(note, str) else str(note or ""))[:20000]
        self._nettoyer_familles_vides()
        self.sauvegarder()
        return fam

    def _nettoyer_familles_vides(self):
        """Supprime les familles sans membre, puis re-dérive INTÉGRALEMENT
        fams/famc depuis la table des familles (seule source de vérité des liens).

        On ne se contente PAS de filtrer les pointeurs pendants : on RECONSTRUIT.
        Ainsi une asymétrie — un parent présent dans une famille mais absent de
        ses `fams` — est réparée à chaque mutation. C'est ce trou qui faisait
        qu'une union n'apparaissait que d'un seul côté et que les enfants ajoutés
        filaient dans une famille fantôme « conjoint·e inconnu·e »."""
        def _sans_objet(fam):
            """Une famille ne vaut d'être gardée que si elle exprime un lien :
            au moins un enfant, OU un couple (2 parents), OU une info de mariage
            (« marié·e à un·e inconnu·e le … »). Un parent seul, sans enfant ni
            mariage, est une union fantôme : on la supprime."""
            if fam.get("enfants"):
                return False
            parents = {fam.get("mari"), fam.get("epouse")} - {"", None}
            if len(parents) >= 2:
                return False
            mar = fam.get("mariage") or {}
            if mar.get("date") or mar.get("lieu") or mar.get("citations"):
                return False
            return not fam.get("evenements")

        vides = [fid for fid, fam in self.donnees["familles"].items() if _sans_objet(fam)]
        for fid in vides:
            del self.donnees["familles"][fid]
        self._recalc_tous_liens()

    # ── Sources (le cœur d'Arboriane) ─────────────────────────────────
    CHAMPS_SOURCE = (
        "titre", "type", "date", "lieu", "ville", "pays", "auteur", "depot",
        "depot_id", "cote", "page", "publ", "ark", "fiabilite", "statut", "note",
        "transcription", "fichier", "fichiers", "personnes",
    )

    # Champs de source qui DOIVENT rester des listes (même motif que
    # _assainir_champ_individu : `.forEach`/`.map` côté écran Actes).
    _CHAMPS_SOURCE_LISTE = frozenset(("fichiers", "personnes"))

    @classmethod
    def _assainir_champ_source(cls, cle, valeur):
        """Contraint chaque champ de source à son type attendu : une écriture
        malformée ne doit jamais casser la fiche, l'écran Actes ni l'export."""
        if cle in cls._CHAMPS_SOURCE_LISTE:
            if not isinstance(valeur, list):
                return []
            # Les ITEMS aussi doivent être sains (contrôle post-correction :
            # un item non conforme recassait fiche/Actes/export — TECH-01 bis).
            if cle == "personnes":
                # tags de personnes : dicts {id:str, role:str} uniquement
                props = []
                for it in valeur:
                    if isinstance(it, dict) and isinstance(it.get("id"), str) and it.get("id"):
                        props.append({"id": it["id"][:64],
                                      "role": str(it.get("role", ""))[:200]})
                    elif isinstance(it, str) and it:      # tolérance : id nu
                        props.append({"id": it[:64], "role": ""})
                return props
            # fichiers : chaînes non vides bornées
            return [str(it)[:500] for it in valeur
                    if isinstance(it, (str, int, float)) and str(it).strip()]
        # champs texte : forcer en chaîne et borner (transcription et note
        # peuvent être longues, le reste non).
        maxi = 100000 if cle == "transcription" else (20000 if cle == "note" else 2000)
        if valeur is None:
            return ""
        return (valeur if isinstance(valeur, str) else str(valeur))[:maxi]

    @_synchronise
    def creer_source(self, champs):
        self.donnees.setdefault("sources", {})
        sid = modele.nouvel_id_monotone(self.donnees, "sources", "S")
        src = {"id": sid}
        for cle in self.CHAMPS_SOURCE:
            defaut = [] if cle in self._CHAMPS_SOURCE_LISTE else ""
            src[cle] = self._assainir_champ_source(cle, champs.get(cle, defaut))
        self.donnees["sources"][sid] = src
        self.sauvegarder()
        return src

    @_synchronise
    def modifier_source(self, sid, champs):
        src = self.donnees.get("sources", {}).get(sid)
        if not src:
            return None
        for cle in self.CHAMPS_SOURCE:
            if cle in champs:
                src[cle] = self._assainir_champ_source(cle, champs[cle])
        self.sauvegarder()
        return src

    @_synchronise
    def supprimer_source(self, sid):
        """Supprime une source ET toutes les citations qui la référencent."""
        srcs = self.donnees.get("sources", {})
        if sid not in srcs:
            return False
        del srcs[sid]

        def _net(cites):
            return [c for c in (cites or []) if c.get("source") != sid]
        for ind in self.donnees["individus"].values():
            ind["citations"] = _net(ind.get("citations"))
            for ev in (ind.get("naissance"), ind.get("deces")):
                if isinstance(ev, dict) and ev.get("citations"):
                    ev["citations"] = _net(ev["citations"])
            for ev in ind.get("evenements", []):
                if ev.get("citations"):
                    ev["citations"] = _net(ev["citations"])
            for res in ind.get("residences", []):   # les résidences aussi peuvent être sourcées
                if isinstance(res, dict) and res.get("citations"):
                    res["citations"] = _net(res["citations"])
        for fam in self.donnees["familles"].values():
            m = fam.get("mariage")
            if isinstance(m, dict) and m.get("citations"):
                m["citations"] = _net(m["citations"])
            for ev in fam.get("evenements", []):
                if ev.get("citations"):
                    ev["citations"] = _net(ev["citations"])
        self.sauvegarder()
        return True

    @staticmethod
    def _normaliser_citation(citation):
        """Force une citation au format canonique {source:str, page:str bornée,
        quay:int 0-3 ou None, role:str} — une citation malformée (types
        hostiles) ne doit jamais casser fiche, écran Actes ni export GEDCOM.
        NB : « pas de niveau » = None (jamais "") — l'export GEDCOM écrit QUAY
        dès que la valeur n'est pas None, et l'import (champs.py) pose None."""
        c = citation if isinstance(citation, dict) else {}
        src = c.get("source")
        page = c.get("page")
        role = c.get("role")
        quay = c.get("quay")
        if isinstance(quay, bool):        # True/False ne sont pas des niveaux QUAY
            quay = None
        try:
            quay = min(3, max(0, int(quay)))
        except (TypeError, ValueError):
            quay = None                   # absent ou non numérique : pas de niveau
        return {
            "source": (src if isinstance(src, str) else str(src or ""))[:100],
            "page": (page if isinstance(page, str) else str(page or ""))[:2000],
            "quay": quay,
            "role": (role if isinstance(role, str) else str(role or ""))[:200],
        }

    def _fam_visee(self, ind, pid, famille):
        """Famille visée par une preuve d'union : `famille` si pid en est bien
        un parent (cas remariage), sinon sa première union, sinon None."""
        if famille and famille in self.donnees["familles"]:
            cand = self.donnees["familles"][famille]
            if pid in (cand.get("mari"), cand.get("epouse")):
                return cand
        fams = ind.get("fams") or []
        return self.donnees["familles"].get(fams[0]) if fams else None

    @_synchronise
    def citer(self, pid, fait, citation, famille=None):
        """Attache une citation (preuve) à un fait d'une personne.
        `fait` ∈ {'naissance','deces','personne','union'}, un fait secondaire
        'coll:index' (residence/profession/evenement), un événement de couple
        'union_evenement:index', ou l'index nu d'un événement individuel.
        `famille` (facultatif) cible l'union PRÉCISE à prouver (sinon
        la 1re) — utile en cas de remariage. `citation` = {source, page, quay, role}."""
        citation = self._normaliser_citation(citation)
        ind = self.donnees["individus"].get(pid)
        if not ind:
            return None
        if fait == "personne":
            ind.setdefault("citations", []).append(citation)
        elif fait in ("naissance", "deces"):
            ev = ind.setdefault(fait, {"date": "", "lieu": ""})
            ev.setdefault("citations", []).append(citation)
        elif fait == "union":
            # L'union est portée par la FAMILLE (mariage), pas par l'individu — la
            # citation est donc PARTAGÉE par les deux conjoints. On cible l'union
            # demandée (`famille`) si pid en est bien un parent, sinon sa 1re.
            fam = self._fam_visee(ind, pid, famille)
            if not fam:
                return None
            mar = fam.setdefault("mariage", {"date": "", "lieu": ""})
            mar.setdefault("citations", []).append(citation)
        elif str(fait).startswith("union_evenement:"):
            # Fait porté par la FAMILLE (divorce, séparation… balise GEDCOM DIV,
            # SEPR…) : comme le mariage, il est PARTAGÉ par les deux conjoints. On
            # cible l'union demandée (`famille`) si pid en est parent, sinon la 1re.
            idx = str(fait).split(":", 1)[1]
            fam = self._fam_visee(ind, pid, famille)
            evts = (fam or {}).get("evenements") or []
            if not fam or not idx.isdigit() or not (0 <= int(idx) < len(evts)) \
                    or not isinstance(evts[int(idx)], dict):
                return None
            evts[int(idx)].setdefault("citations", []).append(citation)
        elif ":" in str(fait):
            # Fait secondaire ciblé par « coll:index » : résidence, profession,
            # événement. La citation vit DANS l'item (déplacée avec lui si l'ordre
            # change), pas indexée en externe.
            _CLE = {"residence": "residences", "profession": "professions",
                    "evenement": "evenements"}
            nom, _, idx = str(fait).partition(":")
            cle = _CLE.get(nom)
            liste = ind.get(cle) or [] if cle else []
            if not cle or not idx.isdigit() or not (0 <= int(idx) < len(liste)) \
                    or not isinstance(liste[int(idx)], dict):
                return None
            liste[int(idx)].setdefault("citations", []).append(citation)
        else:
            try:
                ind["evenements"][int(fait)].setdefault("citations", []).append(citation)
            except (ValueError, IndexError, KeyError):
                return None
        self.sauvegarder()
        return ind

    def _citations_du_fait(self, pid, fait, famille=None):
        """Liste VIVANTE des citations du fait visé — même aiguillage que
        citer(). None si personne/fait introuvable ou sans citations.
        Lecture seule : ne crée jamais la liste manquante."""
        ind = self.donnees["individus"].get(pid)
        if not ind:
            return None
        fait = str(fait)
        if fait == "personne":
            cible = ind
        elif fait in ("naissance", "deces"):
            cible = ind.get(fait)
        elif fait == "union":
            fam = self._fam_visee(ind, pid, famille)
            cible = (fam or {}).get("mariage")
        elif fait.startswith("union_evenement:"):
            idx = fait.split(":", 1)[1]
            evts = (self._fam_visee(ind, pid, famille) or {}).get("evenements") or []
            cible = (evts[int(idx)]
                     if idx.isdigit() and int(idx) < len(evts) else None)
        elif ":" in fait:
            _CLE = {"residence": "residences", "profession": "professions",
                    "evenement": "evenements"}
            nom, _, idx = fait.partition(":")
            liste = ind.get(_CLE.get(nom) or "") or []
            cible = (liste[int(idx)]
                     if idx.isdigit() and int(idx) < len(liste) else None)
        else:
            try:
                cible = (ind.get("evenements") or [])[int(fait)]
            except (ValueError, IndexError):
                cible = None
        if not isinstance(cible, dict):
            return None
        cits = cible.get("citations")
        return cits if isinstance(cits, list) else None

    @_synchronise
    def citations_de(self, pid, fait, famille=None):
        """COPIE des citations attachées à un fait ([] si aucune) — pour les
        afficher (dépliage « Preuves par fait ») sans exposer la liste vivante."""
        liste = self._citations_du_fait(pid, fait, famille)
        return [dict(c) for c in (liste or []) if isinstance(c, dict)]

    @_synchronise
    def retirer_citation(self, pid, fait, index, famille=None):
        """Retire la citation n° `index` du fait visé (même aiguillage que
        citer() — vaut donc aussi pour l'union et les faits du couple, via
        `famille`). La source elle-même n'est jamais touchée. Renvoie
        l'individu si le retrait a eu lieu, None sinon."""
        try:
            index = int(index)
        except (TypeError, ValueError):
            return None
        liste = self._citations_du_fait(pid, fait, famille)
        if liste is None or not (0 <= index < len(liste)):
            return None
        del liste[index]
        self.sauvegarder()
        return self.donnees["individus"].get(pid)

    @_synchronise
    def taguer_personne_source(self, sid, pid, role=""):
        """Relie une personne à une source (personne citée, avec rôle)."""
        src = self.donnees.get("sources", {}).get(sid)
        if not src:
            return None
        perss = src.setdefault("personnes", [])
        if not any(p.get("id") == pid and p.get("role") == role for p in perss):
            perss.append({"id": pid, "role": role})
        self.sauvegarder()
        return src

    def _recalc_tous_liens(self):
        """Reconstruit fams/famc de TOUS les individus depuis les familles."""
        inds = self.donnees["individus"]
        for ind in inds.values():
            ind["fams"], ind["famc"] = [], []
        for fid, fam in self.donnees["familles"].items():
            for role in ("mari", "epouse"):
                if fam.get(role) in inds:
                    inds[fam[role]]["fams"].append(fid)
            for e in fam.get("enfants", []):
                if e in inds:
                    inds[e]["famc"].append(fid)
        for ind in inds.values():
            ind["fams"] = list(dict.fromkeys(ind["fams"]))
            ind["famc"] = list(dict.fromkeys(ind["famc"]))
